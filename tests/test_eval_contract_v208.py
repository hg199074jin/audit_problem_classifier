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


def test_v209_contract_version():
    schema=json.loads((ROOT/"evals/case.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "2.0.9"
    versions=set()
    for path in (ROOT/"evals/cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                versions.add(json.loads(raw)["contract_version"])
    assert versions == {"2.0.9"}


def test_empty_law_roles_pin_accepts_omission():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.9","id":"x","domain":"law-applicability","prompt":"x","context":{},
        "expected":{"law_roles":{},"conclusion_codes":["liability_basis_not_default"]},
    }
    result={
        "contract_version":"2.0.9","id":"x","text":"",
        "conclusion_codes":["liability_basis_not_default"],
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures


def test_empty_law_roles_pin_accepts_explicit_empty_object():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.9","id":"x","domain":"law-applicability","prompt":"x","context":{},
        "expected":{"law_roles":{},"conclusion_codes":["liability_basis_not_default"]},
    }
    result={
        "contract_version":"2.0.9","id":"x","text":"",
        "law_roles":{},
        "conclusion_codes":["liability_basis_not_default"],
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures


def test_empty_law_roles_pin_rejects_nonempty_mapping():
    scorer=load_scorer()
    law_id="CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE"
    case={
        "contract_version":"2.0.9","id":"x","domain":"law-applicability","prompt":"x","context":{},
        "expected":{"law_roles":{},"conclusion_codes":["liability_basis_not_default"]},
    }
    result={
        "contract_version":"2.0.9","id":"x","text":"",
        "law_ids":[law_id],
        "law_roles":{law_id:"liability_basis"},
        "conclusion_codes":["liability_basis_not_default"],
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("expected empty mapping" in item for item in outcome.failures)


def test_nonempty_law_roles_pin_remains_exact_mapping():
    scorer=load_scorer()
    law_id="CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE"
    case={
        "contract_version":"2.0.9","id":"x","domain":"law-applicability","prompt":"x","context":{},
        "expected":{"law_ids":[law_id],"law_roles":{law_id:"supporting_basis"}},
    }
    missing={
        "contract_version":"2.0.9","id":"x","text":"",
        "law_ids":[law_id],
    }
    outcome=scorer.score_case(case,missing)
    assert not outcome.passed
    assert any("expected object mapping" in item for item in outcome.failures)


def test_contract_documents_empty_pin_semantics():
    text=(ROOT/"rules/result-contract.md").read_text(encoding="utf-8")
    assert "空值 pin 断言空性" in text
    assert "缺省与显式 `{}`" in text
