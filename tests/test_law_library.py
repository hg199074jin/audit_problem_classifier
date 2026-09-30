import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
LAW_ROOT = ROOT / "references" / "laws"
SCHEMA = ROOT / "schemas" / "law.schema.json"

MANDATORY_CURRENT_IDS = {
    "CN-INVOICE-2023-ART20", "CN-OFFICIAL-VEHICLE-2017",
    "CN-APPRAISAL-COMMENDATION-2018", "CN-INTEGRITY-2015",
    "CN-GOV-ACCOUNTING-2017", "CN-BASIC-CONSTRUCTION-FINANCE-2016",
    "CN-GOV-PURCHASE-SERVICES-2020-ART18", "CN-CIVIL-SERVANT-REWARD-2020",
    "HENAN-GP-2020-DISP-PROVINCE-GS-1M", "HENAN-GP-2020-DISP-ZHENGZHOU-GS-1M",
    "HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K", "HENAN-GP-2020-DISP-COUNTY-GS-300K",
    "HENAN-GP-2020-TENDER-PROVINCE-GS-4M", "HENAN-GP-2020-TENDER-ZHENGZHOU-GS-4M",
    "HENAN-GP-2020-TENDER-OTHER-MUNICIPAL-GS-2M", "HENAN-GP-2020-TENDER-COUNTY-GS-2M",
}
MANDATORY_HISTORICAL_IDS = {
    "CN-INVOICE-2010-ART21-HIST", "CN-OFFICIAL-VEHICLE-2011-HIST",
    "CN-APPRAISAL-COMMENDATION-2010-HIST", "CN-INTEGRITY-2010-HIST",
    "CN-ADMIN-ACCOUNTING-2013-HIST", "CN-PUBLIC-INSTITUTION-ACCOUNTING-2012-HIST",
    "CN-BASIC-CONSTRUCTION-FINANCE-2002-HIST",
}

def law_files():
    assert LAW_ROOT.exists(), f"missing structured law root: {LAW_ROOT}"
    files = sorted(p for p in LAW_ROOT.rglob("*.yaml") if p.is_file())
    assert files, "structured law library is empty"
    return files

def load_schema():
    return json.loads(SCHEMA.read_text(encoding="utf-8"))

def load_law(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} must contain one law object"
    return data

def test_every_structured_law_validates_and_has_verified_source():
    validator = Draft202012Validator(load_schema())
    for path in law_files():
        law = load_law(path)
        errors = list(validator.iter_errors(law))
        assert not errors, f"{path}: {errors[0].message if errors else ''}"
        assert law["verified_at"], f"{path}: verified_at required"
        source = law["source"]
        assert source.get("verified") is True, f"{path}: source must be verified"
        assert source.get("url") or source.get("identifier"), f"{path}: official source URL or identifier required"
        assert source.get("type") in {"official", "official_archive"}, f"{path}: initial P0 library must use official sources"

def test_historical_directory_never_marks_items_effective():
    historical = LAW_ROOT / "historical"
    assert historical.exists(), "historical directory required"
    files = sorted(historical.glob("*.yaml"))
    assert files, "historical directory must contain migrated retired rules"
    for path in files:
        assert load_law(path)["status"] != "effective", f"{path}: historical item marked effective"

def test_law_ids_are_unique():
    ids = []
    for path in law_files():
        law_id = load_law(path).get("id")
        assert law_id, f"{path}: id required"
        ids.append(law_id)
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    assert not duplicates, f"duplicate law ids: {duplicates}"

def test_all_mandatory_p0_current_and_historical_groups_exist():
    ids = {load_law(path)["id"] for path in law_files()}
    assert not (MANDATORY_CURRENT_IDS - ids), f"missing current P0 law objects: {sorted(MANDATORY_CURRENT_IDS - ids)}"
    assert not (MANDATORY_HISTORICAL_IDS - ids), f"missing historical P0 law objects: {sorted(MANDATORY_HISTORICAL_IDS - ids)}"

def test_henan_threshold_rules_encode_non_leaking_scopes():
    laws = {load_law(path)["id"]: load_law(path) for path in law_files()}
    other_city = laws["HENAN-GP-2020-DISP-OTHER-MUNICIPAL-GS-500K"]
    assert other_city["jurisdiction"]["province"] == "Henan"
    assert other_city["subject_scope"]["organization_levels"] == ["municipal"]
    assert {c["field"] for c in other_city.get("excludes_if", [])} >= {"jurisdiction.city"}
    assert any(c["field"] == "amount" and c["operator"] == "gte" and c["value"] == 500000 for c in other_city.get("applies_if", []))
    county = laws["HENAN-GP-2020-DISP-COUNTY-GS-300K"]
    assert county["subject_scope"]["organization_levels"] == ["county"]
    assert any(c["field"] == "amount" and c["operator"] == "gte" and c["value"] == 300000 for c in county.get("applies_if", []))

    for law_id, law in laws.items():
        if law_id.startswith("HENAN-GP-2020-"):
            assert law["document_no"] == "豫财办〔2020〕4号", f"{law_id}: wrong document number"
            assert law["source"]["identifier"] == "豫财办〔2020〕4号"

def test_law_library_readme_exists():
    assert (LAW_ROOT / "README.md").exists()


def test_official_vehicle_public_institution_scope_is_conditioned():
    laws = {load_law(path)["id"]: load_law(path) for path in law_files()}
    direct = laws["CN-OFFICIAL-VEHICLE-2017"]
    assert direct["subject_scope"]["organization_types"] == ["administrative_unit"]

    principle = laws["CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE"]
    assert principle["subject_scope"]["organization_types"] == ["public_institution"]
    assert principle["rule_role"] == "supporting_basis"
    assert any(
        c["field"] == "organization.civil_servant_managed"
        and c["operator"] == "eq"
        and c["value"] is False
        for c in principle["applies_if"]
    )


def test_watchlist_has_documented_entrypoint():
    assert (LAW_ROOT / "watchlist" / "README.md").exists()


def test_government_purchase_service_rules_condition_public_institution_reference():
    laws = {load_law(path)["id"]: load_law(path) for path in law_files()}

    for article in ("ART10", "ART18"):
        direct = laws[f"CN-GOV-PURCHASE-SERVICES-2020-{article}"]
        assert direct["subject_scope"]["organization_types"] == ["administrative_unit"]

        ref = laws[f"CN-GOV-PURCHASE-SERVICES-2020-{article}-PUBLIC-INSTITUTION-REF"]
        assert ref["subject_scope"]["organization_types"] == ["public_institution"]
        assert ref["funding_scope"] == ["fiscal_funds"]
        assert any(
            c["field"] == "organization.performs_administrative_functions"
            and c["operator"] == "eq"
            and c["value"] is True
            for c in ref["applies_if"]
        )

    art18 = laws["CN-GOV-PURCHASE-SERVICES-2020-ART18-PUBLIC-INSTITUTION-REF"]
    assert any(
        c["field"] == "service_provider_type"
        and c["operator"] == "eq"
        and c["value"] == "individual"
        for c in art18["applies_if"]
    )
