#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "2.0.1"

STRUCTURED_LIST_FIELDS = (
    "finding_types",
    "conclusion_codes",
    "law_ids",
    "excluded_law_ids",
)
STRUCTURED_SCALAR_FIELDS = (
    "gate_status",
    "category",
    "applicability_status",
    "record_count",
    "finding_count",
)


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


def _load_format_linter():
    path = ROOT / "scripts" / "report_format_lint.py"
    spec = importlib.util.spec_from_file_location("report_format_lint_for_eval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load report format linter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _score_text_checks(case: dict, text: str, failures: list[str]) -> None:
    checks = (case.get("expected") or {}).get("text_checks")
    if checks is None:
        return
    if case.get("domain") != "report-format":
        failures.append("text_checks: literal text assertions are only allowed for report-format cases")
        return
    if not isinstance(checks, dict):
        failures.append("text_checks: expected an object")
        return

    for needle in checks.get("contains", []):
        if needle not in text:
            failures.append(f"text_checks.contains: missing {needle!r}")
    for needle in checks.get("not_contains", []):
        if needle in text:
            failures.append(f"text_checks.not_contains: found {needle!r}")
    for pattern in checks.get("regex", []):
        if re.search(pattern, text) is None:
            failures.append(f"text_checks.regex: no match for {pattern!r}")
    for pattern in checks.get("not_regex", []):
        if re.search(pattern, text) is not None:
            failures.append(f"text_checks.not_regex: matched {pattern!r}")


def _score_format_lint(case: dict, text: str, failures: list[str]) -> None:
    expected = case.get("expected") or {}
    forbidden_violations = expected.get("format_forbid")
    if forbidden_violations is None:
        return
    if case.get("domain") != "report-format":
        failures.append("format_forbid: format lint is only allowed for report-format cases")
        return

    module = _load_format_linter()
    actual_violations = set(module.lint_report_text(text))
    for violation in forbidden_violations:
        if violation in actual_violations:
            failures.append(f"format_forbid: found {violation!r}")


def score_case(case: dict, result: dict) -> CaseOutcome:
    failures: list[str] = []
    case_id = case["id"]
    text = result.get("text")
    if not isinstance(text, str):
        failures.append("text: missing or not a string")
        text = ""

    case_version = case.get("contract_version")
    if case_version is not None and result.get("contract_version") != case_version:
        failures.append(
            f"contract_version: expected {case_version!r}, got {result.get('contract_version')!r}"
        )

    expected = case.get("expected") or {}

    if "contains" in expected or "not_contains" in expected:
        failures.append("legacy prose assertions are not allowed in V2.0.1; use structured fields or report-format text_checks")
    if case.get("forbidden"):
        failures.append("legacy forbidden assertions are not allowed in V2.0.1")

    _score_text_checks(case, text, failures)
    _score_format_lint(case, text, failures)

    for field in STRUCTURED_SCALAR_FIELDS:
        if field in expected and result.get(field) != expected[field]:
            failures.append(f"{field}: expected {expected[field]!r}, got {result.get(field)!r}")

    for field in STRUCTURED_LIST_FIELDS:
        if field not in expected:
            continue
        actual = result.get(field)
        if not isinstance(actual, list):
            failures.append(f"{field}: structured list missing")
            continue
        missing = [item for item in expected[field] if item not in actual]
        if missing:
            failures.append(f"{field}: missing {missing!r}")

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
