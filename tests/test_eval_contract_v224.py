"""V2.2.4 scorer global audit-object contract tests (RED first).

The scorer independently re-verifies audit objects against the case source
(global, not expected-dependent): an invoice finding without a verified
authorized_sw object is a failure, regardless of what `expected` says.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

P2_PROMPT = (
    "报销发票记载的购买方信息与实际报销单位存在不一致，但交易真实、货物确已取得，"
    "目前没有虚构交易、无真实业务开票或其他虚开发票证据。请定性。"
)


def load_scorer():
    spec = importlib.util.spec_from_file_location("score_v224", ROOT / "evals" / "score.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def p2_case():
    return {
        "contract_version": "2.2.4", "id": "x", "domain": "evidence-wording",
        "prompt": P2_PROMPT, "context": {},
    }


def verified_objects():
    return [{
        "object_id": "AO-1",
        "source_record_id": None,
        "object_kind": "invoice_compliance",
        "directness": "primary",
        "decision": "authorized_sw",
        "assertions": [
            {"assertion_kind": "invoice_buyer_mismatch", "polarity": "affirmative",
             "source_id": "prompt", "quote": "购买方信息与实际报销单位存在不一致"},
            {"assertion_kind": "explicit_invoice_characterization_request", "polarity": "affirmative",
             "source_id": "prompt", "quote": "请定性"},
        ],
    }]


def sw_result(objects):
    result = {
        "contract_version": "2.2.4", "id": "x", "text": "",
        "gate_status": "proceed",
        "category": "SW",
        "finding_types": ["invoice_information_irregularity"],
        "conclusion_codes": ["invoice_irregularity_not_false_invoicing_established"],
    }
    if objects is not None:
        result["audit_objects"] = objects
    return result


def test_sw_with_verified_objects_passes():
    scorer = load_scorer()
    case = p2_case()
    case["expected"] = {
        "conclusion_codes": ["invoice_irregularity_not_false_invoicing_established"]
    }
    outcome = scorer.score_case(case, sw_result(verified_objects()))
    assert outcome.passed, outcome.failures


def test_sw_without_audit_objects_fails_globally():
    """Global check, independent of expected: invoice finding needs a verified
    authorized_sw object."""
    scorer = load_scorer()
    case = p2_case()
    case["expected"] = {}
    outcome = scorer.score_case(case, sw_result(None))
    assert not outcome.passed
    assert any("SW_WITHOUT_AUTHORIZED_OBJECT" in f for f in outcome.failures)


def test_sw_with_fabricated_quote_fails():
    scorer = load_scorer()
    objects = verified_objects()
    objects[0]["assertions"][0]["quote"] = "购买方信息完全错误"
    case = p2_case()
    case["expected"] = {}
    outcome = scorer.score_case(case, sw_result(objects))
    assert not outcome.passed
    assert any("AUDIT_OBJECT_UNVERIFIED" in f or "QUOTE_NOT_IN_SOURCE" in f for f in outcome.failures)


def test_sw_with_unauthorized_decision_fails():
    scorer = load_scorer()
    objects = verified_objects()
    objects[0]["decision"] = "candidate"
    case = p2_case()
    case["expected"] = {}
    outcome = scorer.score_case(case, sw_result(objects))
    assert not outcome.passed
    assert any("DECISION_MISMATCH" in f for f in outcome.failures), outcome.failures


def test_scorer_refuses_self_authorized_object_missing_focus():
    """F-002: scorer re-derives the gate decision; a defect-only object with
    self-filled authorized_sw cannot make an SW result pass."""
    scorer = load_scorer()
    rogue = verified_objects()
    rogue[0]["assertions"] = [rogue[0]["assertions"][0]]  # defect only, no focus
    case = p2_case()
    case["expected"] = {"conclusion_codes": ["invoice_irregularity_not_false_invoicing_established"]}
    outcome = scorer.score_case(case, sw_result(rogue))
    assert not outcome.passed
    assert any(
        "DECISION_MISMATCH" in f or "SW_WITHOUT_AUTHORIZED_OBJECT" in f
        for f in outcome.failures
    ), outcome.failures


def test_fy_without_objects_passes():
    scorer = load_scorer()
    case = {"contract_version": "2.2.4", "id": "y", "domain": "classification",
            "prompt": "水费维修费报销有的缺少明细有的发票抬头不一致。请分类。", "context": {},
            "expected": {}}
    result = {"contract_version": "2.2.4", "id": "y", "text": "",
              "category": "FY",
              "finding_types": ["expense_supporting_documents_nonstandard"]}
    outcome = scorer.score_case(case, result)
    assert outcome.passed, outcome.failures


def test_invoice_finding_type_alone_triggers_object_requirement():
    """category may be absent but the invoice finding type alone is an
    invoice claim."""
    scorer = load_scorer()
    case = p2_case()
    case["expected"] = {}
    result = sw_result(None)
    result["category"] = "FY"
    outcome = scorer.score_case(case, result)
    assert not outcome.passed
    assert any("SW_WITHOUT_AUTHORIZED_OBJECT" in f for f in outcome.failures)


def test_honest_context_attribution_passes():
    """F-004: a fact that lives in context and is honestly attributed to
    source_id=context must verify (scorer rebuilds both buckets)."""
    scorer = load_scorer()
    case = {
        "contract_version": "2.2.4", "id": "z", "domain": "evidence-wording",
        "prompt": "请对该发票问题定性。",
        "context": {"invoice_fact": "购买方信息与实际报销单位存在不一致"},
        "expected": {"conclusion_codes": ["invoice_irregularity_not_false_invoicing_established"]},
    }
    objects = [{
        "object_id": "AO-1", "source_record_id": None,
        "object_kind": "invoice_compliance", "directness": "primary",
        "decision": "authorized_sw",
        "assertions": [
            {"assertion_kind": "invoice_buyer_mismatch", "polarity": "affirmative",
             "source_id": "context", "quote": "购买方信息与实际报销单位存在不一致"},
            {"assertion_kind": "explicit_invoice_characterization_request", "polarity": "affirmative",
             "source_id": "prompt", "quote": "请对该发票问题定性"},
        ],
    }]
    outcome = scorer.score_case(case, sw_result(objects))
    assert outcome.passed, outcome.failures
