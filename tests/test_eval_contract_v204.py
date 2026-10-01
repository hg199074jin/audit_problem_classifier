import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_scorer():
    path = ROOT / "evals" / "score.py"
    spec = importlib.util.spec_from_file_location("score_v207", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_case():
    return {
        "contract_version": "2.0.7",
        "id": "x",
        "domain": "classification",
        "prompt": "x",
        "context": {},
        "expected": {
            "finding_types": ["expense_supporting_documents_incomplete"],
            "conclusion_codes": ["collusive_bidding_not_established"],
        },
    }


def test_v207_contract_version():
    schema=json.loads((ROOT/"evals/case.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "2.0.7"
    versions=set()
    for path in (ROOT/"evals/cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                versions.add(json.loads(raw)["contract_version"])
    assert versions == {"2.0.7"}


def test_list_expectations_are_required_subset_by_default():
    scorer=load_scorer()
    case=base_case()
    result={
        "contract_version":"2.0.7","id":"x","text":"",
        "finding_types":[
            "expense_supporting_documents_incomplete",
            "expense_supporting_documents_nonstandard",
        ],
        "conclusion_codes":[
            "collusive_bidding_not_established",
            "travel_subsidy_pending_review",
        ],
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures


def test_exact_fields_opt_in_rejects_extra_values():
    scorer=load_scorer()
    case=base_case()
    case["expected"]["exact_fields"]=["finding_types"]
    result={
        "contract_version":"2.0.7","id":"x","text":"",
        "finding_types":[
            "expense_supporting_documents_incomplete",
            "expense_supporting_documents_nonstandard",
        ],
        "conclusion_codes":["collusive_bidding_not_established"],
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("exact set" in x for x in outcome.failures)


def test_field_absent_from_expected_does_not_mean_empty():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.7","id":"x","domain":"law-applicability","prompt":"x",
        "context":{"event_date":"2025-01-01"},
        "expected":{"conclusion_codes":["future_law_not_direct_basis"]},
    }
    result={
        "contract_version":"2.0.7","id":"x","text":"",
        "conclusion_codes":["future_law_not_direct_basis"],
        "excluded_law_ids":["CN-INVOICE-2010-ART21-HIST"],
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures


def test_unknown_law_id_is_rejected_even_when_field_not_expected():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.7","id":"x","domain":"law-applicability","prompt":"x",
        "context":{},"expected":{"conclusion_codes":["future_law_not_direct_basis"]},
    }
    result={
        "contract_version":"2.0.7","id":"x","text":"",
        "conclusion_codes":["future_law_not_direct_basis"],
        "excluded_law_ids":["FAKE-LEGACY-ID"],
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("unknown law id" in x for x in outcome.failures)


def test_report_sections_only_emit_for_explicit_report_mode_context():
    scorer=load_scorer()
    case=base_case()
    result={
        "contract_version":"2.0.7","id":"x","text":"",
        "finding_types":["expense_supporting_documents_incomplete"],
        "conclusion_codes":["collusive_bidding_not_established"],
        "report_sections":["mode_a_overview_coverage"],
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("report_sections" in x and "report_mode" in x for x in outcome.failures)


def test_report_sections_use_canonical_codes_not_titles():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.7","id":"x","domain":"report-mode","prompt":"x",
        "context":{"report_mode":"classification_report"},
        "expected":{
            "report_mode":"classification_report",
            "report_sections":[
                "mode_a_overview_coverage",
                "mode_a_classification_summary",
                "mode_a_classification_details",
                "mode_a_management_recommendations",
                "mode_a_followup_materials",
            ],
            "exact_fields":["report_sections"],
        },
    }
    good={
        "contract_version":"2.0.7","id":"x","text":"",
        "report_mode":"classification_report",
        "report_sections":[
            "mode_a_overview_coverage",
            "mode_a_classification_summary",
            "mode_a_classification_details",
            "mode_a_management_recommendations",
            "mode_a_followup_materials",
        ],
    }
    assert scorer.score_case(case,good).passed
    bad=good|{"report_sections":["基本情况及覆盖校验"]}
    outcome=scorer.score_case(case,bad)
    assert not outcome.passed
    assert any("report_sections" in x for x in outcome.failures)


def test_unverified_review_code_may_be_emitted_from_runtime_analysis_path():
    scorer=load_scorer()
    case=base_case()
    result={
        "contract_version":"2.0.7","id":"x","text":"",
        "finding_types":["expense_supporting_documents_incomplete"],
        "conclusion_codes":[
            "collusive_bidding_not_established",
            "unverified_law_requires_review",
        ],
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures


def test_mode_a_and_format_case_use_same_specific_finding_type():
    ids={}
    for path in (ROOT/"evals/cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                row=json.loads(raw)
                ids[row["id"]]=row
    assert ids["format-hard-rules"]["expected"]["finding_types"] == ["distribution_list_missing"]
    assert ids["mode-a-complete-regression"]["expected"]["finding_types"] == ["distribution_list_missing"]


def test_live_classification_case_has_project_context_needed_to_proceed():
    ids={}
    for path in (ROOT/"evals/cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                row=json.loads(raw)
                ids[row["id"]]=row
    context=ids["live-20260629"]["context"]
    assert context["jurisdiction"]["province"] == "Henan"
    assert context["organization"]["type"] == "public_institution"
    assert context["audit_period"]["start"]
    assert context["audit_period"]["end"]


def test_amount_coverage_rejects_unrelated_semantic_fields():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.7","id":"x","domain":"amount-coverage","prompt":"x",
        "context":{"source_records":[{"source_record_id":"SR-1","voucher_amount":10000}],"requested_findings":3},
        "expected":{"record_count":1,"finding_count":3,"voucher_total":10000},
    }
    result={
        "contract_version":"2.0.7","id":"x","text":"",
        "record_count":1,"finding_count":3,"voucher_total":10000,
        "conclusion_codes":["funds_occupied"],
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("amount-coverage" in x and "conclusion_codes" in x for x in outcome.failures)


def test_report_format_rejects_unrelated_semantic_conclusions():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.7","id":"x","domain":"report-format","prompt":"x","context":{},
        "expected":{"finding_types":["distribution_list_missing"]},
    }
    result={
        "contract_version":"2.0.7","id":"x","text":"2025/05，66号凭证。",
        "finding_types":["distribution_list_missing"],
        "conclusion_codes":["funds_occupied"],
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("report-format" in x and "conclusion_codes" in x for x in outcome.failures)
