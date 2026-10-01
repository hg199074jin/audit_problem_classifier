import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "evals" / "cases"
SCORER = ROOT / "evals" / "score.py"

SEMANTIC_FIELDS = {
    "gate_status",
    "category",
    "finding_types",
    "conclusion_codes",
    "applicability_status",
    "law_ids",
    "excluded_law_ids",
    "record_count",
    "finding_count",
    "voucher_total",
    "law_roles",
}


def load_scorer():
    spec = importlib.util.spec_from_file_location("audit_eval_score_v201", SCORER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_cases():
    rows = []
    for path in sorted(CASE_DIR.glob("*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                rows.append(json.loads(raw))
    return rows


def test_non_format_cases_use_structured_semantics_not_literal_prose_assertions():
    for case in load_cases():
        if case["domain"] == "report-format":
            continue
        expected = case["expected"]
        assert "contains" not in expected, case["id"]
        assert "not_contains" not in expected, case["id"]
        assert not case.get("forbidden"), case["id"]
        assert SEMANTIC_FIELDS & expected.keys(), case["id"]


def test_runtime_contract_fields_are_scored_structurally():
    scorer = load_scorer()
    case = {
        "contract_version": "2.0.9",
        "id": "semantic",
        "domain": "law-applicability",
        "prompt": "x",
        "context": {},
        "expected": {
            "gate_status": "proceed",
            "applicability_status": "not_applicable",
            "finding_types": ["tax_issue"],
            "conclusion_codes": ["future_law_not_direct_basis"],
            "law_ids": ["CN-INVOICE-2023-ART20"],
            "law_roles": {"CN-INVOICE-2023-ART20": "direct_basis"},
            "excluded_law_ids": ["CN-INVOICE-2010-ART21-HIST"],
        },
    }
    result = {
        "contract_version": "2.0.9",
        "id": "semantic",
        "text": "措辞完全自由，不要求固定短语。",
        "gate_status": "proceed",
        "applicability_status": "not_applicable",
        "finding_types": ["tax_issue"],
        "conclusion_codes": ["future_law_not_direct_basis"],
        "law_ids": ["CN-INVOICE-2023-ART20"],
        "law_roles": {"CN-INVOICE-2023-ART20": "direct_basis"},
        "excluded_law_ids": ["CN-INVOICE-2010-ART21-HIST"],
    }
    outcome = scorer.score_case(case, result)
    assert outcome.passed, outcome.failures


def test_semantic_forbidden_word_in_negated_prose_does_not_fail_without_structured_violation():
    scorer = load_scorer()
    case = {
        "contract_version": "2.0.9",
        "id": "negation",
        "domain": "evidence-wording",
        "prompt": "x",
        "context": {},
        "expected": {
            "finding_types": ["procurement_quote_collusion_suspected"],
            "conclusion_codes": ["collusive_bidding_not_established"],
        },
    }
    result = {
        "contract_version": "2.0.9",
        "id": "negation",
        "text": "现有证据不能认定构成串通投标。",
        "finding_types": ["procurement_quote_collusion_suspected"],
        "conclusion_codes": ["collusive_bidding_not_established"],
    }
    outcome = scorer.score_case(case, result)
    assert outcome.passed, outcome.failures


def test_structured_excluded_law_ids_are_required_when_expected():
    scorer = load_scorer()
    case = {
        "contract_version": "2.0.9",
        "id": "law",
        "domain": "law-applicability",
        "prompt": "x",
        "context": {},
        "expected": {
            "law_ids": ["CN-INVOICE-2023-ART20"],
            "law_roles": {"CN-INVOICE-2023-ART20": "direct_basis"},
            "excluded_law_ids": ["CN-INVOICE-2010-ART21-HIST"],
        },
    }
    bad = {
        "contract_version": "2.0.9",
        "id": "law",
        "text": "旧法不得引用。",
        "law_ids": ["CN-INVOICE-2023-ART20"],
        "law_roles": {"CN-INVOICE-2023-ART20": "direct_basis"},
        "excluded_law_ids": [],
    }
    outcome = scorer.score_case(case, bad)
    assert not outcome.passed
    assert any("excluded_law_ids" in failure for failure in outcome.failures)


def test_literal_text_checks_are_rejected_outside_report_format_domain():
    scorer = load_scorer()
    case = {
        "contract_version": "2.0.9",
        "id": "bad-contract",
        "domain": "classification",
        "prompt": "x",
        "context": {},
        "expected": {
            "text_checks": {"contains": ["固定措辞"]}
        },
    }
    result = {"contract_version": "2.0.9", "id": "bad-contract", "text": "固定措辞"}
    outcome = scorer.score_case(case, result)
    assert not outcome.passed
    assert any("text_checks" in failure for failure in outcome.failures)
