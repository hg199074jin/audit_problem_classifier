from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def load_case(case_id: str):
    for path in sorted((ROOT / "evals" / "cases").glob("*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            row=json.loads(raw)
            if row["id"]==case_id:
                return row
    raise AssertionError(f"missing case {case_id}")


def test_travel_subsidy_pending_review_does_not_require_reimbursement_review_insufficient():
    case=load_case("qualitative-downgrade")
    codes=case["expected"]["conclusion_codes"]
    assert "travel_subsidy_pending_review" in codes
    assert "reimbursement_review_insufficient" not in codes


def test_result_contract_distinguishes_pending_entitlement_from_confirmed_review_deficiency():
    text=(ROOT / "rules" / "result-contract.md").read_text(encoding="utf-8")
    assert "travel_subsidy_pending_review" in text
    assert "reimbursement_review_insufficient" in text
    assert "不构成蕴含关系" in text
    assert "只有在已有证据能够确认报销审核程序或必要附件存在缺陷时" in text


def test_eval_contract_version_is_209():
    cases=[]
    for path in sorted((ROOT / "evals" / "cases").glob("*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                cases.append(json.loads(raw))
    assert cases
    assert {row["contract_version"] for row in cases} == {"2.1.1"}
    schema=json.loads((ROOT / "evals" / "case.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "2.1.1"
