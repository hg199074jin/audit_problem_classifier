import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_scorer():
    path=ROOT/"evals"/"score.py"
    spec=importlib.util.spec_from_file_location("score_gate_e_final",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def case(expected=None, domain="law-applicability", context=None):
    return {
        "contract_version":"2.1.1","id":"x","domain":domain,"prompt":"x",
        "context":context or {},
        "expected":expected or {"conclusion_codes":["liability_basis_not_default"]},
    }


def test_result_schema_exists_and_contract_is_v209():
    schema=json.loads((ROOT/"evals"/"result.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "2.1.1"
    assert schema["additionalProperties"] is False


def test_malformed_known_field_types_fail_without_exception():
    scorer=load_scorer()
    malformed=[
        {"contract_version":"2.1.1","id":"x","text":"","law_ids":""},
        {"contract_version":"2.1.1","id":"x","text":"","finding_types":0},
        {"contract_version":"2.1.1","id":"x","text":"","record_count":"1"},
    ]
    for result in malformed:
        outcome=scorer.score_case(case(expected={}),result)
        assert not outcome.passed
        assert any("schema" in failure.lower() or "type" in failure.lower() for failure in outcome.failures)


def test_selected_laws_require_complete_role_mapping():
    scorer=load_scorer()
    law_id="CN-INVOICE-2023-ART20"
    result={
        "contract_version":"2.1.1","id":"x","text":"",
        "law_ids":[law_id],
    }
    outcome=scorer.score_case(case(expected={"law_ids":[law_id]}),result)
    assert not outcome.passed
    assert any("law_roles" in failure and "complete" in failure for failure in outcome.failures)


def test_law_role_must_match_catalog_rule_role():
    scorer=load_scorer()
    law_id="CN-INVOICE-2023-ART20"
    result={
        "contract_version":"2.1.1","id":"x","text":"",
        "law_ids":[law_id],
        "law_roles":{law_id:"liability_basis"},
    }
    outcome=scorer.score_case(
        case(expected={"law_ids":[law_id],"law_roles":{law_id:"direct_basis"}}),
        result,
    )
    assert not outcome.passed
    assert any("rule_role" in failure for failure in outcome.failures)


def test_liability_not_requested_cannot_emit_liability_role():
    scorer=load_scorer()
    law_id="CN-INTEGRITY-2010-HIST"
    result={
        "contract_version":"2.1.1","id":"x","text":"",
        "law_ids":[law_id],
        "law_roles":{law_id:"liability_basis"},
        "conclusion_codes":["liability_basis_not_default"],
    }
    outcome=scorer.score_case(
        case(
            expected={"law_roles":{},"conclusion_codes":["liability_basis_not_default"]},
            context={"user_requested_liability_analysis":False},
        ),
        result,
    )
    assert not outcome.passed


def test_unexpected_substantive_conclusion_fails_but_diagnostic_review_code_may_be_extra():
    scorer=load_scorer()
    base={
        "contract_version":"2.1.1","id":"x","text":"",
        "conclusion_codes":["collusive_bidding_not_established"],
    }
    c=case(expected={"conclusion_codes":["collusive_bidding_not_established"]},domain="evidence-wording")
    safe=base|{"conclusion_codes":["collusive_bidding_not_established","unverified_law_requires_review"]}
    assert scorer.score_case(c,safe).passed

    bad=base|{"conclusion_codes":["collusive_bidding_not_established","funds_occupied"]}
    outcome=scorer.score_case(c,bad)
    assert not outcome.passed
    assert any("unexpected conclusion" in failure for failure in outcome.failures)


def test_unknown_top_level_still_fails_under_result_schema():
    scorer=load_scorer()
    result={
        "contract_version":"2.1.1","id":"x","text":"",
        "conclusion_codes":["liability_basis_not_default"],
        "bad_key":True,
    }
    outcome=scorer.score_case(case(),result)
    assert not outcome.passed
