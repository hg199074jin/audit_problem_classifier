"""V2.2.4 metamorphic tests: change-only-one-fact mutations on the audit
object gate. The SW authorization must track the changed fact, not the
unchanged wording."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROMPT = (
    "报销发票记载的购买方信息与实际报销单位存在不一致，但交易真实、货物确已取得，"
    "目前没有虚构交易、无真实业务开票或其他虚开发票证据。请定性。"
)
SOURCES = {"prompt": PROMPT, "context": ""}


def load_pair():
    def load(name):
        spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return load("classification_emission"), load("audit_object_grounding")


def case10_assertions():
    return [
        {"assertion_kind": "invoice_buyer_mismatch", "polarity": "affirmative",
         "source_id": "prompt", "quote": "购买方信息与实际报销单位存在不一致"},
        {"assertion_kind": "explicit_invoice_characterization_request", "polarity": "affirmative",
         "source_id": "prompt", "quote": "请定性"},
        {"assertion_kind": "true_transaction", "polarity": "affirmative",
         "source_id": "prompt", "quote": "交易真实"},
        {"assertion_kind": "false_invoicing_evidence_absent", "polarity": "negative",
         "source_id": "prompt",
         "quote": "目前没有虚构交易、无真实业务开票或其他虚开发票证据"},
    ]


def gate(aog, eng, assertions, sources=SOURCES):
    objects = [{
        "object_id": "AO-1", "source_record_id": None,
        "object_kind": "invoice_compliance", "directness": "primary",
        "assertions": assertions,
    }]
    return eng.invoice_object_gate(audit_objects=objects, sources=sources), aog


def test_baseline_authorizes_sw():
    eng, aog = load_pair()
    out, _ = gate(aog, eng, case10_assertions())
    assert out["decision"] == "sw_independent"
    assert out["restrictions"] == ["no_false_invoicing_finding"]


def test_mutation_remove_focus_no_sw():
    eng, aog = load_pair()
    assertions = [a for a in case10_assertions()
                  if a["assertion_kind"] != "explicit_invoice_characterization_request"]
    out, _ = gate(aog, eng, assertions)
    assert out["decision"] != "sw_independent"
    assert out["decision"] == "needs_review"


def test_mutation_incidental_downgrade_no_sw():
    eng, aog = load_pair()
    assertions = [a for a in case10_assertions()
                  if a["assertion_kind"] != "explicit_invoice_characterization_request"]
    objects = [{
        "object_id": "AO-1", "source_record_id": None,
        "object_kind": "invoice_compliance", "directness": "incidental",
        "assertions": assertions,
    }]
    out = eng.invoice_object_gate(audit_objects=objects, sources=SOURCES)
    assert out["decision"] == "fy_incidental"


def test_mutation_remove_defect_no_sw():
    eng, aog = load_pair()
    assertions = [a for a in case10_assertions()
                  if a["assertion_kind"] != "invoice_buyer_mismatch"]
    out, _ = gate(aog, eng, assertions)
    assert out["decision"] == "needs_review"
    assert out["emit_invoice_information_irregularity"] is False


def test_mutation_defect_fact_negated_in_source_no_sw():
    eng, aog = load_pair()
    mutated_sources = {
        "prompt": PROMPT.replace("购买方信息与实际报销单位存在不一致", "购买方信息与实际报销单位一致"),
        "context": "",
    }
    out, _ = gate(aog, eng, case10_assertions(), mutated_sources)
    assert out["decision"] != "sw_independent"


def test_mutation_hypothetical_defect_no_sw():
    eng, aog = load_pair()
    assertions = case10_assertions()
    assertions[0]["polarity"] = "hypothetical"
    out, _ = gate(aog, eng, assertions)
    assert out["decision"] != "sw_independent"


def test_mutation_remove_true_transaction_drops_restriction_not_authorization():
    eng, aog = load_pair()
    assertions = [a for a in case10_assertions() if a["assertion_kind"] != "true_transaction"]
    out, _ = gate(aog, eng, assertions)
    assert out["decision"] == "sw_independent"
    assert out["restrictions"] == ["no_false_invoicing_finding"], (
        "false-invoicing-absent (still verified) keeps the restriction"
    )


def test_mutation_remove_all_restrictions_drops_restriction():
    eng, aog = load_pair()
    assertions = [a for a in case10_assertions()
                  if a["assertion_kind"] not in ("true_transaction", "false_invoicing_evidence_absent")]
    out, _ = gate(aog, eng, assertions)
    assert out["decision"] == "sw_independent"
    assert out["restrictions"] == []
