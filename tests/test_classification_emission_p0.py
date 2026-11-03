"""GPT-005 P0 preflight RED tests: engine precedence, abstention, CLI, controversy binding."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_engine():
    spec = importlib.util.spec_from_file_location("classification_emission_p0", ROOT / "scripts" / "classification_emission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------- P0-A: false_invoicing dispute takes precedence over expense default ----------

def test_p0a_dispute_overrides_expense_default():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=True,
        invoice_blemish={"header_mismatch"},
        independent_invoice_object=False,
        false_invoicing_dispute=True,
    )
    assert d["decision"] == "sw_independent", d
    assert d["primary_class"] == "SW"
    assert d["emit_invoice_information_irregularity"] is True


# ---------- P0-B: no invoice issue => gate abstains, never fabricates SW ----------

def test_p0b_no_blemish_no_expense_abstains():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=False,
        invoice_blemish=set(),
        independent_invoice_object=False,
        false_invoicing_dispute=False,
    )
    assert d["decision"] == "no_invoice_finding", d
    assert d["emit_invoice_information_irregularity"] is False


def test_p0b_no_blemish_with_expense_context_abstains():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=True,
        invoice_blemish=set(),
        independent_invoice_object=False,
        false_invoicing_dispute=False,
    )
    assert d["decision"] == "no_invoice_finding", d
    assert d["emit_invoice_information_irregularity"] is False


def test_p0b_dispute_without_blemish_facts_is_needs_review():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=False,
        invoice_blemish=set(),
        independent_invoice_object=False,
        false_invoicing_dispute=True,
    )
    assert d["decision"] == "needs_review", d
    assert d["emit_invoice_information_irregularity"] is False


def test_p0b_incidental_blemish_without_expense_context_is_needs_review():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=False,
        invoice_blemish={"header_mismatch"},
        independent_invoice_object=False,
        false_invoicing_dispute=False,
    )
    assert d["decision"] == "needs_review", d


# ---------- protected behaviors keep passing under the new engine ----------

def test_protected_expense_boundary_incidental_pair_stays_fy():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=True,
        invoice_blemish={"header_mismatch", "issuer_payee_mismatch"},
        independent_invoice_object=False,
        false_invoicing_dispute=False,
    )
    assert d["decision"] == "fy_incidental"
    assert d["primary_class"] == "FY"
    assert d["emit_invoice_information_irregularity"] is False


def test_protected_nonincidental_defect_splits_sw():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=True,
        invoice_blemish={"noncompliant_invoice_obtained"},
        independent_invoice_object=False,
        false_invoicing_dispute=False,
    )
    assert d["decision"] == "sw_independent"
    assert d["primary_class"] == "SW"


def test_protected_independent_object_splits_sw():
    eng = load_engine()
    d = eng.invoice_split_gate(
        expense_context=False,
        invoice_blemish=set(),
        independent_invoice_object=True,
        false_invoicing_dispute=False,
    )
    assert d["decision"] == "sw_independent"
    assert d["primary_class"] == "SW"


# ---------- P0-D: controversy must match the conclusion code family ----------

def test_p0d_mismatched_controversy_rejected():
    eng = load_engine()
    try:
        eng.safe_negative_conclusion_gate(
            "misappropriation_not_established",
            controversy="false_invoicing",
            raised=True,
            fact_preconditions_met=True,
        )
        raised = False
    except ValueError:
        raised = True
    assert raised, "cross-family controversy must be rejected"


def test_p0d_matched_controversy_and_facts_allows():
    eng = load_engine()
    assert (
        eng.safe_negative_conclusion_gate(
            "misappropriation_not_established",
            controversy="misappropriation",
            raised=True,
            fact_preconditions_met=True,
        )
        is True
    )


def test_p0d_matched_controversy_not_raised_rejects():
    eng = load_engine()
    assert (
        eng.safe_negative_conclusion_gate(
            "invoice_irregularity_not_false_invoicing_established",
            controversy="false_invoicing",
            raised=False,
            fact_preconditions_met=True,
        )
        is False
    )


# ---------- P0-C: runtime-invokable CLI ----------

def test_p0c_cli_invoice_split_returns_decision():
    facts = {"expense_context": True, "invoice_blemish": ["header_mismatch"], "independent_invoice_object": False, "false_invoicing_dispute": False}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "classification_emission.py"), "invoice-split", "--input", "-"],
        input=json.dumps(facts), capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["decision"] == "fy_incidental"


def test_p0c_cli_safe_conclusion_binding():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "classification_emission.py"), "safe-conclusion",
         "--code", "invoice_irregularity_not_false_invoicing_established",
         "--controversy", "false_invoicing", "--raised", "--preconditions-met"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["allowed"] is True


def test_p0c_cli_rejects_mismatched_controversy():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "classification_emission.py"), "safe-conclusion",
         "--code", "misappropriation_not_established",
         "--controversy", "false_invoicing", "--raised", "--preconditions-met"],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0
