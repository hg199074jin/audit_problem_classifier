#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NamedTuple

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "2.0.9"
RESULT_SCHEMA_PATH = ROOT / "evals" / "result.schema.json"

STRUCTURED_LIST_FIELDS = (
    "finding_types",
    "conclusion_codes",
    "law_ids",
    "excluded_law_ids",
    "report_sections",
)

STRUCTURED_OBJECT_FIELDS = (
    "law_roles",
)
STRUCTURED_SCALAR_FIELDS = (
    "gate_status",
    "category",
    "applicability_status",
    "record_count",
    "finding_count",
    "report_mode",
)

ALLOWED_RESULT_FIELDS = {
    "id",
    "contract_version",
    "text",
    "gate_status",
    "category",
    "finding_types",
    "conclusion_codes",
    "applicability_status",
    "law_ids",
    "excluded_law_ids",
    "record_count",
    "finding_count",
    "voucher_total",
    "law_roles",
    "report_mode",
    "report_sections",
}

KNOWN_FINDING_TYPES = {
    "procurement_quote_collusion_suspected",
    "procurement_inquiry_missing",
    "procurement_quotation_material_nonstandard",
    "procurement_award_material_nonstandard",
    "procurement_economic_analysis_insufficient",
    "expense_supporting_documents_incomplete",
    "expense_supporting_documents_nonstandard",
    "accounting_issue",
    "tax_issue",
    "distribution_list_missing",
    "receivable_undercollection",
    "contract_signed_after_performance",
    "invoice_information_irregularity",
}

KNOWN_REPORT_SECTIONS = {
    "mode_a_overview_coverage",
    "mode_a_classification_summary",
    "mode_a_classification_details",
    "mode_a_management_recommendations",
    "mode_a_followup_materials",
    "mode_b_engagement_purpose",
    "mode_b_entity_overview",
    "mode_b_major_findings",
    "mode_b_opinions_recommendations",
    "mode_b_report_use_scope",
}

DOMAIN_FORBIDDEN_FIELDS = {
    "amount-coverage": {
        "category",
        "finding_types",
        "conclusion_codes",
        "applicability_status",
        "law_ids",
        "excluded_law_ids",
        "law_roles",
        "report_mode",
        "report_sections",
    },
    "report-format": {
        "conclusion_codes",
        "applicability_status",
        "law_ids",
        "excluded_law_ids",
        "law_roles",
        "report_mode",
        "report_sections",
    },
}

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
    "recoverable_undercollection_not_loss_established",
    "post_execution_signing_not_backdating_established",
    "invoice_irregularity_not_false_invoicing_established",
}

DIAGNOSTIC_CONCLUSION_CODES = {
    "unverified_law_requires_review",
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


def _load_law_catalog() -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    law_root = ROOT / "references" / "laws"
    try:
        import yaml
    except ImportError:
        return catalog
    for path in law_root.rglob("*.yaml"):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            catalog[data["id"]] = data
    return catalog


def _known_law_ids() -> set[str]:
    return set(_load_law_catalog())


def _validate_result_schema(result: dict) -> list[str]:
    schema = json.loads(RESULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    failures: list[str] = []
    for error in sorted(validator.iter_errors(result), key=lambda item: list(item.path)):
        path = ".".join(str(part) for part in error.path) or "<root>"
        failures.append(f"result schema/type: {path}: {error.message}")
    return failures


def _is_empty(value) -> bool:
    return value in (None, "", [], {})


def _score_result_invariants(case: dict, result: dict, failures: list[str]) -> None:
    unknown_top_level = sorted(set(result) - ALLOWED_RESULT_FIELDS)
    for field in unknown_top_level:
        failures.append(f"unknown top-level field: {field}")

    domain = case.get("domain")
    for field in DOMAIN_FORBIDDEN_FIELDS.get(domain, set()):
        value = result.get(field)
        if not _is_empty(value):
            failures.append(f"{domain}: field {field} is outside this eval domain's emission profile")

    law_ids = set(result.get("law_ids") or [])
    excluded = set(result.get("excluded_law_ids") or [])
    overlap = sorted(law_ids.intersection(excluded))
    if overlap:
        failures.append(f"law_ids/excluded_law_ids overlap: {overlap!r}")

    findings = set(result.get("finding_types") or [])
    unknown_findings = sorted(findings - KNOWN_FINDING_TYPES)
    if unknown_findings:
        failures.append(f"finding_types: unknown codes {unknown_findings!r}")

    conclusions = set(result.get("conclusion_codes") or [])
    unknown = sorted(conclusions - KNOWN_CONCLUSION_CODES)
    if unknown:
        failures.append(f"conclusion_codes: unknown codes {unknown!r}")
    for pair in MUTUALLY_EXCLUSIVE_CONCLUSIONS:
        if pair <= conclusions:
            failures.append(f"conclusion_codes: mutually exclusive codes present {sorted(pair)!r}")

    law_catalog = _load_law_catalog()
    known_laws = set(law_catalog)
    for field in ("law_ids", "excluded_law_ids"):
        values = set(result.get(field) or [])
        unknown_laws = sorted(values - known_laws)
        if unknown_laws:
            failures.append(f"{field}: unknown law id(s) {unknown_laws!r}")

    raw_roles = result.get("law_roles")
    if law_ids and not isinstance(raw_roles, dict):
        failures.append("law_roles: complete mapping required for selected law_ids")
    if raw_roles is not None:
        if not isinstance(raw_roles, dict):
            failures.append("law_roles must be an object mapping law_id to role")
        else:
            allowed_roles = {"direct_basis", "supporting_basis", "liability_basis"}
            role_keys = set(raw_roles)
            unknown_role_keys = sorted(role_keys - known_laws)
            if unknown_role_keys:
                failures.append(f"law_roles: unknown law id key(s) {unknown_role_keys!r}")
            non_selected = sorted(role_keys - law_ids)
            if non_selected:
                failures.append(f"law_roles keys must be selected law_ids: {non_selected!r}")
            missing_roles = sorted(law_ids - role_keys)
            if missing_roles:
                failures.append(f"law_roles: complete mapping missing selected law_ids: {missing_roles!r}")
            unknown_roles = sorted({role for role in raw_roles.values() if role not in allowed_roles})
            if unknown_roles:
                failures.append(f"law_roles: unknown role value(s) {unknown_roles!r}")
            for law_id in sorted(role_keys.intersection(law_ids).intersection(known_laws)):
                catalog_role = law_catalog[law_id].get("rule_role")
                actual_role = raw_roles.get(law_id)
                if catalog_role != actual_role:
                    failures.append(
                        f"law_roles: {law_id} role {actual_role!r} does not match Law Object rule_role {catalog_role!r}"
                    )
            if (
                any(role == "liability_basis" for role in raw_roles.values())
                and (case.get("context") or {}).get("user_requested_liability_analysis") is not True
            ):
                failures.append("law_roles: liability_basis requires explicit user_requested_liability_analysis=true")

    sections = set(result.get("report_sections") or [])
    unknown_sections = sorted(sections - KNOWN_REPORT_SECTIONS)
    if unknown_sections:
        failures.append(f"report_sections: unknown canonical code(s) {unknown_sections!r}")
    context_report_mode = (case.get("context") or {}).get("report_mode")
    if sections and context_report_mode is None:
        failures.append("report_sections may only be emitted when context.report_mode is explicitly provided")

    gate = result.get("gate_status")
    if gate == "blocked":
        forbidden_fields = ("category", "finding_types", "applicability_status", "law_ids", "excluded_law_ids", "law_roles", "report_mode", "report_sections")
        for field in forbidden_fields:
            value = result.get(field)
            if not _is_empty(value):
                failures.append(f"blocked gate cannot emit formal field {field}")
        for field in ("record_count", "finding_count", "voucher_total"):
            value = result.get(field)
            if value not in (None, 0, 0.0):
                failures.append(f"blocked gate cannot emit nonzero {field}")

    if gate == "needs_review":
        if result.get("law_ids") not in (None, []):
            failures.append("needs_review gate cannot emit formal law_ids")
        if not _is_empty(result.get("law_roles")):
            failures.append("needs_review gate cannot emit formal law_roles")


def _validate_case_graph(case: dict, failures: list[str]) -> None:
    context = case.get("context") or {}
    records = context.get("source_records")
    if records is None:
        return
    if not isinstance(records, list):
        failures.append("case graph: source_records must be a list")
        return

    record_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            failures.append("case graph: each source_record must be an object")
            continue
        record_id = record.get("source_record_id")
        if not isinstance(record_id, str) or not record_id:
            failures.append("case graph: source_record_id missing or invalid")
            continue
        if record_id in record_ids:
            failures.append(f"case graph: duplicate source_record_id {record_id}")
        record_ids.add(record_id)
        amount = record.get("voucher_amount")
        if amount is not None:
            try:
                decimal_amount = Decimal(str(amount))
            except (InvalidOperation, ValueError, TypeError):
                failures.append(f"case graph: invalid voucher_amount for {record_id}")
            else:
                if decimal_amount < 0:
                    failures.append(f"case graph: negative voucher_amount for {record_id}")

    findings = context.get("findings")
    if findings is None:
        return
    if not isinstance(findings, list):
        failures.append("case graph: findings must be a list")
        return

    finding_ids: set[str] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            failures.append("case graph: each finding must be an object")
            continue
        finding_id = finding.get("finding_id")
        source_record_id = finding.get("source_record_id")
        if not isinstance(finding_id, str) or not finding_id:
            failures.append("case graph: finding_id missing or invalid")
        elif finding_id in finding_ids:
            failures.append(f"case graph: duplicate finding_id {finding_id}")
        else:
            finding_ids.add(finding_id)
        if source_record_id not in record_ids:
            failures.append(
                f"case graph: orphan finding {finding_id!r} references unknown source_record_id {source_record_id!r}"
            )
        amounts = finding.get("amounts") or {}
        if isinstance(amounts, dict):
            for field, value in amounts.items():
                if value is None:
                    continue
                try:
                    decimal_value = Decimal(str(value))
                except (InvalidOperation, ValueError, TypeError):
                    failures.append(f"case graph: invalid finding amount {field} for {finding_id}")
                    continue
                if decimal_value < 0:
                    failures.append(f"case graph: negative finding amount {field} for {finding_id}")

    requested = context.get("requested_findings")
    if requested is not None and requested != len(findings):
        failures.append(
            f"case graph: requested_findings {requested!r} does not match structured findings {len(findings)!r}"
        )


def _derived_coverage(case: dict) -> tuple[int, Decimal, int | None] | None:
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
    findings = (case.get("context") or {}).get("findings")
    derived_findings = len(findings) if isinstance(findings, list) else None
    if derived_findings is None:
        requested_findings = (case.get("context") or {}).get("requested_findings")
        if isinstance(requested_findings, int):
            derived_findings = requested_findings
    return len(unique), total, derived_findings


def score_case(case: dict, result: dict) -> CaseOutcome:
    failures: list[str] = []
    case_id = case["id"]

    schema_failures = _validate_result_schema(result)
    failures.extend(schema_failures)
    if schema_failures:
        return CaseOutcome(case_id, False, failures)

    _validate_case_graph(case, failures)

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
    _score_result_invariants(case, result, failures)

    for field in STRUCTURED_SCALAR_FIELDS:
        if field in expected and result.get(field) != expected[field]:
            failures.append(f"{field}: expected {expected[field]!r}, got {result.get(field)!r}")

    if "law_roles" in expected:
        expected_roles = expected.get("law_roles")
        actual_roles = result.get("law_roles")
        if _is_empty(expected_roles):
            if not _is_empty(actual_roles):
                failures.append(
                    f"law_roles: expected empty mapping, got {actual_roles!r}"
                )
        elif not isinstance(actual_roles, dict):
            failures.append("law_roles: expected object mapping law_id to role")
        elif actual_roles != expected_roles:
            failures.append(
                f"law_roles: expected exact mapping {expected_roles!r}, got {actual_roles!r}"
            )

    exact_fields = set(expected.get("exact_fields") or [])
    for field in STRUCTURED_LIST_FIELDS:
        if field not in expected:
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

        if field in exact_fields:
            if actual_set != expected_set:
                failures.append(
                    f"{field}: expected exact set {sorted(expected_set)!r}, got {sorted(actual_set)!r}"
                )
        else:
            missing = sorted(expected_set - actual_set)
            if missing:
                failures.append(f"{field}: missing required values {missing!r}")
            if field == "conclusion_codes":
                unexpected = sorted(actual_set - expected_set - DIAGNOSTIC_CONCLUSION_CODES)
                if unexpected:
                    failures.append(f"unexpected conclusion_codes: {unexpected!r}")

    derived = _derived_coverage(case)
    if derived is not None:
        derived_count, derived_total, derived_finding_count = derived
        if result.get("record_count") != derived_count:
            failures.append(
                f"record_count: derived {derived_count!r}, got {result.get('record_count')!r}"
            )
        if not _same_number(result.get("voucher_total"), derived_total):
            failures.append(
                f"voucher_total: derived {derived_total!r}, got {result.get('voucher_total')!r}"
            )
        if derived_finding_count is not None and result.get("finding_count") != derived_finding_count:
            failures.append(
                f"finding_count: derived {derived_finding_count!r}, got {result.get('finding_count')!r}"
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
