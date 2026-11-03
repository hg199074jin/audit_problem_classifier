import json
from copy import deepcopy
from pathlib import Path

import yaml
import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
FIXTURE_DIR = ROOT / "tests" / "fixtures"

SCHEMA_FIXTURES = {
    "project-context": "valid-project-context.yaml",
    "source-record": "valid-source-record.yaml",
    "finding": "valid-finding.yaml",
    "law": "valid-law.yaml",
}


def load_schema(name):
    path = SCHEMA_DIR / f"{name}.schema.json"
    assert path.exists(), f"missing schema: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixture(filename):
    path = FIXTURE_DIR / filename
    assert path.exists(), f"missing fixture: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def errors_for(schema_name, value):
    validator = Draft202012Validator(load_schema(schema_name))
    return sorted(validator.iter_errors(value), key=lambda e: list(e.path))


def test_all_valid_fixtures_pass_their_schemas():
    for schema_name, filename in SCHEMA_FIXTURES.items():
        fixture = load_fixture(filename)
        assert errors_for(schema_name, fixture) == []


def test_law_requires_status_verified_at_and_source():
    law = load_fixture("valid-law.yaml")
    for missing in ("status", "verified_at", "source"):
        candidate = deepcopy(law)
        candidate.pop(missing)
        assert errors_for("law", candidate), f"law without {missing} must fail"


def test_finding_requires_source_record_id():
    finding = load_fixture("valid-finding.yaml")
    finding.pop("source_record_id")
    assert errors_for("finding", finding)


def test_finding_supports_separate_amount_semantics():
    finding = load_fixture("valid-finding.yaml")
    finding["amounts"] = {
        "issue_amount": 6000,
        "confirmed_difference": 2000,
        "pending_amount": 4000,
    }
    assert errors_for("finding", finding) == []


def test_project_context_requires_jurisdiction_organization_and_audit_period():
    context = load_fixture("valid-project-context.yaml")
    for missing in ("jurisdiction", "organization", "audit_period"):
        candidate = deepcopy(context)
        candidate.pop(missing)
        assert errors_for("project-context", candidate), f"context without {missing} must fail"


def test_validator_script_is_present():
    assert (ROOT / "scripts" / "validate_v2_data.py").exists()


def _load_validator_module():
    import importlib.util
    script = ROOT / "scripts" / "validate_v2_data.py"
    spec = importlib.util.spec_from_file_location("validate_v2_data", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validator_exposes_required_interface():
    module = _load_validator_module()
    assert hasattr(module, "load_data")
    assert hasattr(module, "load_schema")
    assert hasattr(module, "validate_file")


def test_validate_file_accepts_valid_law_fixture():
    module = _load_validator_module()
    module.validate_file(FIXTURE_DIR / "valid-law.yaml", "law")


def test_validator_rejects_invalid_iso_dates(tmp_path):
    module = _load_validator_module()
    context = load_fixture("valid-project-context.yaml")
    context["audit_period"]["start"] = "2025-13-40"
    path = tmp_path / "bad-context.yaml"
    path.write_text(yaml.safe_dump(context, allow_unicode=True), encoding="utf-8")
    with pytest.raises((ValidationError, ValueError)):
        module.validate_file(path, "project-context")


def test_validator_rejects_inverted_date_ranges(tmp_path):
    module = _load_validator_module()

    context = load_fixture("valid-project-context.yaml")
    context["audit_period"] = {"start": "2025-12-31", "end": "2025-01-01"}
    context_path = tmp_path / "inverted-context.yaml"
    context_path.write_text(yaml.safe_dump(context, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="audit_period"):
        module.validate_file(context_path, "project-context")

    law = load_fixture("valid-law.yaml")
    law["effective_from"] = "2025-12-31"
    law["effective_to"] = "2025-01-01"
    law_path = tmp_path / "inverted-law.yaml"
    law_path.write_text(yaml.safe_dump(law, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="effective"):
        module.validate_file(law_path, "law")


def test_finding_accepts_structured_applicability_facts():
    finding = load_fixture("valid-finding.yaml")
    finding["applicability_facts"] = {
        "business_type": "service_procurement",
        "person_type": "ordinary_employee",
        "service_provider_type": "individual",
        "invoice_noncompliant": True,
    }
    assert errors_for("finding", finding) == []


def test_project_context_can_capture_public_institution_management_status():
    context = load_fixture("valid-project-context.yaml")
    context["organization"]["civil_servant_managed"] = False
    assert errors_for("project-context", context) == []


def test_project_context_can_capture_administrative_function_status():
    context = load_fixture("valid-project-context.yaml")
    context["organization"]["performs_administrative_functions"] = True
    assert errors_for("project-context", context) == []
