#!/usr/bin/env python3
"""Pre-final Skill delivery boundary (V2.2.4).

Mandatory companion to the conclusion-grounding boundary (SKILL workflow
step 13). A machine result may only be DELIVERED when every invoice-level
claim it makes is backed by verified audit objects:

- `finding_types` containing `invoice_information_irregularity` or a
  `category` of `SW` requires at least one `audit_objects` entry whose
  decision is `authorized_sw` and whose assertion quotes verify verbatim
  against the immutable source input (prompt + context).
- FY / needs_review / blocked deliveries need no audit objects.

Fail closed: violations -> exit 1, nothing on stdout (the delivery is
refused); the runtime fixes its result and re-runs until clean.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

INVOICE_FINDING = "invoice_information_irregularity"


def _load_aog():
    path = Path(__file__).resolve().parent / "audit_object_grounding.py"
    spec = importlib.util.spec_from_file_location("audit_object_grounding_delivery", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_delivery(result: dict, sources: dict[str, str]) -> list[str]:
    """Return violation codes; empty list = deliverable.

    F-002: the recorded `decision` field is NOT trusted — decisions are
    re-derived through the frozen gate; a self-filled authorized_sw that the
    gate would not grant is a refusal (DECISION_MISMATCH)."""
    violations: list[str] = []
    finding_types = result.get("finding_types") or []
    category = result.get("category")
    invoice_claim = (
        isinstance(finding_types, list) and INVOICE_FINDING in finding_types
    ) or category == "SW"
    if not invoice_claim:
        return violations

    objects = result.get("audit_objects")
    if not isinstance(objects, list) or not objects:
        violations.append(
            "SW_WITHOUT_AUTHORIZED_OBJECT: invoice finding requires at least one "
            "authorized_sw audit object verified against the source input"
        )
        return violations

    aog = _load_aog()
    delivery_violations, authorized_ids = aog.verify_delivery_objects(objects, sources)
    if not authorized_ids:
        violations.append("SW_WITHOUT_AUTHORIZED_OBJECT: no gate-recomputed authorized_sw object")
    for violation in delivery_violations:
        violations.append(f"AUDIT_OBJECT_UNVERIFIED:{violation}")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pre-final Skill delivery boundary (V2.2.4)")
    parser.add_argument("--result", required=True, help="machine result JSON file")
    parser.add_argument("--source", required=True, help='source JSON {"prompt":..., "context":...}')
    args = parser.parse_args(argv)
    try:
        result = json.loads(Path(args.result).read_text(encoding="utf-8"))
        sources = json.loads(Path(args.source).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not isinstance(result, dict) or not isinstance(sources, dict):
        print("ERROR: result must be an object and source must map prompt/context", file=sys.stderr)
        return 2
    violations = verify_delivery(result, sources)
    if violations:
        for v in violations:
            print(f"VIOLATION {v}", file=sys.stderr)
        print("DELIVERY-REFUSED: fix the machine result and re-run until clean", file=sys.stderr)
        return 1
    print("PASS skill delivery boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
