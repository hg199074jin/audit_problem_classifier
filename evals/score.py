#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NamedTuple


class CaseOutcome(NamedTuple):
    case_id: str
    passed: bool
    failures: list[str]


class ScoreReport(NamedTuple):
    passed: bool
    outcomes: list[CaseOutcome]
    failures: list[str]


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_no}: row must be an object")
        rows.append(value)
    return rows


def _ensure_unique(rows: list[dict], label: str) -> None:
    seen: set[str] = set()
    for row in rows:
        row_id = row.get("id")
        if not isinstance(row_id, str) or not row_id:
            raise ValueError(f"{label} row missing id")
        if row_id in seen:
            raise ValueError(f"duplicate {label} id: {row_id}")
        seen.add(row_id)


def load_cases(case_dir: Path) -> list[dict]:
    case_dir = Path(case_dir)
    rows: list[dict] = []
    for path in sorted(case_dir.glob("*.jsonl")):
        rows.extend(_read_jsonl(path))
    _ensure_unique(rows, "case")
    return rows


def load_results(path: Path) -> list[dict]:
    rows = _read_jsonl(Path(path))
    _ensure_unique(rows, "result")
    return rows


def _same_number(actual, expected) -> bool:
    try:
        return Decimal(str(actual)) == Decimal(str(expected))
    except (InvalidOperation, ValueError, TypeError):
        return False


def score_case(case: dict, result: dict) -> CaseOutcome:
    failures: list[str] = []
    case_id = case["id"]
    text = result.get("text")
    if not isinstance(text, str):
        failures.append("text: missing or not a string")
        text = ""

    expected = case.get("expected") or {}
    for needle in expected.get("contains", []):
        if needle not in text:
            failures.append(f"contains: missing {needle!r}")
    for needle in expected.get("not_contains", []):
        if needle in text:
            failures.append(f"not_contains: found {needle!r}")
    structured_tokens: set[str] = set()
    category = result.get("category")
    if isinstance(category, str):
        structured_tokens.add(category)
    law_ids = result.get("law_ids")
    if isinstance(law_ids, list):
        structured_tokens.update(item for item in law_ids if isinstance(item, str))

    for needle in case.get("forbidden", []):
        if needle in text or needle in structured_tokens:
            failures.append(f"forbidden: found {needle!r}")

    if "category" in expected:
        actual = result.get("category")
        if actual != expected["category"]:
            failures.append(f"category: expected {expected['category']!r}, got {actual!r}")

    if "law_ids" in expected:
        actual_ids = result.get("law_ids")
        if not isinstance(actual_ids, list):
            failures.append("law_ids: structured list missing")
        else:
            missing = [law_id for law_id in expected["law_ids"] if law_id not in actual_ids]
            if missing:
                failures.append(f"law_ids: missing {missing!r}")

    for field in ("record_count", "finding_count"):
        if field in expected and result.get(field) != expected[field]:
            failures.append(f"{field}: expected {expected[field]!r}, got {result.get(field)!r}")

    if "voucher_total" in expected and not _same_number(result.get("voucher_total"), expected["voucher_total"]):
        failures.append(
            f"voucher_total: expected {expected['voucher_total']!r}, got {result.get('voucher_total')!r}"
        )

    return CaseOutcome(case_id, not failures, failures)


def score_all(cases: list[dict], results: list[dict]) -> ScoreReport:
    result_map = {row["id"]: row for row in results}
    outcomes: list[CaseOutcome] = []
    global_failures: list[str] = []

    for case in cases:
        case_id = case["id"]
        result = result_map.get(case_id)
        if result is None:
            failure = f"missing result: {case_id}"
            outcomes.append(CaseOutcome(case_id, False, [failure]))
            global_failures.append(failure)
            continue
        outcome = score_case(case, result)
        outcomes.append(outcome)
        global_failures.extend(f"{case_id}: {message}" for message in outcome.failures)

    case_ids = {case["id"] for case in cases}
    for extra in sorted(set(result_map) - case_ids):
        global_failures.append(f"unexpected result: {extra}")

    return ScoreReport(not global_failures, outcomes, global_failures)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic Audit Problem Classifier eval scorer")
    parser.add_argument("--cases", type=Path, required=True, help="directory containing case JSONL files")
    parser.add_argument("--results", type=Path, required=True, help="candidate result JSONL file")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    results = load_results(args.results)
    report = score_all(cases, results)

    for outcome in report.outcomes:
        if outcome.passed:
            print(f"PASS {outcome.case_id}")
        else:
            print(f"FAIL {outcome.case_id}")
            for failure in outcome.failures:
                print(f"  - {failure}")
    for failure in report.failures:
        if failure.startswith("unexpected result"):
            print(f"FAIL {failure}")

    passed = sum(1 for outcome in report.outcomes if outcome.passed)
    print(f"SUMMARY {passed}/{len(report.outcomes)} passed")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
