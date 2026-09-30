import json
from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

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
        "voucher_amount": 10000,
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
