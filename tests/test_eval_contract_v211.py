"""V2.1.1 contract tests: version alignment, frozen oracles, positive-protection, stale-version cleanup."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _all_cases():
    rows = []
    for path in sorted((ROOT / "evals" / "cases").glob("*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                rows.append(json.loads(raw))
    return rows


def _fixture_rows(name):
    return {
        row["id"]: row
        for line in (ROOT / "evals/fixtures" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }


def test_v211_version_everywhere():
    case_schema = json.loads((ROOT / "evals/case.schema.json").read_text(encoding="utf-8"))
    assert case_schema["properties"]["contract_version"]["const"] == "2.1.1"
    result_schema = json.loads((ROOT / "evals/result.schema.json").read_text(encoding="utf-8"))
    assert result_schema["properties"]["contract_version"]["const"] == "2.1.1"
    assert {row["contract_version"] for row in _all_cases()} == {"2.1.1"}
    for name in ("passing-results", "failing-results"):
        rows = [
            json.loads(line)
            for line in (ROOT / "evals/fixtures" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert {row["contract_version"] for row in rows} == {"2.1.1"}
    scorer_text = (ROOT / "evals" / "score.py").read_text(encoding="utf-8")
    assert 'CONTRACT_VERSION = "2.1.1"' in scorer_text
    assert "2.0.9" not in scorer_text


def test_contract_docs_reference_v211():
    for rel in ("rules/result-contract.md", "evals/README.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "2.1.1" in text, rel


def test_frozen_oracle_live_20260629_unchanged():
    rows = {row["id"]: row for row in _all_cases()}
    expected = rows["live-20260629"]["expected"]
    assert expected["conclusion_codes"] == ["collusive_bidding_not_established"]
    assert expected["finding_types"] == [
        "procurement_quote_collusion_suspected",
        "procurement_inquiry_missing",
        "expense_supporting_documents_incomplete",
        "accounting_issue",
        "tax_issue",
    ]


def test_frozen_oracle_expense_boundary_unchanged():
    rows = {row["id"]: row for row in _all_cases()}
    expected = rows["expense-boundary"]["expected"]
    assert expected["category"] == "FY"
    assert expected["finding_types"] == [
        "expense_supporting_documents_incomplete",
        "expense_supporting_documents_nonstandard",
    ]


def test_protected_p2_invoice_case_keeps_safe_conclusion():
    rows = {row["id"]: row for row in _all_cases()}
    expected = rows["p2-invoice-irregularity-not-false-invoicing"]["expected"]
    assert expected["conclusion_codes"] == ["invoice_irregularity_not_false_invoicing_established"]
    fixture = _fixture_rows("passing-results")["p2-invoice-irregularity-not-false-invoicing"]
    assert fixture["conclusion_codes"] == ["invoice_irregularity_not_false_invoicing_established"]


def test_protected_mode_integrated_cases_keep_sw():
    rows = {row["id"]: row for row in _all_cases()}
    fixture = _fixture_rows("passing-results")
    for cid in ("mode-a-integrated-law-amount", "mode-b-integrated-law-amount"):
        assert rows[cid]["expected"]["category"] == "SW", cid
        assert fixture[cid]["category"] == "SW", cid
        assert rows[cid]["expected"]["finding_types"] == ["invoice_information_irregularity"]


def test_protected_kaifeng_target_design_unchanged():
    rows = {row["id"]: row for row in _all_cases()}
    expected = rows["p0-kaifeng-procurement-threshold"]["expected"]
    assert expected["applicability_target"] == "HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K"
    assert expected["applicability_status"] == "applicable"


def test_result_schema_pairing_invariants_unchanged():
    schema = json.loads((ROOT / "evals/result.schema.json").read_text(encoding="utf-8"))
    assert schema["dependentRequired"]["applicability_status"] == ["applicability_target"]
    assert schema["dependentRequired"]["applicability_target"] == ["applicability_status"]


def test_classification_documents_fy_sw_decision_gate_with_engine():
    text = (ROOT / "rules/classification.md").read_text(encoding="utf-8")
    assert "FY 与 SW：附带发票瑕疵拆分决策门" in text
    assert "scripts/classification_emission.py" in text
    assert "invoice_information_irregularity" in text
    assert "不得额外拆出" in text or "DO NOT SPLIT" in text


def test_classification_independent_finding_criteria_conjunctive():
    text = (ROOT / "rules/classification.md").read_text(encoding="utf-8")
    assert "同时成立" in text
    assert "不构成" in text and "独立 Finding" in text


def test_result_contract_documents_safe_conclusion_trigger_gate():
    text = (ROOT / "rules/result-contract.md").read_text(encoding="utf-8")
    assert "实际触发对应严重定性争议" in text
    assert "invoice_irregularity_not_false_invoicing_established" in text
    assert "decision_required_" in text
    assert "防御性发射" in text


def test_classification_emission_engine_exists():
    assert (ROOT / "scripts/classification_emission.py").exists()
