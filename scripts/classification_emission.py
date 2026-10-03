#!/usr/bin/env python3
"""Deterministic classification / emission decision tables (V2.1.1).

The runtime derives the factual inputs from the case; this engine applies the
FY-vs-SW split gate and the conclusion emission trigger gates mechanically so
that the boundaries in rules/classification.md and rules/result-contract.md
are machine-checkable and regression-testable.

Inputs are runtime-derived facts (booleans / blemish sets), not case IDs.
"""
from __future__ import annotations

# Invoice blemish kinds that remain incidental to an expense/reimbursement
# context. Any kind outside this set (e.g. noncompliant_invoice_obtained)
# indicates the invoice defect itself is the audit object.
INCIDENTAL_INVOICE_BLEMISH_KINDS = {
    "header_mismatch",
    "issuer_payee_mismatch",
    "general_information_irregularity",
}

SAFE_NEGATIVE_CONCLUSION_CODES = {
    "invoice_irregularity_not_false_invoicing_established",
    "collusive_bidding_not_established",
    "misappropriation_not_established",
    "post_execution_signing_not_backdating_established",
    "recoverable_undercollection_not_loss_established",
}


def invoice_split_gate(
    *,
    expense_context: bool,
    invoice_blemish: set[str],
    independent_invoice_object: bool,
    false_invoicing_dispute: bool,
) -> dict:
    """Decide FY-vs-SW when invoice blemishes appear in an expense context.

    expense_context: the scenario is reimbursement / expense vouchers / payment
        review / expense supporting documents.
    invoice_blemish: observed invoice defect kinds.
    independent_invoice_object: the input explicitly makes invoice legality /
        tax-violation itself the independent audit object (Gate B hit).
    false_invoicing_dispute: the input actually raises 虚开 / transaction
        authenticity / invoice legal validity as a disputed question.

    Precedence: Gate A (expense-context default → FY) wins over incidental
    invoice blemishes unless Gate B (independent invoice/tax object) is met.
    """
    if independent_invoice_object:
        return {
            "primary_class": "SW",
            "split_invoice_finding": True,
            "emit_invoice_information_irregularity": True,
            "rationale": "gate B: invoice legality/tax violation is an explicit independent audit object",
        }
    if invoice_blemish and not set(invoice_blemish) <= INCIDENTAL_INVOICE_BLEMISH_KINDS:
        return {
            "primary_class": "SW",
            "split_invoice_finding": True,
            "emit_invoice_information_irregularity": True,
            "rationale": "gate B: non-incidental invoice defect (e.g. noncompliant invoice obtained) is the audit object",
        }
    if expense_context:
        return {
            "primary_class": "FY",
            "split_invoice_finding": False,
            "emit_invoice_information_irregularity": False,
            "rationale": "gate A/C: expense-context default wins; incidental invoice blemishes do not split SW",
        }
    if false_invoicing_dispute:
        return {
            "primary_class": "SW",
            "split_invoice_finding": True,
            "emit_invoice_information_irregularity": True,
            "rationale": "gate B: false-invoicing dispute makes the invoice the audit object",
        }
    return {
        "primary_class": "SW",
        "split_invoice_finding": True,
        "emit_invoice_information_irregularity": True,
        "rationale": "no expense context and invoice legality is the direct object",
    }


def safe_negative_conclusion_gate(
    code: str,
    *,
    controversy_triggered: bool,
    fact_preconditions_met: bool,
) -> bool:
    """Gate for 'not escalated to the more severe characterization' codes.

    controversy_triggered: the input facts or the user request actually raise
        the corresponding more-severe characterization as a disputed question.
    fact_preconditions_met: the specific preconditions recorded for that code
        (e.g. for invoice: irregular information + genuine transaction + no
        false-invoicing evidence) are present.
    """
    if code not in SAFE_NEGATIVE_CONCLUSION_CODES:
        raise ValueError(f"unknown safe negative conclusion code: {code!r}")
    return bool(controversy_triggered and fact_preconditions_met)


def reimbursement_review_insufficient_gate(
    *,
    review_procedure_defect: bool,
    required_attachments_missing: bool,
    approval_responsibility_facts: bool,
    finding_is_review_control: bool,
) -> bool:
    """Gate for reimbursement_review_insufficient.

    Requires explicit review-control facts AND the current finding to actually
    be a review-control problem. Invoice header mismatch, issuer/payee
    mismatch, or general voucher nonstandardness alone never qualifies.
    """
    explicit_facts = review_procedure_defect or required_attachments_missing or approval_responsibility_facts
    return bool(finding_is_review_control and explicit_facts)


def decision_required_pending_items_gate(
    *,
    blank_record: bool,
    inclusion_decision_needed: bool,
    pending_or_unconfirmed_facts: bool,
) -> bool:
    """Gate for decision_required_pending_items.

    Only real pending facts (blank record, inclusion/exclusion decision,
    待落实 / 是否有文件 / unconfirmed items) qualify. A complex multi-item list
    alone never does.
    """
    return bool(blank_record or inclusion_decision_needed or pending_or_unconfirmed_facts)


if __name__ == "__main__":
    raise SystemExit("decision table module — import and call the gate functions; no CLI")
