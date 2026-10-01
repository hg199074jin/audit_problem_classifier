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


def test_v207_contract_version():
    schema=json.loads((ROOT/"evals/case.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "2.0.7"
    versions=set()
    for path in (ROOT/"evals/cases").glob("*.jsonl"):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                versions.add(json.loads(raw)["contract_version"])
    assert versions == {"2.0.7"}


def test_unknown_top_level_result_field_fails():
    scorer=load_scorer()
    case={
        "contract_version":"2.0.7","id":"x","domain":"classification","prompt":"x","context":{},
        "expected":{"conclusion_codes":["collusive_bidding_not_established"]},
    }
    result={
        "contract_version":"2.0.7","id":"x","text":"",
        "conclusion_codes":["collusive_bidding_not_established"],
        "unverified_law_requires_review": True,
    }
    outcome=scorer.score_case(case,result)
    assert not outcome.passed
    assert any("unknown top-level field" in item for item in outcome.failures)


def test_known_machine_fields_remain_valid():
    scorer=load_scorer()
    law_id="CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE"
    case={
        "contract_version":"2.0.7","id":"x","domain":"law-applicability","prompt":"x","context":{},
        "expected":{
            "law_ids":[law_id],
            "law_roles":{law_id:"supporting_basis"},
        },
    }
    result={
        "contract_version":"2.0.7","id":"x","text":"",
        "gate_status":"proceed",
        "applicability_status":"applicable",
        "law_ids":[law_id],
        "law_roles":{law_id:"supporting_basis"},
        "conclusion_codes":["official_vehicle_public_institution_principle_applies"],
    }
    outcome=scorer.score_case(case,result)
    assert outcome.passed, outcome.failures


def test_result_contract_forbids_orchestrator_filtering_unknown_keys():
    text=(ROOT/"rules/result-contract.md").read_text(encoding="utf-8")
    assert "不得过滤、删除、重命名或修复 runtime 原始顶层键" in text
    assert "未知顶层键" in text
    assert "只允许机械新增 `id` 和 `contract_version`" in text


def test_law_roles_mapping_remains_canonical():
    text=(ROOT/"rules/result-contract.md").read_text(encoding="utf-8")
    assert '"law_roles": {' in text
    assert "law_id → role" in text or "law_id→role" in text
