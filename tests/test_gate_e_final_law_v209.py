import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    path = ROOT / "scripts" / "law_applicability.py"
    spec = importlib.util.spec_from_file_location("law_app_v209", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_law(rel):
    import yaml
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


def henan_service_law():
    return load_law("references/laws/henan/henan-gp-disp-other-municipal-gs-500k.yaml")


def base_context():
    return {
        "jurisdiction": {"country": "CN", "province": "Henan", "city": "Kaifeng"},
        "organization": {"level": "municipal", "type": "public_institution"},
        "event_date": "2025-06-01",
        "business_type": "service_procurement",
        "government_procurement_scope": True,
        "in_centralized_catalog": False,
        "amount": 800000,
    }


def test_mixed_project_funding_requires_review_without_transaction_attribution():
    m=load_module()
    ctx=base_context() | {"funding": ["fiscal_funds", "own_funds"]}
    result=m.evaluate_applicability(ctx, henan_service_law())
    assert result.status == "needs_review"
    assert any("混合" in reason or "归属" in reason for reason in result.reasons)


def test_source_record_funding_can_narrow_mixed_project_funding():
    m=load_module()
    project={
        "jurisdiction": {"country": "CN", "province": "Henan", "city": "Kaifeng"},
        "organization": {"level": "municipal", "type": "public_institution"},
        "funding": ["fiscal_funds", "own_funds"],
    }
    finding={
        "finding_id":"F-1","source_record_id":"SR-1","primary_category":"CG",
        "facts":"x","evidence_status":"confirmed","decision_status":"ready",
        "applicability_facts":{
            "business_type":"service_procurement",
            "government_procurement_scope":True,
            "in_centralized_catalog":False,
            "amount":800000,
        },
    }
    source={
        "source_record_id":"SR-1","source_type":"voucher",
        "event_date":"2025-06-01","funding":["fiscal_funds"],
    }
    ctx=m.build_evaluation_context(project,finding,source)
    assert ctx["funding"] == ["fiscal_funds"]
    assert m.evaluate_applicability(ctx,henan_service_law()).status == "applicable"


def test_source_record_own_funds_excludes_fiscal_only_law():
    m=load_module()
    project={
        "jurisdiction": {"country": "CN", "province": "Henan", "city": "Kaifeng"},
        "organization": {"level": "municipal", "type": "public_institution"},
        "funding": ["fiscal_funds", "own_funds"],
    }
    finding={
        "finding_id":"F-1","source_record_id":"SR-1","primary_category":"CG",
        "facts":"x","evidence_status":"confirmed","decision_status":"ready",
        "applicability_facts":{
            "business_type":"service_procurement",
            "government_procurement_scope":True,
            "in_centralized_catalog":False,
            "amount":800000,
        },
    }
    source={
        "source_record_id":"SR-1","source_type":"voucher",
        "event_date":"2025-06-01","funding":["own_funds"],
    }
    ctx=m.build_evaluation_context(project,finding,source)
    assert m.evaluate_applicability(ctx,henan_service_law()).status == "not_applicable"


def test_historical_law_without_start_date_fails_closed():
    m=load_module()
    law=load_law("references/laws/historical/cn-integrity-2010-hist.yaml")
    law["effective_from"]=None
    result=m.evaluate_applicability(
        {"jurisdiction":{"country":"CN"},"event_date":"2000-01-01"},
        law,
    )
    assert result.status == "needs_review"
    assert any("起始" in reason or "生效" in reason for reason in result.reasons)


def test_three_historical_objects_have_verified_start_dates():
    expected={
        "references/laws/historical/cn-admin-accounting-2013-hist.yaml":"2014-01-01",
        "references/laws/historical/cn-integrity-2010-hist.yaml":"2010-01-18",
        "references/laws/historical/cn-public-institution-accounting-2012-hist.yaml":"2013-01-01",
    }
    for rel,start in expected.items():
        assert load_law(rel)["effective_from"] == start


def test_historical_schema_requires_bounded_period():
    schema=json.loads((ROOT/"schemas/law.schema.json").read_text(encoding="utf-8"))
    law=load_law("references/laws/historical/cn-integrity-2010-hist.yaml")
    law["effective_from"]=None
    errors=list(Draft202012Validator(schema).iter_errors(law))
    assert errors


def test_official_verified_source_without_traceability_is_needs_review():
    m=load_module()
    law={
        "id":"TEST","status":"effective","effective_from":"2020-01-01","effective_to":None,
        "jurisdiction":{"country":"CN"},"subject_scope":{},"business_scope":[],"funding_scope":[],
        "applies_if":[],"excludes_if":[],
        "source":{"type":"official","verified":True,"url":None,"identifier":None},
    }
    result=m.evaluate_applicability(
        {"jurisdiction":{"country":"CN"},"event_date":"2025-01-01"},
        law,
    )
    assert result.status == "needs_review"
    assert any("追溯" in reason or "来源" in reason for reason in result.reasons)


@pytest.mark.parametrize("bad_date", ["not-a-date", 123])
def test_invalid_dates_fail_closed_instead_of_raising(bad_date):
    m=load_module()
    law={
        "id":"TEST","status":"effective","effective_from":bad_date,"effective_to":None,
        "jurisdiction":{"country":"CN"},"subject_scope":{},"business_scope":[],"funding_scope":[],
        "applies_if":[],"excludes_if":[],
        "source":{"type":"official","verified":True,"url":"https://example.invalid","identifier":None},
    }
    result=m.evaluate_applicability(
        {"jurisdiction":{"country":"CN"},"event_date":"2025-01-01"},
        law,
    )
    assert result.status == "needs_review"


@pytest.mark.parametrize("operator", ["in", "not_in"])
def test_invalid_membership_condition_types_fail_closed(operator):
    m=load_module()
    law={
        "id":"TEST","status":"effective","effective_from":"2020-01-01","effective_to":None,
        "jurisdiction":{"country":"CN"},"subject_scope":{},"business_scope":[],"funding_scope":[],
        "applies_if":[{"field":"person_type","operator":operator,"value":123}],
        "excludes_if":[],
        "source":{"type":"official","verified":True,"url":"https://example.invalid","identifier":None},
    }
    result=m.evaluate_applicability(
        {"jurisdiction":{"country":"CN"},"event_date":"2025-01-01","person_type":"ordinary_employee"},
        law,
    )
    assert result.status == "needs_review"
    assert any("类型" in reason for reason in result.reasons)


def test_source_record_schema_accepts_item_level_funding_and_rejects_negative_voucher():
    schema=json.loads((ROOT/"schemas/source-record.schema.json").read_text(encoding="utf-8"))
    good={"source_record_id":"SR-1","source_type":"voucher","voucher_amount":100,"funding":["fiscal_funds"]}
    assert not list(Draft202012Validator(schema).iter_errors(good))
    bad=good|{"voucher_amount":-1}
    assert list(Draft202012Validator(schema).iter_errors(bad))
