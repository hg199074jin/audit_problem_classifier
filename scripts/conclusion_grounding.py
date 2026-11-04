#!/usr/bin/env python3
"""Fact-grounding pre-final boundary for guarded conclusion codes (V2.2.3).

Root cause (V2.2.1 Gate D, cases 04/23/24): the runtime freely derived fact
booleans (e.g. `pending_or_unconfirmed_facts=True` when the evidence chain was
merely open, or `finding_is_review_control=True` when only an attachment was
missing) and then fed them to the decision gates, producing over-emitted
conclusion codes. Text-only rules cannot constrain an LLM's fact derivation.

This module closes the loop with two mechanisms (V2.2.2 + V2.2.3):

1. Verbatim-presence grounding (V2.2.2): a guarded conclusion code is only
   accepted when the runtime supplies, for every required fact, a citation
   that appears verbatim in the source input text (prompt + context).
2. Field-specific support (V2.2.3): a verbatim citation must also *support*
   the claimed fact field — the citation text must contain at least one
   professional anchor phrase for that field (FIELD_SUPPORT_ANCHORS). A
   citation that is present but about something else (e.g. an amount cited
   for a blank-record fact) fails closed.

The three decision_required codes are guarded 1:1 (V2.2.3): each code is
licensed only by its own fact, so one generalization code can never swallow
the facts of its brother codes.

Enforcement is fail-closed without cross-field rewriting (V2.2.3):
`enforce_grounding` returns the result UNMODIFIED together with the
violations. It never partially rewrites `gate_status`, `applicability_*`,
`law_ids` or `law_roles` — partial rewriting of unrelated fields could
manufacture new contract violations. On violations the caller must not
deliver the result: the runtime removes the ungrounded codes itself and
re-runs the boundary until it exits clean.

The boundary is invoked as a mandatory pre-final step by the Skill workflow
(SKILL.md step 13) and is mirrored by a global (not expected-dependent) check
in the eval scorer, which derives its guarded set from GUARDED_CODES.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

# Guarded conclusion codes and the facts that license them.
#
# `any_of`  — at least one listed fact must be grounded (value True).
# `all_of`  — every listed fact must be grounded (value True).
#
# The three decision_required codes map 1:1 to their own fact (V2.2.3): a
# generalization code must not absorb its brother codes' facts.
#
# `required_attachments_missing` is deliberately NOT a licensing fact for
# `reimbursement_review_insufficient`: a missing attachment supports
# `distribution_list_missing`, but review-control failure requires an
# independent review-procedure / sign-off / responsibility fact.
CONCLUSION_FACT_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "decision_required_blank_record": {
        "any_of": ["blank_record"],
    },
    "decision_required_record_inclusion": {
        "any_of": ["inclusion_decision_needed"],
    },
    "decision_required_pending_items": {
        "any_of": ["pending_or_unconfirmed_facts"],
    },
    "reimbursement_review_insufficient": {
        "any_of": ["review_procedure_defect", "approval_responsibility_facts"],
        "all_of": ["finding_is_review_control"],
    },
}

GUARDED_CODES = frozenset(CONCLUSION_FACT_REQUIREMENTS)

# Field-specific support lexicon (V2.2.3). A citation grounds a fact field
# only when it contains at least one of the field's professional anchor
# phrases. Anchors are a small whitelist tied to the professional meaning of
# each field — not a keyword blacklist and not case-specific.
FIELD_SUPPORT_ANCHORS: dict[str, tuple[str, ...]] = {
    "blank_record": ("问题描述空白", "空白记录", "无问题描述", "描述空白", "为空", "留空"),
    "inclusion_decision_needed": (
        "只有摘要和金额", "只有金额", "汇总行", "只有摘要",
        "无事项", "没有事项", "无问题描述",
    ),
    "pending_or_unconfirmed_facts": ("待落实", "是否有文件", "待确认", "待核实", "待定"),
    "review_procedure_defect": ("未履行审核", "审核程序", "未经审核", "未审核", "审核记录缺失"),
    "approval_responsibility_facts": ("签批", "审批", "批准"),
    "finding_is_review_control": ("审核岗位", "审核程序", "复核", "审批", "签批", "审核记录"),
}

# Defect-class fields whose licensing citation must not state a COMPLETED /
# satisfactory control state (V2.2.3 polarity guard, preflight F-001): a
# citation like "审核程序完整" or "审批手续齐全" names the topic but asserts
# its opposite, so it must not license the defect.
DEFECT_TYPE_FIELDS = frozenset({"review_procedure_defect", "finding_is_review_control"})
COMPLETION_STATE_ANCHORS = (
    "已履行审核", "已审核", "审核程序完整", "程序完备", "手续齐全",
    "审批手续完备", "审核合格", "审核到位", "依规审核", "审核程序合规",
)


def _citation_in_source(citation: str, source_text: str) -> bool:
    """A citation grounds a fact only when it appears verbatim in the source."""
    if not isinstance(citation, str):
        return False
    needle = citation.strip()
    if not needle:
        return False
    return needle in source_text


def _citation_supports_field(citation: str, field: str) -> bool:
    """A verbatim citation supports a field only when it carries one of the
    field's professional anchors (V2.2.3) — and, for defect-class fields, when
    it does not assert a completed/satisfactory control state (polarity
    guard, V2.2.3 preflight F-001)."""
    if not isinstance(citation, str):
        return False
    if field in DEFECT_TYPE_FIELDS:
        for done in COMPLETION_STATE_ANCHORS:
            if done in citation:
                return False
    anchors = FIELD_SUPPORT_ANCHORS.get(field)
    if not anchors:
        # No lexicon entry: fall back to verbatim presence only.
        return True
    return any(anchor in citation for anchor in anchors)


def verify_grounding(result: dict, source_text: str) -> list[str]:
    """Return a list of grounding violations for the guarded codes in `result`.

    A violation is reported when:
    - a guarded conclusion code is emitted without any fact record;
    - a required fact is missing, false, or its citation is absent from the
      source text;
    - a citation is present verbatim but does not support the claimed field
      (no professional anchor of that field in the citation text, V2.2.3);
    - `reimbursement_review_insufficient` rests only on
      `required_attachments_missing` (explicitly non-licensing).
    """
    violations: list[str] = []
    codes = result.get("conclusion_codes") or []
    if not isinstance(codes, list):
        return ["conclusion_codes: not a list"]
    grounding = result.get("fact_grounding")
    if grounding is None:
        grounding = []
    if not isinstance(grounding, list):
        return ["fact_grounding: not a list"]

    # index fact records by field name
    facts: dict[str, dict[str, Any]] = {}
    for record in grounding:
        if isinstance(record, dict) and isinstance(record.get("field"), str):
            facts[record["field"]] = record

    for code in codes:
        if code not in CONCLUSION_FACT_REQUIREMENTS:
            continue
        req = CONCLUSION_FACT_REQUIREMENTS[code]

        def _ok(field: str) -> bool:
            record = facts.get(field)
            if not isinstance(record, dict):
                return False
            if record.get("value") is not True:
                return False
            citation = record.get("citation")
            if not _citation_in_source(citation, source_text):
                return False
            return _citation_supports_field(citation, field)

        any_fields = req.get("any_of") or []
        all_fields = req.get("all_of") or []
        if any_fields and not any(_ok(f) for f in any_fields):
            violations.append(
                f"{code}: no grounded licensing fact among {any_fields} "
                "(fact record missing/false, citation not present in source "
                "input, or citation does not support the fact field)"
            )
        for field in all_fields:
            if not _ok(field):
                violations.append(
                    f"{code}: required fact {field!r} not grounded "
                    "(missing/false, citation not present in source input, "
                    "or citation does not support the fact field)"
                )
    return violations


def enforce_grounding(result: dict, source_text: str) -> tuple[dict, list[str]]:
    """Return (result, violations). Fail-closed, no cross-field mutation.

    The result is returned UNMODIFIED (a deep copy). When violations exist the
    caller must not deliver the result: per the Skill workflow the runtime
    removes the ungrounded codes itself and re-runs this boundary until it
    exits clean. This module never partially rewrites `gate_status`,
    `applicability_*`, `law_ids` or `law_roles` — silent partial rewriting of
    unrelated fields can manufacture new contract violations.
    """
    violations = verify_grounding(result, source_text)
    return copy.deepcopy(result), violations


def _load_json(path: str) -> dict:
    if path == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fact-grounding boundary for guarded conclusion codes"
    )
    parser.add_argument("--result", required=True, help="machine result JSON file, or '-' for stdin")
    parser.add_argument("--source", required=True, help="source input text file, or '-' for stdin")
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="pre-final boundary: deliver the result on stdout only when grounding is clean",
    )
    args = parser.parse_args(argv)

    try:
        result = _load_json(args.result)
        source_text = _load_text(args.source)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not isinstance(result, dict):
        print("ERROR: result must be a JSON object", file=sys.stderr)
        return 2

    if args.enforce:
        boundary_result, violations = enforce_grounding(result, source_text)
        if violations:
            for violation in violations:
                print(f"VIOLATION {violation}", file=sys.stderr)
            print(
                "GROUNDING-ENFORCEMENT-BLOCKED: result not delivered; "
                "remove the ungrounded guarded codes and re-run until clean",
                file=sys.stderr,
            )
            return 1
        print(json.dumps(boundary_result, ensure_ascii=False, indent=2))
        return 0

    violations = verify_grounding(result, source_text)
    for violation in violations:
        print(f"VIOLATION {violation}")
    if violations:
        return 1
    print("PASS conclusion grounding")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
