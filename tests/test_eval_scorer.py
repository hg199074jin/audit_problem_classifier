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
        "contract_version": "2.0.3",
        "id": "case-1",
        "domain": "classification",
        "prompt": "x",
        "context": {},
        "expected": {
            "category": "FY",
            "finding_types": ["expense_supporting_documents_incomplete"],
        },
    }


def base_result():
    return {
        "contract_version": "2.0.3",
        "id": "case-1",
        "text": "正文可以自由表述。",
        "category": "FY",
        "finding_types": ["expense_supporting_documents_incomplete"],
    }


def assert_pass(case, result):
    module = load_module()
    outcome = module.score_case(case, result)
    assert outcome.passed, outcome.failures


def assert_fail(case, result, fragment):
    module = load_module()
    outcome = module.score_case(case, result)
    assert not outcome.passed
    assert any(fragment in failure for failure in outcome.failures), outcome.failures


def test_structured_fields_are_scored_without_prose_dependency():
    assert_pass(base_case(), base_result())
    bad = base_result() | {"category": "KJ"}
    assert_fail(base_case(), bad, "category")


def test_structured_list_expectations_use_exact_set_checks():
    case = base_case()
    result = base_result() | {
        "finding_types": [
            "expense_supporting_documents_incomplete",
            "expense_supporting_documents_nonstandard",
        ]
    }
    assert_fail(case, result, "exact set")


def test_contract_version_must_match_when_case_is_versioned():
    bad = base_result() | {"contract_version": "2.0"}
    assert_fail(base_case(), bad, "contract_version")


def test_record_finding_counts_and_voucher_total_are_structured_assertions():
    case = base_case()
    case["expected"] = {"record_count": 1, "finding_count": 3, "voucher_total": 10000}
    result = {"contract_version": "2.0.3", "id": "case-1", "text": "", "record_count": 1, "finding_count": 3, "voucher_total": 10000}
    assert_pass(case, result)

    bad = result | {"voucher_total": 30000}
    assert_fail(case, bad, "voucher_total")


def test_report_format_text_checks_are_allowed_only_in_report_format_domain():
    case = {
        "contract_version": "2.0.3",
        "id": "fmt",
        "domain": "report-format",
        "prompt": "x",
        "context": {},
        "expected": {
            "text_checks": {
                "contains": ["2025/05"],
                "not_contains": ["2025.5.31"],
            }
        },
    }
    result = {
        "contract_version": "2.0.3",
        "id": "fmt",
        "text": "2025/05，66号凭证。",
    }
    assert_pass(case, result)

    case["domain"] = "classification"
    assert_fail(case, result, "text_checks")


def test_format_lint_is_applied_to_report_format_case():
    case = {
        "contract_version": "2.0.3",
        "id": "fmt",
        "domain": "report-format",
        "prompt": "x",
        "context": {},
        "expected": {
            "format_forbid": [
                "ascii_chinese_quotes",
                "unnormalized_voucher_reference",
                "raw_dot_date",
            ]
        },
    }
    good = {
        "contract_version": "2.0.3",
        "id": "fmt",
        "text": "2025/05，66号凭证，列支“纪念水壶”。",
    }
    assert_pass(case, good)

    bad = good | {"text": '2025.5.31，记账-66号凭证，列支 "纪念水壶"。'}
    assert_fail(case, bad, "format_forbid")


def test_legacy_prose_semantic_assertions_are_rejected():
    case = base_case()
    case["expected"] = {"contains": ["固定措辞"]}
    result = base_result() | {"text": "固定措辞"}
    assert_fail(case, result, "legacy prose")


def test_missing_result_id_fails_score_all():
    module = load_module()
    report = module.score_all([base_case()], [])
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
