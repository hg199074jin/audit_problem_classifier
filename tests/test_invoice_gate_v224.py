"""V2.2.4 invoice object gate tests (RED first).

Production FY/SW split consumes VERIFIED audit objects only. The legacy
naked-bool entry (`invoice_split_gate`) remains as a pure internal function
but can no longer drive the production decision.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "classification_emission_v224", ROOT / "scripts" / "classification_emission.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def aog():
    spec = importlib.util.spec_from_file_location(
        "audit_object_grounding_v224", ROOT / "scripts" / "audit_object_grounding.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CASE10_PROMPT = (
    "报销发票记载的购买方信息与实际报销单位存在不一致，但交易真实、货物确已取得，"
    "目前没有虚构交易、无真实业务开票或其他虚开发票证据。请定性。"
)
SOURCES = {"prompt": CASE10_PROMPT, "context": ""}


def case10_objects():
    return [{
        "object_id": "AO-1",
        "source_record_id": None,
        "object_kind": "invoice_compliance",
        "directness": "primary",
        "assertions": [
            {"assertion_kind": "invoice_buyer_mismatch", "polarity": "affirmative",
             "source_id": "prompt", "quote": "购买方信息与实际报销单位存在不一致"},
            {"assertion_kind": "explicit_invoice_characterization_request", "polarity": "affirmative",
             "source_id": "prompt", "quote": "请定性"},
            {"assertion_kind": "true_transaction", "polarity": "affirmative",
             "source_id": "prompt", "quote": "交易真实"},
            {"assertion_kind": "false_invoicing_evidence_absent", "polarity": "negative",
             "source_id": "prompt",
             "quote": "目前没有虚构交易、无真实业务开票或其他虚开发票证据"},
        ],
    }]


def incidental_object():
    return [{
        "object_id": "AO-2",
        "source_record_id": "SR-1",
        "object_kind": "invoice_compliance",
        "directness": "incidental",
        "assertions": [
            {"assertion_kind": "issuer_payee_mismatch", "polarity": "affirmative",
             "source_id": "prompt", "quote": "开票单位与收款单位不一致"},
        ],
    }]


def test_case10_shape_authorizes_sw_with_restriction():
    eng = load_module()
    out = eng.invoice_object_gate(audit_objects=case10_objects(), sources=SOURCES)
    assert out["decision"] == "sw_independent"
    assert out["primary_class"] == "SW"
    assert out["emit_invoice_information_irregularity"] is True
    assert out["authorized_object_ids"] == ["AO-1"]
    assert "no_false_invoicing_finding" in out["restrictions"], (
        "negative evidence must become a conclusion restriction, not an authorizer"
    )


def test_expense_boundary_incidental_shape_stays_fy():
    eng = load_module()
    prompt = "某事业单位报销水费、维修费，其中有的发票开票单位与收款单位不一致。请分类并形成报告标题。"
    out = eng.invoice_object_gate(
        audit_objects=incidental_object(), sources={"prompt": prompt, "context": ""},
    )
    assert out["decision"] == "fy_incidental"
    assert out["emit_invoice_information_irregularity"] is False


def test_mode_integrated_noncompliant_object_authorizes_sw():
    eng = load_module()
    prompt = "某事业单位报销取得不符合规定的发票并作为财务报销凭证，交易真实。请形成完整审计问题报告。"
    objs = [{
        "object_id": "AO-3",
        "source_record_id": None,
        "object_kind": "invoice_compliance",
        "directness": "primary",
        "assertions": [
            {"assertion_kind": "noncompliant_invoice_obtained", "polarity": "affirmative",
             "source_id": "prompt", "quote": "取得不符合规定的发票并作为财务报销凭证"},
            {"assertion_kind": "true_transaction", "polarity": "affirmative",
             "source_id": "prompt", "quote": "交易真实"},
        ],
    }]
    out = eng.invoice_object_gate(audit_objects=objs, sources={"prompt": prompt, "context": ""})
    assert out["decision"] == "sw_independent"
    assert out["emit_invoice_information_irregularity"] is True


def test_negative_only_yields_no_invoice_finding():
    eng = load_module()
    prompt = "某单位一笔报销暂无虚开发票证据，无其他具体发票异常描述。请定性。"
    objs = [{
        "object_id": "AO-4",
        "source_record_id": None,
        "object_kind": "invoice_compliance",
        "directness": "primary",
        "assertions": [
            {"assertion_kind": "false_invoicing_evidence_absent", "polarity": "negative",
             "source_id": "prompt", "quote": "暂无虚开发票证据"},
            {"assertion_kind": "explicit_invoice_characterization_request", "polarity": "affirmative",
             "source_id": "prompt", "quote": "请定性"},
        ],
    }]
    out = eng.invoice_object_gate(audit_objects=objs, sources={"prompt": prompt, "context": ""})
    assert out["decision"] == "needs_review"
    assert out["emit_invoice_information_irregularity"] is False


def test_naked_bool_cannot_drive_production_gate():
    """The R3 root cause, closed: legacy bools alone can no longer produce SW
    on the production entry."""
    eng = load_module()
    out = eng.invoice_object_gate(
        audit_objects=[],
        sources=SOURCES,
        legacy={
            "expense_context": True,
            "independent_invoice_object": True,
            "false_invoicing_dispute": True,
            "invoice_blemish": {"header_mismatch"},
        },
    )
    assert out["decision"] != "sw_independent"
    assert out["emit_invoice_information_irregularity"] is False
    assert any("LEGACY_BOOL_UNVERIFIED" in rc for rc in out["reason_codes"])


def test_verified_object_with_legacy_bools_still_authorized():
    eng = load_module()
    out = eng.invoice_object_gate(
        audit_objects=case10_objects(), sources=SOURCES,
        legacy={"independent_invoice_object": False, "false_invoicing_dispute": False},
    )
    assert out["decision"] == "sw_independent", "verified objects outrank legacy bools"


def test_mixed_authorized_and_incidental_objects():
    eng = load_module()
    prompt = CASE10_PROMPT + "另有发票开票单位与收款单位不一致。"
    out = eng.invoice_object_gate(
        audit_objects=case10_objects() + incidental_object(),
        sources={"prompt": prompt, "context": ""},
    )
    assert out["decision"] == "sw_independent"
    assert out["authorized_object_ids"] == ["AO-1"]
    assert out["incidental_object_ids"] == ["AO-2"], "incidental defects stay on the FY side"


def test_legacy_pure_function_unchanged():
    """invoice_split_gate stays as a pure internal function (existing tests
    and fixtures keep passing)."""
    eng = load_module()
    out = eng.invoice_split_gate(
        expense_context=True,
        invoice_blemish={"header_mismatch"},
        independent_invoice_object=False,
        false_invoicing_dispute=False,
    )
    assert out["decision"] == "fy_incidental"


def test_partially_invalid_object_degrades_to_needs_review():
    """Frozen table: invalid assertions degrade the object (defect lost →
    focus-without-defect); only fully unverifiable objects are rejected."""
    eng = load_module()
    bad = case10_objects()[0]
    bad["assertions"][0]["quote"] = "不在源输入中的引文"
    out = eng.invoice_object_gate(audit_objects=[bad], sources=SOURCES)
    assert out["decision"] == "needs_review"
    assert out["emit_invoice_information_irregularity"] is False
    assert any("OBJECT_NEEDS_REVIEW" in rc for rc in out["reason_codes"])


def test_fully_unverifiable_object_rejected():
    eng = load_module()
    bad = case10_objects()[0]
    for a in bad["assertions"]:
        a["quote"] = "不在源输入中的引文"
    out = eng.invoice_object_gate(audit_objects=[bad], sources=SOURCES)
    assert out["decision"] == "needs_review"
    assert out["emit_invoice_information_irregularity"] is False
    assert any("UNVERIFIED_OBJECT" in rc for rc in out["reason_codes"])
