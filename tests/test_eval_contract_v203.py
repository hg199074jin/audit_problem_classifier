import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_scorer():
    path = ROOT / "evals" / "score.py"
    spec = importlib.util.spec_from_file_location("score_gatee", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v204_contract_is_frozen_in_cases_and_schema():
    schema = json.loads((ROOT / "evals" / "case.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "2.0.4"
    versions=set()
    for path in (ROOT / "evals" / "cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                versions.add(json.loads(raw)["contract_version"])
    assert versions == {"2.0.4"}


def test_unknown_dangerous_extra_conclusion_is_rejected():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.4","id":"x","domain":"evidence-wording","prompt":"x","context":{},
        "expected":{"conclusion_codes":["collusive_bidding_not_established"]}
    }
    result={
        "contract_version":"2.0.4","id":"x","text":"",
        "conclusion_codes":["collusive_bidding_not_established","misappropriation_established"]
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("unknown codes" in x for x in outcome.failures)


def test_law_ids_and_excluded_law_ids_must_not_overlap():
    scorer=load_scorer()
    case={"contract_version":"2.0.4","id":"x","domain":"law-applicability","prompt":"x","context":{},"expected":{"law_ids":["CN-INVOICE-2023-ART20"]}}
    result={"contract_version":"2.0.4","id":"x","text":"","law_ids":["CN-INVOICE-2023-ART20"],"excluded_law_ids":["CN-INVOICE-2023-ART20"]}
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("overlap" in x for x in outcome.failures)


def test_blocked_gate_cannot_emit_formal_result_fields():
    scorer=load_scorer()
    case={"contract_version":"2.0.4","id":"x","domain":"decision-gate","prompt":"x","context":{},"expected":{"gate_status":"blocked"}}
    result={
        "contract_version":"2.0.4","id":"x","text":"","gate_status":"blocked",
        "category":"CG","law_ids":["CN-INVOICE-2023-ART20"],"record_count":1,"finding_count":1,"voucher_total":100
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("blocked" in x for x in outcome.failures)


def test_amount_coverage_is_recomputed_from_source_records():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.4","id":"x","domain":"amount-coverage","prompt":"x",
        "context":{
            "source_records":[
                {"source_record_id":"SR-1","voucher_amount":10000},
                {"source_record_id":"SR-1","voucher_amount":10000},
            ],
            "requested_findings":3
        },
        "expected":{"record_count":1,"finding_count":3,"voucher_total":10000}
    }
    bad={"contract_version":"2.0.4","id":"x","text":"","record_count":2,"finding_count":3,"voucher_total":20000}
    outcome=scorer.score_case(case,bad)
    assert not outcome.passed
    assert any("derived" in x for x in outcome.failures)


def test_gate_e_runtime_cases_are_present():
    ids=set()
    for path in (ROOT / "evals" / "cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                ids.add(json.loads(raw)["id"])
    required={
        "p1-gps-public-institution-reference",
        "p1-official-vehicle-public-institution-principle",
        "p1-unverified-law-needs-review",
        "p1-henan-works-own-funds-not-applicable",
        "p1-liability-basis-not-default",
        "mode-a-complete-regression",
        "mode-b-complete-regression",
    }
    assert required <= ids
