import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_scorer():
    path = ROOT / "evals" / "score.py"
    spec = importlib.util.spec_from_file_location("score_v209", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_cases():
    cases={}
    for path in (ROOT/"evals/cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                row=json.loads(raw)
                cases[row["id"]]=row
    return cases


def test_v209_contract_version_and_law_roles_schema():
    schema=json.loads((ROOT/"evals/case.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "2.1.1"
    roles=schema["properties"]["expected"]["properties"]["law_roles"]
    assert roles["type"] == "object"
    assert roles["additionalProperties"]["enum"] == [
        "direct_basis","supporting_basis","liability_basis"
    ]


def test_law_roles_mapping_is_accepted():
    scorer=load_scorer()
    law_id="CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE"
    case={
        "contract_version":"2.1.1","id":"x","domain":"law-applicability","prompt":"x","context":{},
        "expected":{
            "law_ids":[law_id],
            "law_roles":{law_id:"supporting_basis"},
        },
    }
    result={
        "contract_version":"2.1.1","id":"x","text":"",
        "law_ids":[law_id],
        "law_roles":{law_id:"supporting_basis"},
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures


def test_law_roles_array_shape_is_rejected():
    scorer=load_scorer()
    law_id="CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE"
    case={
        "contract_version":"2.1.1","id":"x","domain":"law-applicability","prompt":"x","context":{},
        "expected":{"law_ids":[law_id],"law_roles":{law_id:"supporting_basis"}},
    }
    result={
        "contract_version":"2.1.1","id":"x","text":"",
        "law_ids":[law_id],
        "law_roles":["supporting_basis"],
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("law_roles" in x and "object" in x for x in outcome.failures)


def test_law_role_mapping_keys_must_be_selected_law_ids():
    scorer=load_scorer()
    selected="CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE"
    extra="CN-OFFICIAL-VEHICLE-2017"
    case={
        "contract_version":"2.1.1","id":"x","domain":"law-applicability","prompt":"x","context":{},
        "expected":{"law_ids":[selected]},
    }
    result={
        "contract_version":"2.1.1","id":"x","text":"",
        "law_ids":[selected],
        "law_roles":{extra:"supporting_basis"},
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("law_roles keys" in x for x in outcome.failures)


def test_unknown_role_value_is_rejected():
    scorer=load_scorer()
    law_id="CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE"
    case={
        "contract_version":"2.1.1","id":"x","domain":"law-applicability","prompt":"x","context":{},
        "expected":{"law_ids":[law_id]},
    }
    result={
        "contract_version":"2.1.1","id":"x","text":"",
        "law_ids":[law_id],
        "law_roles":{law_id:"mystery_basis"},
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("unknown role" in x or "schema/type" in x for x in outcome.failures)


def test_official_vehicle_case_uses_mapping_shape():
    case=load_cases()["p1-official-vehicle-public-institution-principle"]
    law_id="CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE"
    assert case["expected"]["law_roles"] == {law_id:"supporting_basis"}
    assert "law_roles" not in set(case["expected"].get("exact_fields") or [])


def test_liability_not_default_case_uses_empty_mapping():
    case=load_cases()["p1-liability-basis-not-default"]
    assert case["expected"]["law_roles"] == {}


def test_result_contract_contains_canonical_mapping_example():
    text=(ROOT/"rules"/"result-contract.md").read_text(encoding="utf-8")
    assert '"law_roles": {' in text
    assert '"CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE": "supporting_basis"' in text
