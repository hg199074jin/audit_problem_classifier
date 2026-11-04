#!/usr/bin/env python3
"""Fact-grounding pre-final boundary for guarded conclusion codes (V2.2.2).

Root cause (V2.2.1 Gate D, cases 04/23/24): the runtime freely derived fact
booleans (e.g. `pending_or_unconfirmed_facts=True` when the evidence chain was
merely open, or `finding_is_review_control=True` when only an attachment was
missing) and then fed them to the decision gates, producing over-emitted
conclusion codes. Text-only rules cannot constrain an LLM's fact derivation.

This module closes the loop: a guarded conclusion code is only accepted when
the runtime supplies, for every required fact, a citation that is verifiably
present in the source input text (prompt + context). Missing or ungrounded
evidence fails closed: the code is dropped and the situation is reported.

The boundary is invoked as a mandatory pre-final step by the Skill workflow
(SKILL.md step 12) and is mirrored by a global (not expected-dependent) check
in the eval scorer.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Guarded conclusion codes and the facts that license them.
#
# `any_of`  — at least one listed fact must be grounded (value True).
# `all_of`  — every listed fact must be grounded (value True).
#
# `required_attachments_missing` is deliberately NOT a licensing fact for
# `reimbursement_review_insufficient`: a missing attachment supports
# `distribution_list_missing`, but review-control failure requires an
# independent review-procedure / sign-off / responsibility fact.
CONCLUSION_FACT_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "decision_required_pending_items": {
        "any_of": ["blank_record", "inclusion_decision_needed", "pending_or_unconfirmed_facts"],
    },
    "reimbursement_review_insufficient": {
        "any_of": ["review_procedure_defect", "approval_responsibility_facts"],
        "all_of": ["finding_is_review_control"],
    },
}

GUARDED_CODES = frozenset(CONCLUSION_FACT_REQUIREMENTS)


def _citation_in_source(citation: str, source_text: str) -> bool:
    """A citation grounds a fact only when it appears verbatim in the source."""
    if not isinstance(citation, str):
        return False
    needle = citation.strip()
    if not needle:
        return False
    return needle in source_text


def verify_grounding(result: dict, source_text: str) -> list[str]:
    """Return a list of grounding violations for the guarded codes in `result`.

    A violation is reported when:
    - a guarded conclusion code is emitted without any fact record;
    - a required fact is missing, false, or its citation is absent from the
      source text;
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
            return _citation_in_source(record.get("citation"), source_text)

        any_fields = req.get("any_of") or []
        all_fields = req.get("all_of") or []
        if any_fields and not any(_ok(f) for f in any_fields):
            violations.append(
                f"{code}: no grounded licensing fact among {any_fields} "
                "(fact record missing/false, or citation not present in source input)"
            )
        for field in all_fields:
            if not _ok(field):
                violations.append(
                    f"{code}: required fact {field!r} not grounded "
                    "(missing/false, or citation not present in source input)"
                )
    return violations


def enforce_grounding(result: dict, source_text: str) -> tuple[dict, list[str]]:
    """Return (cleaned_result, violations).

    Ungrounded guarded codes are removed from `conclusion_codes`. When the
    emission of a code was the only support for a `proceed`/`applicable`
    stance, the cleaned result is downgraded to `needs_review` so the failure
    is closed rather than silently green.
    """
    violations = verify_grounding(result, source_text)
    cleaned = dict(result)
    codes = cleaned.get("conclusion_codes")
    if isinstance(codes, list) and violations:
        grounding = cleaned.get("fact_grounding") or []

        def _grounded(code: str) -> bool:
            req = CONCLUSION_FACT_REQUIREMENTS[code]
            facts = {
                r.get("field"): r
                for r in grounding
                if isinstance(r, dict) and isinstance(r.get("field"), str)
            }
            def ok(f: str) -> bool:
                r = facts.get(f)
                return bool(
                    isinstance(r, dict)
                    and r.get("value") is True
                    and _citation_in_source(r.get("citation"), source_text)
                )
            any_fields = req.get("any_of") or []
            all_fields = req.get("all_of") or []
            if any_fields and not any(ok(f) for f in any_fields):
                return False
            return all(ok(f) for f in all_fields)

        kept = [c for c in codes if c not in GUARDED_CODES or _grounded(c)]
        dropped = [c for c in codes if c not in kept]
        if dropped:
            cleaned["conclusion_codes"] = kept
            if cleaned.get("gate_status") == "proceed":
                cleaned["gate_status"] = "needs_review"
            if cleaned.get("applicability_status") == "applicable":
                cleaned["applicability_status"] = "needs_review"
    return cleaned, violations


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
        help="emit the grounded result on stdout instead of only reporting violations",
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
        cleaned, violations = enforce_grounding(result, source_text)
        print(json.dumps(cleaned, ensure_ascii=False, indent=2))
        for violation in violations:
            print(f"VIOLATION {violation}", file=sys.stderr)
        return 1 if violations else 0

    violations = verify_grounding(result, source_text)
    for violation in violations:
        print(f"VIOLATION {violation}")
    if violations:
        return 1
    print("PASS conclusion grounding")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
