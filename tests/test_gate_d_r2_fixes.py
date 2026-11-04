"""Gate D round 2 generalizable fixes: fact-precondition conclusion gate + candidate_rule_id target binding."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_scorer():
    spec = importlib.util.spec_from_file_location("score_r2", ROOT / "evals" / "score.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r2_review_insufficient_requires_context_facts():
    scorer = load_scorer()
    case = {
        "contract_version": "2.2.2", "id": "x", "domain": "classification", "prompt": "p", "context": {},
        "expected": {"conclusion_codes": ["collusive_bidding_not_established"]},
    }
    result = {
        "contract_version": "2.2.2", "id": "x", "text": "",
        "conclusion_codes": ["collusive_bidding_not_established", "reimbursement_review_insufficient"],
    }
    outcome = scorer.score_case(case, result)
    assert not outcome.passed
    assert any("review_control" in f or "reimbursement_review_insufficient" in f for f in outcome.failures)


def test_r2_review_insufficient_allowed_with_context_facts():
    """V2.2.2: the code is licensed by grounded review-control facts whose
    citations appear verbatim in the case source input."""
    scorer = load_scorer()
    case = {
        "contract_version": "2.2.2", "id": "x", "domain": "evidence-wording",
        "prompt": "该笔报销单已经部门负责人签批，但财务审核岗位未履行审核程序即予入账。",
        "context": {},
        "expected": {"conclusion_codes": ["reimbursement_review_insufficient"]},
    }
    result = {
        "contract_version": "2.2.2", "id": "x", "text": "",
        "conclusion_codes": ["reimbursement_review_insufficient"],
        "fact_grounding": [
            {"field": "review_procedure_defect", "value": True, "citation": "财务审核岗位未履行审核程序即予入账"},
            {"field": "finding_is_review_control", "value": True, "citation": "财务审核岗位未履行审核程序即予入账"},
        ],
    }
    outcome = scorer.score_case(case, result)
    assert outcome.passed, outcome.failures


def test_r2_candidate_rule_id_binds_target():
    scorer = load_scorer()
    case = {
        "contract_version": "2.2.2", "id": "x", "domain": "law-applicability", "prompt": "p",
        "context": {"candidate_rule_id": "CN-OFFICIAL-VEHICLE-2011-HIST"},
        "expected": {"applicability_status": "not_applicable", "applicability_target": "CN-OFFICIAL-VEHICLE-2011-HIST"},
    }
    wrong_target = {
        "contract_version": "2.2.2", "id": "x", "text": "",
        "applicability_status": "applicable", "applicability_target": "CN-OFFICIAL-VEHICLE-2017",
        "law_ids": ["CN-OFFICIAL-VEHICLE-2017"],
    }
    outcome = scorer.score_case(case, wrong_target)
    assert not outcome.passed
    assert any("candidate_rule_id" in f or "applicability_target" in f for f in outcome.failures)
    right_target = {
        "contract_version": "2.2.2", "id": "x", "text": "",
        "applicability_status": "not_applicable", "applicability_target": "CN-OFFICIAL-VEHICLE-2011-HIST",
        "excluded_law_ids": ["CN-OFFICIAL-VEHICLE-2011-HIST"],
    }
    outcome = scorer.score_case(case, right_target)
    assert outcome.passed, outcome.failures


def test_r2Obsolete_vehicle_case_context_has_candidate_rule_id():
    rows = {}
    for path in sorted((ROOT / "evals" / "cases").glob("*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                row = json.loads(raw)
                rows[row["id"]] = row
    context = rows["p0-obsolete-official-vehicle-rule-not-current"]["context"]
    assert context.get("candidate_rule_id") == "CN-OFFICIAL-VEHICLE-2011-HIST"
