import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCORER = ROOT / "evals" / "score.py"


def load_module():
    assert SCORER.exists(), "missing evals/score.py"
    spec = importlib.util.spec_from_file_location("audit_eval_score", SCORER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_case():
    return {
        "id": "case-1",
        "domain": "test",
        "prompt": "x",
        "context": {},
        "expected": {"contains": ["应出现"]},
        "forbidden": ["禁止词"],
    }


def base_result():
    return {"id": "case-1", "text": "这里应出现正确措辞"}


def assert_pass(case, result):
    module = load_module()
    outcome = module.score_case(case, result)
    assert outcome.passed, outcome.failures


def assert_fail(case, result, fragment):
    module = load_module()
    outcome = module.score_case(case, result)
    assert not outcome.passed
    assert any(fragment in failure for failure in outcome.failures), outcome.failures


def test_contains_and_not_contains_and_forbidden_are_checked_against_text():
    case = base_case()
    case["expected"]["not_contains"] = ["错误结论"]
    assert_pass(case, base_result())

    bad = base_result() | {"text": "应出现，但错误结论也出现"}
    assert_fail(case, bad, "not_contains")

    bad = base_result() | {"text": "应出现，但包含禁止词"}
    assert_fail(case, bad, "forbidden")


def test_structured_category_and_law_ids_do_not_pass_from_prose_only():
    case = base_case()
    case["expected"] = {"category": "FY", "law_ids": ["LAW-1"]}
    prose_only = {"id": "case-1", "text": "FY LAW-1"}
    assert_fail(case, prose_only, "category")

    structured = {"id": "case-1", "text": "", "category": "FY", "law_ids": ["LAW-1", "LAW-2"]}
    assert_pass(case, structured)


def test_record_finding_counts_and_voucher_total_are_structured_assertions():
    case = base_case()
    case["expected"] = {"record_count": 1, "finding_count": 3, "voucher_total": 10000}
    result = {"id": "case-1", "text": "", "record_count": 1, "finding_count": 3, "voucher_total": 10000}
    assert_pass(case, result)

    bad = result | {"voucher_total": 30000}
    assert_fail(case, bad, "voucher_total")


def test_missing_result_id_fails_score_all():
    module = load_module()
    case = base_case()
    report = module.score_all([case], [])
    assert not report.passed
    assert any("missing result" in failure for failure in report.failures)


def test_duplicate_result_id_is_rejected(tmp_path):
    module = load_module()
    path = tmp_path / "results.jsonl"
    path.write_text(
        json.dumps(base_result(), ensure_ascii=False) + "\n" + json.dumps(base_result(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate result id"):
        module.load_results(path)


def test_case_directory_loader_rejects_duplicate_case_ids(tmp_path):
    module = load_module()
    (tmp_path / "a.jsonl").write_text(json.dumps(base_case(), ensure_ascii=False) + "\n", encoding="utf-8")
    (tmp_path / "b.jsonl").write_text(json.dumps(base_case(), ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate case id"):
        module.load_cases(tmp_path)
