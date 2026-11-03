import importlib.util
from copy import deepcopy
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "law_applicability.py"
RULE_PATH = ROOT / "rules" / "law-applicability.md"


def load_module():
    assert MODULE_PATH.exists()
    spec = importlib.util.spec_from_file_location("law_applicability", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_context():
    return {
        "jurisdiction": {"country": "CN", "province": "Henan", "city": "Kaifeng"},
        "organization": {"level": "municipal", "type": "public_institution"},
        "person_type": "ordinary_employee",
        "business_type": "service_procurement",
        "funding": ["fiscal_funds"],
        "invoice_noncompliant": True,
    }


def base_law():
    return {
        "id": "TEST-LAW",
        "status": "effective",
        "effective_from": "2024-01-01",
        "effective_to": None,
        "jurisdiction": {"country": "CN", "province": "Henan"},
        "subject_scope": {
            "organization_types": ["public_institution"],
            "organization_levels": ["municipal"],
            "person_types": ["ordinary_employee"],
        },
        "business_scope": ["service_procurement"],
        "funding_scope": ["fiscal_funds"],
        "applies_if": [],
        "excludes_if": [],
        "source": {"type": "official", "verified": True, "url": "https://example.invalid"},
    }


def evaluate(context=None, law=None, event_date=date(2025, 6, 1)):
    module = load_module()
    assert hasattr(module, "evaluate_applicability"), "missing evaluate_applicability"
    result = module.evaluate_applicability(context or base_context(), law or base_law(), event_date)
    assert hasattr(result, "status") and hasattr(result, "reasons")
    return result


def test_required_interface_exists():
    module = load_module()
    assert hasattr(module, "ApplicabilityResult")
    assert hasattr(module, "evaluate_applicability")
    assert RULE_PATH.exists()


def test_effective_period_filters_future_law():
    law = base_law()
    law["effective_from"] = "2026-01-01"
    result = evaluate(law=law, event_date=date(2025, 6, 1))
    assert result.status == "not_applicable"
    assert any("effective" in reason or "生效" in reason for reason in result.reasons)


def test_missing_event_date_needing_time_check_returns_needs_review():
    law = base_law()
    result = evaluate(law=law, event_date=None)
    assert result.status == "needs_review"


def test_historical_repealed_law_can_apply_inside_its_effective_period():
    law = base_law()
    law["status"] = "repealed"
    law["effective_from"] = "2020-01-01"
    law["effective_to"] = "2025-12-31"
    result = evaluate(law=law, event_date=date(2025, 6, 1))
    assert result.status == "applicable"


def test_jurisdiction_mismatch_is_not_applicable_and_missing_scope_fact_needs_review():
    law = base_law()
    law["jurisdiction"]["city"] = "Zhengzhou"
    mismatch = evaluate(law=law)
    assert mismatch.status == "not_applicable"

    context = base_context()
    context["jurisdiction"].pop("city")
    missing = evaluate(context=context, law=law)
    assert missing.status == "needs_review"


def test_subject_scope_filters_organization_level_type_and_person_type():
    law = base_law()
    law["subject_scope"]["organization_levels"] = ["provincial"]
    assert evaluate(law=law).status == "not_applicable"

    law = base_law()
    law["subject_scope"]["organization_types"] = ["enterprise"]
    assert evaluate(law=law).status == "not_applicable"

    law = base_law()
    law["subject_scope"]["person_types"] = ["cadre"]
    assert evaluate(law=law).status == "not_applicable"


def test_business_scope_and_funding_scope_filter_independently():
    law = base_law()
    law["business_scope"] = ["training"]
    assert evaluate(law=law).status == "not_applicable"

    law = base_law()
    law["funding_scope"] = ["union_funds"]
    assert evaluate(law=law).status == "not_applicable"


def test_missing_business_or_funding_fact_returns_needs_review_when_law_requires_it():
    context = base_context()
    context.pop("business_type")
    assert evaluate(context=context).status == "needs_review"

    context = base_context()
    context.pop("funding")
    assert evaluate(context=context).status == "needs_review"


def test_structured_conditions_are_evaluated_without_free_text_execution():
    law = base_law()
    law["applies_if"] = [{"field": "invoice_noncompliant", "operator": "eq", "value": True}]
    assert evaluate(law=law).status == "applicable"

    context = base_context()
    context["invoice_noncompliant"] = False
    assert evaluate(context=context, law=law).status == "not_applicable"

    context = base_context()
    context.pop("invoice_noncompliant")
    assert evaluate(context=context, law=law).status == "needs_review"


def test_exclusion_condition_blocks_when_true_and_needs_review_when_unknown():
    law = base_law()
    law["excludes_if"] = [{"field": "emergency_exception", "operator": "eq", "value": True}]
    context = base_context()
    context["emergency_exception"] = True
    assert evaluate(context=context, law=law).status == "not_applicable"

    context = base_context()
    assert evaluate(context=context, law=law).status == "needs_review"


def test_henan_procurement_level_boundaries_do_not_leak():
    context = base_context()

    province_rule = base_law()
    province_rule["subject_scope"]["organization_levels"] = ["provincial"]
    assert evaluate(context=context, law=province_rule).status == "not_applicable"

    zhengzhou_rule = base_law()
    zhengzhou_rule["jurisdiction"]["city"] = "Zhengzhou"
    assert evaluate(context=context, law=zhengzhou_rule).status == "not_applicable"

    other_municipal_rule = base_law()
    other_municipal_rule["subject_scope"]["organization_levels"] = ["municipal"]
    assert evaluate(context=context, law=other_municipal_rule).status == "applicable"

    county_rule = base_law()
    county_rule["subject_scope"]["organization_levels"] = ["county"]
    assert evaluate(context=context, law=county_rule).status == "not_applicable"


def test_rule_document_uses_same_three_state_vocabulary_and_filter_order():
    text = RULE_PATH.read_text(encoding="utf-8")
    for token in ("applicable", "not_applicable", "needs_review"):
        assert token in text
    order = ["时效", "地域", "主体", "事项", "资金", "事实/证据"]
    positions = [text.index(token) for token in order]
    assert positions == sorted(positions)


def test_unverified_source_never_returns_applicable():
    law = base_law()
    law["source"] = {"verified": False}
    result = evaluate(law=law)
    assert result.status == "needs_review"
    assert any("来源" in reason or "核验" in reason for reason in result.reasons)


def test_build_evaluation_context_merges_project_finding_and_source_record():
    module = load_module()
    assert hasattr(module, "build_evaluation_context")

    project = {
        "jurisdiction": {"country": "CN", "province": "Henan", "city": "Kaifeng"},
        "organization": {
            "level": "municipal",
            "type": "public_institution",
            "civil_servant_managed": False,
        },
        "audit_period": {"start": "2025-01-01", "end": "2025-12-31"},
        "funding": ["fiscal_funds"],
    }
    finding = {
        "finding_id": "F-1",
        "source_record_id": "SR-1",
        "primary_category": "CG",
        "facts": "采购服务",
        "evidence_status": "confirmed",
        "decision_status": "ready",
        "amounts": {"issue_amount": 800000},
        "applicability_facts": {
            "business_type": "service_procurement",
            "person_type": "ordinary_employee",
            "invoice_noncompliant": True,
        },
    }
    source_record = {"source_record_id": "SR-1", "source_type": "voucher", "event_date": "2025-06-01"}
    context = module.build_evaluation_context(project, finding, source_record)

    assert context["jurisdiction"]["city"] == "Kaifeng"
    assert context["organization"]["civil_servant_managed"] is False
    assert context["business_type"] == "service_procurement"
    assert context["person_type"] == "ordinary_employee"
    assert context["amount"] == 800000
    assert context["event_date"] == "2025-06-01"
    assert context["funding"] == ["fiscal_funds"]
