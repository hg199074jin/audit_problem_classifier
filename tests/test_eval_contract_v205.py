import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_scorer():
    path = ROOT / "evals" / "score.py"
    spec = importlib.util.spec_from_file_location("score_v209", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v209_contract_version():
    schema=json.loads((ROOT/"evals/case.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "2.0.9"
    versions=set()
    for path in (ROOT/"evals/cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                versions.add(json.loads(raw)["contract_version"])
    assert versions == {"2.0.9"}


def test_conservative_unverified_review_code_is_allowed_without_predeclared_context_candidate():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.9","id":"x","domain":"classification","prompt":"x","context":{},
        "expected":{"conclusion_codes":["collusive_bidding_not_established","decision_required_pending_items"]},
    }
    result={
        "contract_version":"2.0.9","id":"x","text":"",
        "conclusion_codes":["collusive_bidding_not_established","unverified_law_requires_review"],
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures


def test_extra_known_excluded_laws_are_diagnostic_when_not_exact():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.9","id":"x","domain":"law-applicability","prompt":"x","context":{},
        "expected":{"law_ids":["CN-GOV-PURCHASE-SERVICES-2020-ART18-PUBLIC-INSTITUTION-REF"]},
    }
    result={
        "contract_version":"2.0.9","id":"x","text":"",
        "law_ids":["CN-GOV-PURCHASE-SERVICES-2020-ART18-PUBLIC-INSTITUTION-REF"],
        "law_roles":{"CN-GOV-PURCHASE-SERVICES-2020-ART18-PUBLIC-INSTITUTION-REF":"direct_basis"},
        "excluded_law_ids":["CN-GOV-PURCHASE-SERVICES-2020-ART18"],
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures


def test_specific_and_parent_finding_types_can_coexist_when_not_exact():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.9","id":"x","domain":"report-mode","prompt":"x",
        "context":{"report_mode":"classification_report"},
        "expected":{"finding_types":["distribution_list_missing"]},
    }
    result={
        "contract_version":"2.0.9","id":"x","text":"",
        "finding_types":["distribution_list_missing","expense_supporting_documents_incomplete"],
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures


def test_needs_review_does_not_suppress_independent_evidence_conclusion():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.9","id":"x","domain":"classification","prompt":"x","context":{},
        "expected":{"conclusion_codes":["collusive_bidding_not_established"]},
    }
    result={
        "contract_version":"2.0.9","id":"x","text":"",
        "gate_status":"needs_review",
        "conclusion_codes":["collusive_bidding_not_established","decision_required_pending_items"],
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures

    contract=(ROOT/"rules/result-contract.md").read_text(encoding="utf-8")
    assert "needs_review 不得吞掉已经独立成立的证据层结论" in contract
    assert "collusive_bidding_not_established" in contract


def test_v209_removes_exact_finding_types_from_live_and_mode_cases():
    cases={}
    for path in (ROOT/"evals/cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                row=json.loads(raw)
                cases[row["id"]]=row
    for case_id in ("live-20260629","mode-a-complete-regression","mode-b-complete-regression"):
        assert "finding_types" not in set(cases[case_id]["expected"].get("exact_fields") or [])


def test_v209_removes_closed_excluded_sets_from_three_positive_law_cases():
    cases={}
    for path in (ROOT/"evals/cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                row=json.loads(raw)
                cases[row["id"]]=row
    for case_id in (
        "p0-kaifeng-procurement-threshold",
        "p1-gps-public-institution-reference",
        "p1-official-vehicle-public-institution-principle",
    ):
        expected=cases[case_id]["expected"]
        assert "excluded_law_ids" not in set(expected.get("exact_fields") or [])
