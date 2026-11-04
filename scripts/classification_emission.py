#!/usr/bin/env python3
"""Deterministic classification / emission decision tables (V2.2.1).

The runtime derives factual inputs from the case, then invokes the gate
functions directly or through the CLI (subcommands) so that the boundaries in
rules/classification.md and rules/result-contract.md are machine-checkable,
regression-testable, and actually executable inside the Skill runtime.

Inputs are runtime-derived facts (booleans / blemish sets), not case IDs.
"""
from __future__ import annotations

import argparse
import json
import sys

# Invoice blemish kinds that remain incidental to an expense/reimbursement
# context. Any kind outside this set (e.g. noncompliant_invoice_obtained)
# indicates the invoice defect itself is the audit object.
INCIDENTAL_INVOICE_BLEMISH_KINDS = {
    "header_mismatch",
    "issuer_payee_mismatch",
    "general_information_irregularity",
}

SAFE_NEGATIVE_CONCLUSION_CODES = {
    "invoice_irregularity_not_false_invoicing_established": "false_invoicing",
    "collusive_bidding_not_established": "collusive_bidding",
    "misappropriation_not_established": "misappropriation",
    "post_execution_signing_not_backdating_established": "backdating",
    "recoverable_undercollection_not_loss_established": "established_loss",
}


def invoice_split_gate(
    *,
    expense_context: bool,
    invoice_blemish: set[str],
    independent_invoice_object: bool,
    false_invoicing_dispute: bool,
) -> dict:
    """Decide the invoice dimension of classification. Gate B precedes Gate A.

    expense_context: the scenario is reimbursement / expense vouchers / payment
        review / expense supporting documents.
    invoice_blemish: observed invoice defect kinds (runtime-derived).
    independent_invoice_object: the input explicitly makes invoice legality /
        tax violation itself the independent audit object (Gate B).
    false_invoicing_dispute: the input actually raises 虚开 / transaction
        authenticity / invoice legal validity as a disputed question (Gate B).

    Decisions:
      no_invoice_finding — no invoice issue observed; the gate abstains.
      fy_incidental      — expense context with incidental blemishes: FY,
                           never split an invoice_information_irregularity.
      sw_independent     — Gate B met: SW with an explicit invoice finding.
      needs_review       — a dispute or blemish exists without sufficient facts
                           to classify; fail closed, never fabricate SW.
    """
    blemish = set(invoice_blemish or ())
    non_incidental = blemish - INCIDENTAL_INVOICE_BLEMISH_KINDS
    gate_b = bool(independent_invoice_object) or bool(non_incidental) or bool(false_invoicing_dispute)

    if not blemish and not independent_invoice_object and not false_invoicing_dispute:
        return {
            "decision": "no_invoice_finding",
            "primary_class": None,
            "emit_invoice_information_irregularity": False,
            "rationale": "no invoice defect observed; the invoice gate abstains",
        }
    if gate_b:
        if not blemish and not independent_invoice_object:
            return {
                "decision": "needs_review",
                "primary_class": None,
                "emit_invoice_information_irregularity": False,
                "rationale": "false-invoicing dispute raised without observable invoice defect facts; fail closed",
            }
        unknown_kinds = blemish - INCIDENTAL_INVOICE_BLEMISH_KINDS - {"noncompliant_invoice_obtained"}
        if unknown_kinds and not independent_invoice_object:
            return {
                "decision": "needs_review",
                "primary_class": None,
                "emit_invoice_information_irregularity": False,
                "rationale": f"unknown invoice blemish kind(s) {sorted(unknown_kinds)}; cannot classify",
            }
        return {
            "decision": "sw_independent",
            "primary_class": "SW",
            "emit_invoice_information_irregularity": True,
            "rationale": "gate B: invoice legality/tax violation is an explicit independent audit object",
        }
    if expense_context:
        return {
            "decision": "fy_incidental",
            "primary_class": "FY",
            "emit_invoice_information_irregularity": False,
            "rationale": "gate A/C: expense-context default wins; incidental invoice blemishes do not split SW",
        }
    return {
        "decision": "needs_review",
        "primary_class": None,
        "emit_invoice_information_irregularity": False,
        "rationale": "incidental invoice blemish outside an expense context; classification ownership undetermined",
    }


def safe_negative_conclusion_gate(
    code: str,
    *,
    controversy: str,
    raised: bool,
    fact_preconditions_met: bool,
) -> bool:
    """Gate for 'not escalated to the more severe characterization' codes.

    controversy: which severe characterization is allegedly disputed. It must
        belong to the conclusion code's own family; a cross-family controversy
        (e.g. raising false_invoicing for a misappropriation code) is rejected.
    raised: the input facts or the user request actually raise that controversy.
    fact_preconditions_met: the specific preconditions recorded for that code
        (e.g. for invoice: irregular information + genuine transaction + no
        false-invoicing evidence) are present.
    """
    if code not in SAFE_NEGATIVE_CONCLUSION_CODES:
        raise ValueError(f"unknown safe negative conclusion code: {code!r}")
    if controversy != SAFE_NEGATIVE_CONCLUSION_CODES[code]:
        raise ValueError(
            f"controversy {controversy!r} does not match conclusion code family "
            f"{SAFE_NEGATIVE_CONCLUSION_CODES[code]!r} for {code!r}"
        )
    return bool(raised and fact_preconditions_met)


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


# --------------------------- CLI (runtime invokable) ---------------------------

def _read_input(path: str) -> dict:
    raw = sys.stdin.read() if path == "-" else pathlib_Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("input JSON must be an object")
    return data


def pathlib_Path(path: str):
    from pathlib import Path

    return Path(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic classification / emission decision gates")
    sub = parser.add_subparsers(dest="gate", required=True)

    p_split = sub.add_parser("invoice-split", help="FY-vs-SW invoice split decision")
    p_split.add_argument("--input", required=True, help="facts JSON file path, or '-' for stdin")

    p_safe = sub.add_parser("safe-conclusion", help="safe negative conclusion trigger gate")
    p_safe.add_argument("--code", required=True)
    p_safe.add_argument("--controversy", required=True)
    p_safe.add_argument("--raised", action="store_true")
    p_safe.add_argument("--preconditions-met", action="store_true")

    p_review = sub.add_parser("review-insufficient", help="reimbursement_review_insufficient gate")
    p_review.add_argument("--input", required=True, help="facts JSON file path, or '-' for stdin")

    p_pending = sub.add_parser("decision-required", help="decision_required_pending_items gate")
    p_pending.add_argument("--input", required=True, help="facts JSON file path, or '-' for stdin")

    args = parser.parse_args(argv)

    try:
        if args.gate == "invoice-split":
            facts = _read_input(args.input)
            ec = facts.get("expense_context")
            io = facts.get("independent_invoice_object")
            fd = facts.get("false_invoicing_dispute")
            for name, val in (("expense_context", ec), ("independent_invoice_object", io), ("false_invoicing_dispute", fd)):
                if val is not None and not isinstance(val, bool):
                    print(f"ERROR: {name} must be a JSON boolean, got {type(val).__name__}: {val!r}", file=sys.stderr)
                    return 2
            ib = facts.get("invoice_blemish")
            if ib is not None:
                if not isinstance(ib, list) or not all(isinstance(x, str) for x in ib):
                    print(f"ERROR: invoice_blemish must be a JSON array of strings, got {ib!r}", file=sys.stderr)
                    return 2
            unknown_kinds = set(ib or ()) - INCIDENTAL_INVOICE_BLEMISH_KINDS - {"noncompliant_invoice_obtained"}
            if unknown_kinds:
                    print(f"ERROR: unknown invoice blemish kind(s): {sorted(unknown_kinds)}", file=sys.stderr)
                    return 2
            decision = invoice_split_gate(
                expense_context=bool(ec),
                invoice_blemish=set(ib or ()),
                independent_invoice_object=bool(io),
                false_invoicing_dispute=bool(fd),
            )
            print(json.dumps(decision, ensure_ascii=False, indent=2))
            return 0
        if args.gate == "safe-conclusion":
            allowed = safe_negative_conclusion_gate(
                args.code,
                controversy=args.controversy,
                raised=args.raised,
                fact_preconditions_met=args.preconditions_met,
            )
            print(json.dumps({"code": args.code, "allowed": allowed}, ensure_ascii=False, indent=2))
            return 0
        if args.gate == "review-insufficient":
            facts = _read_input(args.input)
            for name in ("review_procedure_defect", "required_attachments_missing",
                         "approval_responsibility_facts", "finding_is_review_control"):
                val = facts.get(name)
                if val is not None and not isinstance(val, bool):
                    print(f"ERROR: {name} must be a JSON boolean, got {type(val).__name__}: {val!r}", file=sys.stderr)
                    return 2
            allowed = reimbursement_review_insufficient_gate(
                review_procedure_defect=bool(facts.get("review_procedure_defect")),
                required_attachments_missing=bool(facts.get("required_attachments_missing")),
                approval_responsibility_facts=bool(facts.get("approval_responsibility_facts")),
                finding_is_review_control=bool(facts.get("finding_is_review_control")),
            )
            print(json.dumps({"allowed": allowed}, ensure_ascii=False, indent=2))
            return 0
        if args.gate == "decision-required":
            facts = _read_input(args.input)
            for name in ("blank_record", "inclusion_decision_needed", "pending_or_unconfirmed_facts"):
                val = facts.get(name)
                if val is not None and not isinstance(val, bool):
                    print(f"ERROR: {name} must be a JSON boolean, got {type(val).__name__}: {val!r}", file=sys.stderr)
                    return 2
            allowed = decision_required_pending_items_gate(
                blank_record=bool(facts.get("blank_record")),
                inclusion_decision_needed=bool(facts.get("inclusion_decision_needed")),
                pending_or_unconfirmed_facts=bool(facts.get("pending_or_unconfirmed_facts")),
            )
            print(json.dumps({"allowed": allowed}, ensure_ascii=False, indent=2))
            return 0
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
