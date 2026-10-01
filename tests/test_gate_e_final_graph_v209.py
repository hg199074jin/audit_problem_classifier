import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def load_scorer():
    path=ROOT/"evals"/"score.py"
    spec=importlib.util.spec_from_file_location("score_graph_v209",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_case(context):
    return {
        "contract_version":"2.0.9","id":"x","domain":"amount-coverage","prompt":"x",
        "context":context,
        "expected":{"record_count":1,"finding_count":1,"voucher_total":100},
    }


def base_result():
    return {
        "contract_version":"2.0.9","id":"x","text":"",
        "record_count":1,"finding_count":1,"voucher_total":100,
    }


def test_duplicate_source_record_ids_fail():
    scorer=load_scorer()
    context={
        "source_records":[
            {"source_record_id":"SR-1","voucher_amount":100},
            {"source_record_id":"SR-1","voucher_amount":100},
        ],
        "findings":[{"finding_id":"F-1","source_record_id":"SR-1"}],
    }
    outcome=scorer.score_case(base_case(context),base_result())
    assert not outcome.passed
    assert any("duplicate source_record_id" in f for f in outcome.failures)


def test_orphan_finding_reference_fails():
    scorer=load_scorer()
    context={
        "source_records":[{"source_record_id":"SR-1","voucher_amount":100}],
        "findings":[{"finding_id":"F-1","source_record_id":"SR-X"}],
    }
    outcome=scorer.score_case(base_case(context),base_result())
    assert not outcome.passed
    assert any("orphan" in f for f in outcome.failures)


def test_duplicate_finding_ids_fail():
    scorer=load_scorer()
    context={
        "source_records":[{"source_record_id":"SR-1","voucher_amount":100}],
        "findings":[
            {"finding_id":"F-1","source_record_id":"SR-1"},
            {"finding_id":"F-1","source_record_id":"SR-1"},
        ],
    }
    outcome=scorer.score_case(base_case(context),base_result())
    assert not outcome.passed
    assert any("duplicate finding_id" in f for f in outcome.failures)


def test_finding_count_is_derived_from_structured_findings_when_present():
    scorer=load_scorer()
    context={
        "source_records":[{"source_record_id":"SR-1","voucher_amount":100}],
        "findings":[
            {"finding_id":"F-1","source_record_id":"SR-1"},
            {"finding_id":"F-2","source_record_id":"SR-1"},
        ],
    }
    result=base_result()|{"finding_count":1}
    outcome=scorer.score_case(
        base_case(context)|{"expected":{"record_count":1,"finding_count":2,"voucher_total":100}},
        result,
    )
    assert not outcome.passed
    assert any("finding_count" in f and "derived" in f for f in outcome.failures)
