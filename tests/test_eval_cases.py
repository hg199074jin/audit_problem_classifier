import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "evals" / "cases"
CASE_FILES = [
    "classification.jsonl",
    "law-applicability.jsonl",
    "evidence-wording.jsonl",
    "amount-coverage.jsonl",
    "report-format.jsonl",
    "report-modes.jsonl",
]
REQUIRED = {"contract_version", "id", "domain", "prompt", "context", "expected"}
MACHINE_KEYS = {
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
    "text_checks",
    "format_forbid",
    "law_roles",
    "report_mode",
    "report_sections",
    "exact_fields",
}


def load_cases():
    cases = []
    for filename in CASE_FILES:
        path = CASE_DIR / filename
        assert path.exists(), f"missing eval file: {path}"
        for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise AssertionError(f"{path}:{line_no} invalid JSON: {exc}") from exc
            cases.append((path, line_no, item))
    return cases


def test_eval_files_exist_and_rows_have_v205_contract():
    cases = load_cases()
    assert cases, "eval case set must not be empty"
    for path, line_no, item in cases:
        missing = REQUIRED - item.keys()
        assert not missing, f"{path}:{line_no} missing fields: {sorted(missing)}"
        assert item["contract_version"] == "2.0.5"
        assert isinstance(item["context"], dict), f"{path}:{line_no} context must be object"
        assert isinstance(item["expected"], dict), f"{path}:{line_no} expected must be object"
        assert MACHINE_KEYS & item["expected"].keys(), (
            f"{path}:{line_no} expected must contain at least one machine-checkable assertion"
        )


def test_eval_ids_are_unique_across_all_domains():
    ids = []
    for path, line_no, item in load_cases():
        case_id = item.get("id")
        assert isinstance(case_id, str) and case_id.strip(), f"{path}:{line_no} invalid id"
        ids.append(case_id)
    duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    assert not duplicates, f"duplicate eval ids: {duplicates}"


def test_mandatory_p0_regressions_are_present():
    ids = {item["id"] for _, _, item in load_cases()}
    mandatory = {
        "p0-kaifeng-procurement-threshold",
        "p0-no-future-law-for-2025",
        "p0-no-cadre-rule-for-ordinary-worker",
        "p0-no-enterprise-training-rule-for-public-institution",
        "p0-current-invoice-reimbursement-provision",
        "p0-obsolete-official-vehicle-rule-not-current",
        "p0-suspicious-quotes-not-collusive-bidding-finding",
        "p0-one-record-three-findings-no-voucher-duplication",
    }
    assert mandatory <= ids, f"missing mandatory P0 cases: {sorted(mandatory - ids)}"


def test_eval_schema_and_readme_exist():
    assert (ROOT / "evals" / "case.schema.json").exists()
    assert (ROOT / "evals" / "README.md").exists()
