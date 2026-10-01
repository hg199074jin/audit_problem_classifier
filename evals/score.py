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
CONTRACT_VERSION = "2.0.3"

STRUCTURED_LIST_FIELDS = (
    "finding_types",
    "conclusion_codes",
    "law_ids",
    "excluded_law_ids",
    "law_roles",
    "report_sections",
)
STRUCTURED_SCALAR_FIELDS = (
    "gate_status",
    "category",
    "applicability_status",
    "record_count",
    "finding_count",
    "report_mode",
)

KNOWN_CONCLUSION_CODES = {
    "collusive_bidding_not_established",
    "funds_not_fully_remitted",
    "funds_occupied",
    "misappropriation_not_established",
    "reimbursement_review_insufficient",
    "travel_subsidy_pending_review",
    "decision_required_record_inclusion",
    "decision_required_blank_record",
    "decision_required_pending_items",
    "kaifeng_municipal_threshold_applies",
    "future_law_not_direct_basis",
    "cadre_only_rule_not_applicable_to_ordinary_employee",
    "enterprise_training_rule_not_applicable_to_public_institution",
    "current_invoice_art20_direct_basis",
    "obsolete_official_vehicle_rule_not_current",
    "government_purchase_service_reference_applies",
    "official_vehicle_public_institution_principle_applies",
    "unverified_law_requires_review",
    "government_procurement_scope_not_met",
    "liability_basis_not_default",
}

MUTUALLY_EXCLUSIVE_CONCLUSIONS = (
    {"collusive_bidding_not_established", "collusive_bidding_established"},
    {"misappropriation_not_established", "misappropriation_established"},
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
    rows: list[dict] = []
    for path in sorted(Path(case_dir).glob("*.jsonl")):
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


def _score_result_invariants(result: dict, failures: list[str]) -> None:
    law_ids = set(result.get("law_ids") or [])
    excluded = set(result.get("excluded_law_ids") or [])
    overlap = sorted(law_ids.intersection(excluded))
    if overlap:
        failures.append(f"law_ids/excluded_law_ids overlap: {overlap!r}")

    conclusions = set(result.get("conclusion_codes") or [])
    unknown = sorted(conclusions - KNOWN_CONCLUSION_CODES)
    if unknown:
        failures.append(f"conclusion_codes: unknown codes {unknown!r}")
    for pair in MUTUALLY_EXCLUSIVE_CONCLUSIONS:
        if pair <= conclusions:
            failures.append(f"conclusion_codes: mutually exclusive codes present {sorted(pair)!r}")

    gate = result.get("gate_status")
    if gate == "blocked":
        forbidden_fields = ("category", "finding_types", "applicability_status", "law_ids", "excluded_law_ids", "law_roles", "report_mode", "report_sections")
        for field in forbidden_fields:
            value = result.get(field)
            if value not in (None, [], ""):
                failures.append(f"blocked gate cannot emit formal field {field}")
        for field in ("record_count", "finding_count", "voucher_total"):
            value = result.get(field)
            if value not in (None, 0, 0.0):
                failures.append(f"blocked gate cannot emit nonzero {field}")

    if gate == "needs_review":
        if result.get("law_ids") not in (None, []):
            failures.append("needs_review gate cannot emit formal law_ids")
        if result.get("law_roles") not in (None, []):
            failures.append("needs_review gate cannot emit formal law_roles")


def _derived_coverage(case: dict) -> tuple[int, Decimal] | None:
    records = (case.get("context") or {}).get("source_records")
    if not isinstance(records, list):
        return None

    unique: dict[str, dict] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        record_id = record.get("source_record_id")
        if not isinstance(record_id, str) or not record_id:
            continue
        unique.setdefault(record_id, record)

    total = Decimal("0")
    for record in unique.values():
        amount = record.get("voucher_amount")
        if amount is not None:
            total += Decimal(str(amount))
    return len(unique), total


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
    if "contains" in expected or "not_contains" in expected or case.get("forbidden"):
        failures.append("legacy prose assertions are not allowed; use structured fields or report-format checks")

    _score_text_checks(case, text, failures)
    _score_format_lint(case, text, failures)
    _score_result_invariants(result, failures)

    for field in STRUCTURED_SCALAR_FIELDS:
        if field in expected and result.get(field) != expected[field]:
            failures.append(f"{field}: expected {expected[field]!r}, got {result.get(field)!r}")

    # Safety-critical lists use exact-set semantics. Extra output is as meaningful
    # as missing output, so both are failures.
    for field in STRUCTURED_LIST_FIELDS:
        if field not in expected and field not in result:
            continue
        expected_set = set(expected.get(field) or [])
        actual = result.get(field)
        if actual is None:
            actual_set: set[str] = set()
        elif isinstance(actual, list):
            actual_set = set(actual)
        else:
            failures.append(f"{field}: structured list missing")
            continue
        if actual_set != expected_set:
            failures.append(
                f"{field}: expected exact set {sorted(expected_set)!r}, got {sorted(actual_set)!r}"
            )

    derived = _derived_coverage(case)
    if derived is not None:
        derived_count, derived_total = derived
        if result.get("record_count") != derived_count:
            failures.append(
                f"record_count: derived {derived_count!r}, got {result.get('record_count')!r}"
            )
        if not _same_number(result.get("voucher_total"), derived_total):
            failures.append(
                f"voucher_total: derived {derived_total!r}, got {result.get('voucher_total')!r}"
            )
        requested_findings = (case.get("context") or {}).get("requested_findings")
        if requested_findings is not None and result.get("finding_count") != requested_findings:
            failures.append(
                f"finding_count: derived/requested {requested_findings!r}, got {result.get('finding_count')!r}"
            )
    else:
        if "record_count" in expected and result.get("record_count") != expected["record_count"]:
            failures.append(f"record_count: expected {expected['record_count']!r}, got {result.get('record_count')!r}")
        if "finding_count" in expected and result.get("finding_count") != expected["finding_count"]:
            failures.append(f"finding_count: expected {expected['finding_count']!r}, got {result.get('finding_count')!r}")
        if "voucher_total" in expected and not _same_number(result.get("voucher_total"), expected["voucher_total"]):
            failures.append(f"voucher_total: expected {expected['voucher_total']!r}, got {result.get('voucher_total')!r}")

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
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()

    report = score_all(load_cases(args.cases), load_results(args.results))
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
