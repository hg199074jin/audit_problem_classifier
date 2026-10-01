import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load_module(path: str, name: str):
    target = ROOT / path
    spec = importlib.util.spec_from_file_location(name, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_yaml(path: str):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_finding_facts_cannot_override_project_scope():
    module = load_module("scripts/law_applicability.py", "law_app_gatee")
    project = {
        "jurisdiction": {"country": "CN", "province": "Henan", "city": "Kaifeng"},
        "organization": {"level": "municipal", "type": "public_institution"},
        "audit_period": {"start": "2025-01-01", "end": "2025-12-31"},
        "funding": ["fiscal_funds"],
    }
    finding = {
        "finding_id": "F-1",
        "source_record_id": "SR-1",
        "primary_category": "CG",
        "facts": "x",
        "evidence_status": "confirmed",
        "decision_status": "ready",
        "applicability_facts": {
            "jurisdiction": {"country": "CN", "province": "Guangdong", "city": "Shenzhen"},
        },
    }
    with pytest.raises(ValueError, match="reserved"):
        module.build_evaluation_context(project, finding, {"source_record_id": "SR-1", "source_type": "voucher"})


def test_effective_law_without_start_fails_closed():
    module = load_module("scripts/law_applicability.py", "law_app_gatee_time")
    law = {
        "id": "TEST",
        "status": "effective",
        "effective_from": None,
        "effective_to": None,
        "jurisdiction": {"country": "CN"},
        "subject_scope": {},
        "business_scope": [],
        "funding_scope": [],
        "applies_if": [],
        "excludes_if": [],
        "source": {"type": "official", "verified": True, "url": "https://example.invalid"},
    }
    result = module.evaluate_applicability({"jurisdiction": {"country": "CN"}}, law)
    assert result.status == "needs_review"
    assert any("生效" in reason or "时效" in reason for reason in result.reasons)


def test_condition_type_mismatch_degrades_to_needs_review():
    module = load_module("scripts/law_applicability.py", "law_app_gatee_type")
    law = {
        "id": "TEST",
        "status": "effective",
        "effective_from": "2020-01-01",
        "effective_to": None,
        "jurisdiction": {"country": "CN"},
        "subject_scope": {},
        "business_scope": ["service_procurement"],
        "funding_scope": [],
        "applies_if": [{"field": "amount", "operator": "gte", "value": 500000}],
        "excludes_if": [],
        "source": {"type": "official", "verified": True, "url": "https://example.invalid"},
    }
    result = module.evaluate_applicability(
        {
            "jurisdiction": {"country": "CN"},
            "event_date": "2025-01-01",
            "business_type": "service_procurement",
            "amount": "800000",
        },
        law,
    )
    assert result.status == "needs_review"
    assert any("类型" in reason for reason in result.reasons)


def test_secondary_source_can_never_be_applicable_even_if_verified():
    module = load_module("scripts/law_applicability.py", "law_app_gatee_prov")
    law = {
        "id": "TEST",
        "status": "effective",
        "effective_from": "2020-01-01",
        "effective_to": None,
        "jurisdiction": {"country": "CN"},
        "subject_scope": {},
        "business_scope": [],
        "funding_scope": [],
        "applies_if": [],
        "excludes_if": [],
        "source": {"type": "secondary", "verified": True, "url": None, "identifier": None},
    }
    result = module.evaluate_applicability(
        {"jurisdiction": {"country": "CN"}, "event_date": "2025-01-01"},
        law,
    )
    assert result.status == "needs_review"


def test_henan_procurement_objects_are_scoped_and_use_correct_document_number():
    law_root = ROOT / "references" / "laws" / "henan"
    for path in law_root.glob("*.yaml"):
        law = load_yaml(str(path.relative_to(ROOT)))
        if not law["id"].startswith("HENAN-GP-2020-"):
            continue
        assert law["document_no"] == "豫财购〔2020〕4号"
        assert law["source"]["identifier"] == "豫财购〔2020〕4号"
        assert law["effective_from"] == "2020-03-09"
        assert set(law["subject_scope"]["organization_types"]) == {
            "administrative_unit",
            "public_institution",
            "social_organization",
        }
        assert law["funding_scope"] == ["fiscal_funds"]

    works = load_yaml("references/laws/henan/henan-gp-tender-works-delegated.yaml")
    assert works["rule_role"] == "supporting_basis"
    assert any(c["field"] == "government_procurement_scope" and c["value"] is True for c in works["applies_if"])


def test_henan_threshold_rejects_enterprise_own_funds():
    module = load_module("scripts/law_applicability.py", "law_app_gatee_henan")
    law = load_yaml("references/laws/henan/henan-gp-disp-other-municipal-gs-500k.yaml")
    result = module.evaluate_applicability(
        {
            "jurisdiction": {"country": "CN", "province": "Henan", "city": "Kaifeng"},
            "organization": {"level": "municipal", "type": "enterprise"},
            "funding": ["own_funds"],
            "event_date": "2025-06-01",
            "business_type": "service_procurement",
            "amount": 800000,
            "in_centralized_catalog": False,
        },
        law,
    )
    assert result.status == "not_applicable"


def test_finding_schema_makes_source_record_the_only_voucher_amount_owner():
    schema = json.loads((ROOT / "schemas" / "finding.schema.json").read_text(encoding="utf-8"))
    fixture = load_yaml("tests/fixtures/valid-finding.yaml")
    fixture.setdefault("amounts", {})["voucher_amount"] = 10000
    errors = list(Draft202012Validator(schema).iter_errors(fixture))
    assert errors


def test_finding_semantics_reject_pending_final_and_final_without_wording(tmp_path):
    validator = load_module("scripts/validate_v2_data.py", "validator_gatee")
    finding = load_yaml("tests/fixtures/valid-finding.yaml")

    bad = deepcopy(finding)
    bad["evidence_status"] = "pending"
    bad["decision_status"] = "final"
    bad["final_wording"] = "结论"
    p = tmp_path / "pending-final.yaml"
    p.write_text(yaml.safe_dump(bad, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError):
        validator.validate_file(p, "finding")

    bad = deepcopy(finding)
    bad["evidence_status"] = "confirmed"
    bad["decision_status"] = "final"
    bad["final_wording"] = None
    p = tmp_path / "final-no-wording.yaml"
    p.write_text(yaml.safe_dump(bad, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError):
        validator.validate_file(p, "finding")


def test_effective_law_validation_requires_official_traceable_source(tmp_path):
    validator = load_module("scripts/validate_v2_data.py", "validator_gatee_law")
    law = load_yaml("tests/fixtures/valid-law.yaml")
    law["source"] = {
        "type": "secondary",
        "authority": "secondary",
        "url": None,
        "identifier": None,
        "verified": True,
    }
    path = tmp_path / "bad-law.yaml"
    path.write_text(yaml.safe_dump(law, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError):
        validator.validate_file(path, "law")
