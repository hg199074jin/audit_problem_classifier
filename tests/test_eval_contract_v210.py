"""V2.1.1 contract tests: applicability target identity, emission policy, specificity."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_scorer():
    path = ROOT / "evals" / "score.py"
    spec = importlib.util.spec_from_file_location("score_v210", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _all_cases():
    rows = []
    for path in sorted((ROOT / "evals" / "cases").glob("*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                rows.append(json.loads(raw))
    return rows


def test_v210_contract_version_everywhere():
    case_schema = json.loads((ROOT / "evals/case.schema.json").read_text(encoding="utf-8"))
    assert case_schema["properties"]["contract_version"]["const"] == "2.1.1"
    result_schema = json.loads((ROOT / "evals/result.schema.json").read_text(encoding="utf-8"))
    assert result_schema["properties"]["contract_version"]["const"] == "2.1.1"
    versions = {row["contract_version"] for row in _all_cases()}
    assert versions == {"2.1.1"}
    for name in ("passing-results", "failing-results"):
        rows = [
            json.loads(line)
            for line in (ROOT / "evals/fixtures" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert {row["contract_version"] for row in rows} == {"2.1.1"}


def test_result_schema_and_case_schema_accept_applicability_target():
    result_schema = json.loads((ROOT / "evals/result.schema.json").read_text(encoding="utf-8"))
    assert "applicability_target" in result_schema["properties"]
    assert result_schema["properties"]["applicability_target"]["type"] == "string"
    case_schema = json.loads((ROOT / "evals/case.schema.json").read_text(encoding="utf-8"))
    expected_props = case_schema["properties"]["expected"]["properties"]
    assert "applicability_target" in expected_props
    assert expected_props["applicability_target"]["type"] == "string"


def test_scorer_accepts_applicability_target_in_result():
    scorer = load_scorer()
    case = {
        "contract_version": "2.1.1", "id": "x", "domain": "law-applicability", "prompt": "x", "context": {},
        "expected": {
            "applicability_target": "HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K",
            "applicability_status": "applicable",
            "law_ids": ["HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K"],
        },
    }
    result = {
        "contract_version": "2.1.1", "id": "x", "text": "",
        "applicability_target": "HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K",
        "applicability_status": "applicable",
        "law_ids": ["HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K"],
        "law_roles": {"HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K": "direct_basis"},
    }
    outcome = scorer.score_case(case, result)
    assert outcome.passed, outcome.failures


def test_scorer_requires_target_when_expected_pins_it():
    scorer = load_scorer()
    case = {
        "contract_version": "2.1.1", "id": "x", "domain": "law-applicability", "prompt": "x", "context": {},
        "expected": {
            "applicability_target": "HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K",
            "applicability_status": "applicable",
        },
    }
    missing = {
        "contract_version": "2.1.1", "id": "x", "text": "",
        "applicability_status": "applicable",
    }
    outcome = scorer.score_case(case, missing)
    assert not outcome.passed
    assert any("applicability_target" in failure for failure in outcome.failures)
    mismatched = {
        "contract_version": "2.1.1", "id": "x", "text": "",
        "applicability_target": "HENAN-GP-2020-DISP-PROVINCE-GS-1M",
        "applicability_status": "not_applicable",
    }
    outcome = scorer.score_case(case, mismatched)
    assert not outcome.passed
    assert any("applicability_target" in failure for failure in outcome.failures)


def test_applicability_target_forbidden_in_amount_and_format_domains():
    scorer = load_scorer()
    for domain in ("amount-coverage", "report-format"):
        case = {
            "contract_version": "2.1.1", "id": "x", "domain": domain, "prompt": "x", "context": {},
            "expected": {},
        }
        result = {
            "contract_version": "2.1.1", "id": "x", "text": "",
            "applicability_target": "CN-INVOICE-2023-ART20",
        }
        outcome = scorer.score_case(case, result)
        assert not outcome.passed
        assert any("applicability_target" in failure for failure in outcome.failures)


def test_kaifeng_case_pins_applicability_target_to_selected_law():
    rows = {row["id"]: row for row in _all_cases()}
    case = rows["p0-kaifeng-procurement-threshold"]
    assert case["expected"]["applicability_target"] == "HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K"
    assert case["expected"]["applicability_status"] == "applicable"
    assert "HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K" in case["expected"]["law_ids"]


def test_mode_integrated_category_is_sw_per_classification_rule():
    rows = {row["id"]: row for row in _all_cases()}
    for cid in ("mode-a-integrated-law-amount", "mode-b-integrated-law-amount"):
        assert rows[cid]["expected"]["category"] == "SW", cid
        assert rows[cid]["expected"]["finding_types"] == ["invoice_information_irregularity"]
    rule_text = (ROOT / "rules/classification.md").read_text(encoding="utf-8")
    assert "发票法定效力" in rule_text
    assert "只有已经能够直接认定违反发票管理规定或影响纳税义务时才归 SW" in rule_text


def test_result_contract_documents_conclusion_emission_policy():
    text = (ROOT / "rules/result-contract.md").read_text(encoding="utf-8")
    assert "结论码发射决策" in text
    for condition in ("事实前提", "任务范围", "隐式推导", "Finding 粒度"):
        assert condition in text, condition
    assert "reimbursement_review_insufficient" in text
    assert "不得由相邻概念隐式推导" in text


def test_result_contract_documents_applicability_target_binding():
    text = (ROOT / "rules/result-contract.md").read_text(encoding="utf-8")
    assert "applicability_target" in text
    assert "唯一" in text


def test_result_contract_documents_excluded_law_routing():
    text = (ROOT / "rules/result-contract.md").read_text(encoding="utf-8")
    assert "替代现行依据" in text
    assert "excluded_law_ids" in text


def test_classification_documents_finding_specificity_policy():
    text = (ROOT / "rules/classification.md").read_text(encoding="utf-8")
    assert "Finding 粒度规范化" in text
    assert "最具体" in text
    assert "独立 Finding" in text


def test_invoice_fixture_carries_no_unsupported_review_conclusion():
    rows = {
        row["id"]: row
        for line in (ROOT / "evals/fixtures/passing-results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }
    codes = rows["p2-invoice-irregularity-not-false-invoicing"]["conclusion_codes"]
    assert "reimbursement_review_insufficient" not in codes
    assert codes == ["invoice_irregularity_not_false_invoicing_established"]


def test_kaifeng_fixture_carries_applicability_target():
    rows = {
        row["id"]: row
        for line in (ROOT / "evals/fixtures/passing-results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }
    row = rows["p0-kaifeng-procurement-threshold"]
    assert row["applicability_target"] == "HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K"
    assert row["applicability_status"] == "applicable"


def test_mode_integrated_fixtures_use_sw_category():
    rows = {
        row["id"]: row
        for line in (ROOT / "evals/fixtures/passing-results.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }
    for cid in ("mode-a-integrated-law-amount", "mode-b-integrated-law-amount"):
        assert rows[cid]["category"] == "SW", cid
