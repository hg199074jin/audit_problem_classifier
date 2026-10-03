"""V2.1.1 behavior tests for the deterministic FY/SW split and conclusion emission gates.

These test the decision-table module (rule-level behavior), not prose keywords.
Scenario inputs are runtime-derived facts; the engine returns deterministic decisions.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_engine():
    path = ROOT / "scripts" / "classification_emission.py"
    spec = importlib.util.spec_from_file_location("classification_emission_v211", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------- Negative / no-split (Issue #8 items 1-5) ----------

def test_expense_context_header_mismatch_stays_fy_no_split():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=True,
        invoice_blemish={"header_mismatch"},
        independent_invoice_object=False,
        false_invoicing_dispute=False,
    )
    assert d["primary_class"] == "FY"
    assert d["split_invoice_finding"] is False
    assert d["emit_invoice_information_irregularity"] is False


def test_expense_context_issuer_payee_mismatch_stays_fy_no_split():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=True,
        invoice_blemish={"issuer_payee_mismatch"},
        independent_invoice_object=False,
        false_invoicing_dispute=False,
    )
    assert d["primary_class"] == "FY"
    assert d["split_invoice_finding"] is False


def test_incidental_mismatch_does_not_emit_invoice_safe_conclusion():
    eng = load_engine()
    allowed = eng.safe_negative_conclusion_gate(
        "invoice_irregularity_not_false_invoicing_established",
        controversy_triggered=False,
        fact_preconditions_met=True,
    )
    assert allowed is False


def test_invoice_mismatch_alone_does_not_emit_reimbursement_review():
    eng = load_engine()
    allowed = eng.reimbursement_review_insufficient_gate(
        review_procedure_defect=False,
        required_attachments_missing=False,
        approval_responsibility_facts=False,
        finding_is_review_control=False,
    )
    assert allowed is False


def test_multi_item_list_without_pending_facts_does_not_emit_decision_required():
    eng = load_engine()
    allowed = eng.decision_required_pending_items_gate(
        blank_record=False,
        inclusion_decision_needed=False,
        pending_or_unconfirmed_facts=False,
    )
    assert allowed is False


# ---------- Positive / must preserve (Issue #8 items 8-9) ----------

def test_noncompliant_invoice_as_independent_object_splits_sw():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=True,
        invoice_blemish={"noncompliant_invoice_obtained"},
        independent_invoice_object=True,
        false_invoicing_dispute=False,
    )
    assert d["primary_class"] == "SW"
    assert d["split_invoice_finding"] is True
    assert d["emit_invoice_information_irregularity"] is True


def test_false_invoicing_dispute_with_insufficient_evidence_allows_safe_conclusion():
    eng = load_engine()
    allowed = eng.safe_negative_conclusion_gate(
        "invoice_irregularity_not_false_invoicing_established",
        controversy_triggered=True,
        fact_preconditions_met=True,
    )
    assert allowed is True


def test_collusive_bidding_safe_conclusion_triggered_by_quote_anomaly_dispute():
    eng = load_engine()
    assert (
        eng.safe_negative_conclusion_gate(
            "collusive_bidding_not_established",
            controversy_triggered=True,
            fact_preconditions_met=True,
        )
        is True
    )
    assert (
        eng.safe_negative_conclusion_gate(
            "collusive_bidding_not_established",
            controversy_triggered=False,
            fact_preconditions_met=True,
        )
        is False
    )


def test_reimbursement_review_gate_allows_explicit_review_control_facts():
    eng = load_engine()
    assert (
        eng.reimbursement_review_insufficient_gate(
            review_procedure_defect=True,
            required_attachments_missing=False,
            approval_responsibility_facts=False,
            finding_is_review_control=True,
        )
        is True
    )


def test_decision_required_gate_allows_real_pending_facts():
    eng = load_engine()
    assert (
        eng.decision_required_pending_items_gate(
            blank_record=True,
            inclusion_decision_needed=False,
            pending_or_unconfirmed_facts=False,
        )
        is True
    )


def test_precedence_expense_context_beats_incidental_sw_even_with_other_blemishes():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=True,
        invoice_blemish={"header_mismatch", "general_information_irregularity"},
        independent_invoice_object=False,
        false_invoicing_dispute=False,
    )
    assert d["primary_class"] == "FY"
    assert d["split_invoice_finding"] is False


def test_unknown_safe_conclusion_code_rejected():
    eng = load_engine()
    try:
        eng.safe_negative_conclusion_gate("made_up_code", controversy_triggered=True, fact_preconditions_met=True)
        raised = False
    except ValueError:
        raised = True
    assert raised
