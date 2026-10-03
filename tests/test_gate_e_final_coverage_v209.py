import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def load_cases():
    rows={}
    for path in (ROOT/"evals"/"cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                row=json.loads(raw)
                rows[row["id"]]=row
    return rows


def test_v209_adds_missing_wording_boundaries():
    cases=load_cases()
    for case_id in (
        "p2-undercollection-not-loss",
        "p2-post-signing-not-backdating",
        "p2-invoice-irregularity-not-false-invoicing",
    ):
        assert case_id in cases


def test_v209_adds_integrated_mode_a_b_law_amount_cases():
    cases=load_cases()
    for case_id in ("mode-a-integrated-law-amount","mode-b-integrated-law-amount"):
        case=cases[case_id]
        expected=case["expected"]
        assert expected["applicability_status"] == "applicable"
        assert expected["law_ids"] == ["CN-INVOICE-2023-ART20"]
        assert expected["law_roles"] == {"CN-INVOICE-2023-ART20":"direct_basis"}
        assert expected["record_count"] == 1
        assert expected["finding_count"] == 1
        assert expected["voucher_total"] == 2300


def test_amount_coverage_case_contains_structured_findings():
    cases=load_cases()
    context=cases["p0-one-record-three-findings-no-voucher-duplication"]["context"]
    assert len(context["findings"]) == 3
    assert {f["source_record_id"] for f in context["findings"]} == {"SR-001"}
