#!/usr/bin/env python3
"""Evidence-grounded audit-object authorization boundary (V2.2.4).

Root cause (V2.2.3 Gate D, case-10): the invoice split gate consumed naked
runtime booleans (`independent_invoice_object`, `false_invoicing_dispute`).
The same invoice fact flipped between FY and SW across equivalent wordings
because the gate's INPUT AUTHORITY was unverified model judgment.

Frozen semantics: docs/decisions/v224-invoice-audit-object-adjudication.md

Chain: immutable source input (prompt + context) → typed AuditObjectCandidate
with verbatim source-anchored assertions → deterministic verification
(quote presence, source identity, offsets, professional anchors, polarity)
→ authorization decision (authorized_sw / incidental_fy / needs_review /
no_invoice_finding / rejected).

Key properties:
- A quote that is merely present is not proof: each assertion_kind carries a
  professional anchor lexicon; unsupported or negative/hypothetical-polarity
  assertions never authorize (fail closed).
- Restriction facts (`true_transaction`, `false_invoicing_evidence_absent`)
  only constrain conclusions (no false-invoicing finding); they can neither
  create nor absorb an audit object.
- The runtime cannot authorize itself: `decision` fields on input candidates
  are ignored; only this gate assigns decisions.

No network, no side effects. CLI: authorize --input objects.json --source source.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Frozen enums (adjudication §3).
OBJECT_KINDS = ("expense_reimbursement", "invoice_compliance", "tax_obligation")
DEFECT_KINDS = (
    "invoice_buyer_mismatch",
    "issuer_payee_mismatch",
    "noncompliant_invoice_obtained",
    "invoice_information_irregular_fact",
)
FOCUS_KINDS = (
    "explicit_invoice_characterization_request",
    "explicit_invoice_legality_question",
)
RESTRICTION_KINDS = ("true_transaction", "false_invoicing_evidence_absent")
KNOWN_KINDS = DEFECT_KINDS + FOCUS_KINDS + RESTRICTION_KINDS

# Professional anchor lexicons (V2.2.3 FIELD_SUPPORT_ANCHORS pattern):
# a verbatim quote supports an assertion_kind only when it carries one of the
# kind's anchors. Whitelist tied to professional meaning — not a blacklist,
# not case-specific.
ASSERTION_ANCHORS: dict[str, tuple[str, ...]] = {
    "invoice_buyer_mismatch": ("购买方信息", "购买方与实际", "抬头不一致", "抬头不符", "抬头与实际"),
    "issuer_payee_mismatch": ("开票单位与收款单位不一致", "开票方与收款方", "收款单位不一致", "开票单位与收款单位不一致"),
    # F-003: factual phrasing only — the bare statute substring alone must not
    # authorize; normative sentences (不得/应当/必须) are rejected outright.
    "noncompliant_invoice_obtained": (
        "取得不符合规定的发票", "开具了不符合规定的发票", "收到不符合规定的发票",
        "取得不合规发票", "开具不合规发票",
    ),
    "invoice_information_irregular_fact": (
        "购买方信息", "抬头不一致", "抬头不符", "开票单位与收款单位不一致",
        "不符合规定的发票", "发票记载", "记载信息", "票面信息",
    ),
    "explicit_invoice_characterization_request": ("定性", "如何认定", "请认定"),
    "explicit_invoice_legality_question": (
        "是否合规", "能否作为财务报销凭证", "能否报销", "是否合法", "合规性",
    ),
    "true_transaction": ("交易真实", "业务真实", "货物确已取得", "确已取得"),
    "false_invoicing_evidence_absent": (
        "没有虚构交易", "无真实业务开票", "暂无虚开", "没有虚开", "无虚开",
        "虚开发票证据", "未发现虚开",
    ),
}

# Normative/legal sentences are law, not fact evidence: a defect assertion
# whose quote reads as a rule statement fails closed (F-003).
NORMATIVE_MARKERS = ("不得", "应当", "必须", "严禁")

VALID_SOURCE_KEYS = ("prompt", "context")


def validate_sources(sources: dict) -> list[str]:
    """Source maps may only carry prompt/context keys (F-005)."""
    if not isinstance(sources, dict):
        return ["SOURCE_KEYS_ILLEGAL:not_a_map"]
    return [f"SOURCE_KEYS_ILLEGAL:{k}" for k in sources if k not in VALID_SOURCE_KEYS]


def _verify_assertion(obj_id: str, idx: int, assertion: dict, sources: dict[str, str]) -> list[str]:
    """Return violation codes for one assertion (empty = fully valid)."""
    prefix = f"{obj_id}#{idx}"
    violations: list[str] = []
    kind = assertion.get("assertion_kind")
    polarity = assertion.get("polarity")
    source_id = assertion.get("source_id")
    quote = assertion.get("quote")

    if kind not in KNOWN_KINDS:
        violations.append(f"{prefix}:ASSERTION_KIND_UNKNOWN:{kind}")
        return violations
    if source_id not in sources:
        violations.append(f"{prefix}:SOURCE_ID_UNKNOWN:{source_id}")
        return violations
    if not isinstance(quote, str) or not quote.strip():
        violations.append(f"{prefix}:QUOTE_EMPTY")
        return violations
    text = sources[source_id] or ""
    if quote not in text:
        violations.append(f"{prefix}:QUOTE_NOT_IN_SOURCE:{source_id}")
        return violations
    if "start" in assertion and "end" in assertion:
        start, end = assertion["start"], assertion["end"]
        if not (
            isinstance(start, int) and isinstance(end, int)
            and 0 <= start <= end <= len(text)
            and text[start:end] == quote
        ):
            violations.append(f"{prefix}:OFFSET_MISMATCH")
            return violations
    anchors = ASSERTION_ANCHORS.get(kind, ())
    if anchors and not any(anchor in quote for anchor in anchors):
        violations.append(f"{prefix}:ANCHOR_NOT_SUPPORTED:{kind}")
        return violations
    if kind in DEFECT_KINDS and any(marker in quote for marker in NORMATIVE_MARKERS):
        violations.append(f"{prefix}:ANCHOR_NORMATIVE_SENTENCE:{kind}")
        return violations
    if polarity == "hypothetical":
        # A hypothetical statement never asserts a fact of this audit.
        violations.append(f"{prefix}:HYPOTHETICAL_NOT_AUTHORIZING")
        return violations
    if kind == "false_invoicing_evidence_absent" and polarity != "negative":
        violations.append(f"{prefix}:POLARITY_CONFLICT:{kind}:{polarity}")
        return violations
    if kind in ("true_transaction",) and polarity != "affirmative":
        violations.append(f"{prefix}:POLARITY_CONFLICT:{kind}:{polarity}")
        return violations
    if kind in DEFECT_KINDS and polarity != "affirmative":
        violations.append(f"{prefix}:POLARITY_CONFLICT:{kind}:{polarity}")
        return violations
    if kind in FOCUS_KINDS and polarity != "affirmative":
        violations.append(f"{prefix}:POLARITY_CONFLICT:{kind}:{polarity}")
        return violations
    return violations


def verify_audit_objects(objects: list[dict], sources: dict[str, str]) -> list[str]:
    """Verify every assertion of every object against immutable sources.

    Returns violation codes; an empty list means every assertion is verbatim,
    source-bound, anchor-supported, and polarity-consistent. Duplicate
    object_ids and malformed entries are flagged (fail closed).
    """
    violations: list[str] = []
    seen_ids: set[str] = set()
    for pos, obj in enumerate(objects or []):
        if not isinstance(obj, dict):
            violations.append(f"ENTRY#{pos}:OBJECT_MALFORMED_NOT_A_DICT")
            continue
        obj_id = str(obj.get("object_id") or "AO-?")
        if obj_id in seen_ids:
            violations.append(f"{obj_id}:OBJECT_ID_DUPLICATED")
        seen_ids.add(obj_id)
        for idx, assertion in enumerate(obj.get("assertions") or []):
            if not isinstance(assertion, dict):
                violations.append(f"{obj_id}#{idx}:ASSERTION_MALFORMED_NOT_A_DICT")
                continue
            violations.extend(_verify_assertion(obj_id, idx, assertion, sources))
    return violations


def _decide_object(obj: dict, sources: dict[str, str]) -> dict:
    """Apply the frozen authorization decision table to one object."""
    obj_id = str(obj.get("object_id") or "AO-?")
    out = {
        "object_id": obj_id,
        "source_record_id": obj.get("source_record_id"),
        "object_kind": obj.get("object_kind"),
        "directness": obj.get("directness"),
        "assertions": obj.get("assertions") or [],
        "reason_codes": [],
        "review_reason": None,
    }

    defect: list[str] = []
    focus: list[str] = []
    restriction: list[str] = []
    invalid = 0
    for idx, assertion in enumerate(obj.get("assertions") or []):
        if not isinstance(assertion, dict):
            invalid += 1
            out["reason_codes"].append("ASSERTION_MALFORMED_NOT_A_DICT")
            continue
        kind = assertion.get("assertion_kind")
        bad = _verify_assertion(obj_id, idx, assertion, sources)
        if bad:
            invalid += 1
            out["reason_codes"].append(bad[0].split(":", 1)[1])
            continue
        if kind in DEFECT_KINDS:
            defect.append(kind)
        elif kind in FOCUS_KINDS:
            focus.append(kind)
        elif kind in RESTRICTION_KINDS:
            restriction.append(kind)

    directness = obj.get("directness")

    if defect:
        noncompliant_as_object = "noncompliant_invoice_obtained" in defect
        if (focus or noncompliant_as_object) and directness == "primary":
            out["decision"] = "authorized_sw"
            out["reason_codes"].append(
                "SW_AUTHORIZED_NONCOMPLIANT_OBJECT" if noncompliant_as_object and not focus
                else "SW_AUTHORIZED_WITH_FOCUS"
            )
        elif directness == "incidental":
            out["decision"] = "incidental_fy"
            out["reason_codes"].append("INCIDENTAL_ABSORBED_FY")
        else:  # primary claimed but no focus evidence
            out["decision"] = "needs_review"
            out["reason_codes"].append("PRIMARY_WITHOUT_FOCUS")
            out["review_reason"] = "主张 primary 认定对象但缺少焦点证据（定性请求/合法性发问/法规违反本身为对象）"
    elif focus:
        out["decision"] = "needs_review"
        out["reason_codes"].append("FOCUS_WITHOUT_DEFECT")
        out["review_reason"] = "存在发票认定请求但无有效的具体发票异常事实；不得默认归入 FY"
    elif restriction:
        out["decision"] = "no_invoice_finding"
        out["reason_codes"].append("NEGATIVE_ONLY_NO_OBJECT")
    else:
        out["decision"] = "rejected"
        out["reason_codes"].append("NO_VALID_ASSERTIONS")

    if restriction:
        # Restriction facts constrain conclusions only (never authorize/absorb).
        out["reason_codes"].append("RESTRICT_NO_FALSE_INVOICING_FINDING")
    if invalid and out["decision"] not in ("rejected",):
        out["reason_codes"].append("PARTIAL_INVALID_ASSERTIONS")
    if out["decision"] == "rejected" and not any(
        rc.startswith(("NO_VALID_ASSERTIONS",)) for rc in out["reason_codes"]
    ):
        out["reason_codes"].append("NO_VALID_ASSERTIONS")
    return out


def authorize_audit_objects(objects: list[dict], sources: dict[str, str]) -> dict:
    """Deterministic authorization: verify all assertions, then apply the
    frozen decision table per object. Input `decision` fields are ignored —
    only this gate assigns decisions (the runtime cannot self-authorize).
    Malformed entries become rejected objects (fail closed, never crash)."""
    decided: list[dict] = []
    for obj in (objects or []):
        if not isinstance(obj, dict):
            decided.append({
                "object_id": "AO-MALFORMED",
                "source_record_id": None,
                "object_kind": None,
                "directness": None,
                "assertions": [],
                "reason_codes": ["OBJECT_MALFORMED_NOT_A_DICT"],
                "review_reason": "malformed audit object entry",
                "decision": "rejected",
            })
            continue
        decided.append(_decide_object(obj, sources))
    summary = {
        "authorized_sw": sum(1 for o in decided if o["decision"] == "authorized_sw"),
        "incidental_fy": sum(1 for o in decided if o["decision"] == "incidental_fy"),
        "needs_review": sum(1 for o in decided if o["decision"] == "needs_review"),
        "no_invoice_finding": sum(1 for o in decided if o["decision"] == "no_invoice_finding"),
        "rejected": sum(1 for o in decided if o["decision"] == "rejected"),
    }
    return {"objects": decided, "summary": summary}


def verify_delivery_objects(objects: list[dict], sources: dict[str, str]) -> tuple[list[str], set[str]]:
    """Downstream delivery/scorer boundary helper (F-002): verify every
    assertion AND re-derive every decision — the recorded `decision` field is
    cross-checked against the gate's recomputed decision, so a runtime cannot
    self-authorize downstream of the gate. Also enforces the source-key
    whitelist (F-005).

    Returns (violation codes, recomputed authorized_sw object ids).
    """
    violations = validate_sources(sources)
    decided = authorize_audit_objects(objects, sources)
    recomputed = {o["object_id"]: o["decision"] for o in decided["objects"]}
    violations.extend(verify_audit_objects(objects, sources))
    for obj in objects or []:
        if not isinstance(obj, dict):
            continue
        oid = str(obj.get("object_id") or "AO-?")
        recorded = obj.get("decision")
        recomputed_decision = recomputed.get(oid)
        if recorded is not None and recomputed_decision is not None and recorded != recomputed_decision:
            violations.append(f"{oid}:DECISION_MISMATCH:{recorded}!={recomputed_decision}")
    authorized_ids = {oid for oid, d in recomputed.items() if d == "authorized_sw"}
    return violations, authorized_ids


def _read_json(path: str) -> dict | list:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    return json.loads(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evidence-grounded audit-object authorization")
    sub = parser.add_subparsers(dest="command", required=True)
    p_auth = sub.add_parser("authorize", help="verify and authorize audit objects")
    p_auth.add_argument("--input", required=True, help="objects JSON file, or '-' for stdin")
    p_auth.add_argument("--source", required=True, help='source JSON file {"prompt":..., "context":...}')
    p_verify = sub.add_parser("verify", help="verify assertions only, print violations")
    p_verify.add_argument("--input", required=True)
    p_verify.add_argument("--source", required=True)
    args = parser.parse_args(argv)

    try:
        objects = _read_json(args.input)
        sources = _read_json(args.source)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not isinstance(sources, dict):
        print("ERROR: source JSON must be an object with prompt/context keys", file=sys.stderr)
        return 2
    for key in sources:
        if key not in ("prompt", "context"):
            print(f"ERROR: illegal source key: {key}", file=sys.stderr)
            return 2

    if args.command == "verify":
        violations = verify_audit_objects(objects if isinstance(objects, list) else [], sources)
        for v in violations:
            print(f"VIOLATION {v}")
        return 1 if violations else 0

    if not isinstance(objects, list):
        print("ERROR: input JSON must be an array of audit objects", file=sys.stderr)
        return 2
    result = authorize_audit_objects(objects, sources)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["summary"]["rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
