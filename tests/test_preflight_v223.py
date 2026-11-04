"""V2.2.3 preflight structural tests (RED first, GREEN after implementation).

Covers the R2 adjudication items:
- fact→finding_type authorization at the specific-vs-generic attachment
  boundary (R2 Gate D cases 02/03);
- complete 1:1 emission of the three decision_required brother codes
  (R2 Gate D case 05);
- Mode A/B applicability pairing for a single determined structured target
  (R2 Gate D case 26), with disambiguation instead of guessing;
- field-specific citation support: a verbatim citation that does not support
  the claimed fact field must fail (grounding gap #1);
- fail-closed enforce: no partial cross-field rewriting (grounding gap #2).

Regression guards protect the V2.2.2 wins (cases 04/23/24 shapes).
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ============ A. expense_supporting_finding_gate (cases 02/03) ============


def test_generic_details_missing_authorizes_generic_code_not_specific():
    """case-03 shape: '有的缺少明细' without any specific list object must
    yield the generic code, never distribution_list_missing."""
    eng = load("classification_emission")
    source = "某事业单位报销水费、维修费、伙食费和通讯费，其中有的缺少明细。"
    decision = eng.expense_supporting_finding_gate(
        source_text=source,
        specific_distribution_list_citation="",
        generic_supporting_incomplete=True,
        documents_nonstandard=False,
    )
    assert "expense_supporting_documents_incomplete" in decision["finding_types"]
    assert "distribution_list_missing" not in decision["finding_types"]


def test_generic_attachment_missing_training_shape_not_specific():
    """case-02 shape: '培训附件缺失' is generic incompleteness."""
    eng = load("classification_emission")
    source = "培训费报销附件缺失，未见培训通知与签到表。"
    decision = eng.expense_supporting_finding_gate(
        source_text=source,
        specific_distribution_list_citation="",
        generic_supporting_incomplete=True,
    )
    assert decision["finding_types"] == ["expense_supporting_documents_incomplete"]


def test_specific_list_citation_authorizes_distribution_list_missing():
    """case-23 shape: a verbatim citation naming a specific list object
    authorizes distribution_list_missing."""
    eng = load("classification_emission")
    source = "某事业单位报销办公用品，附件缺少领用清单。"
    decision = eng.expense_supporting_finding_gate(
        source_text=source,
        specific_distribution_list_citation="附件缺少领用清单",
        generic_supporting_incomplete=True,
        documents_nonstandard=False,
    )
    assert "distribution_list_missing" in decision["finding_types"]
    assert "expense_supporting_documents_incomplete" not in decision["finding_types"]


def test_specific_citation_must_be_verbatim_in_source():
    eng = load("classification_emission")
    source = "培训费报销附件缺失。"
    decision = eng.expense_supporting_finding_gate(
        source_text=source,
        specific_distribution_list_citation="缺少领用清单",  # not in source
        generic_supporting_incomplete=True,
    )
    assert "distribution_list_missing" not in decision["finding_types"]
    assert "expense_supporting_documents_incomplete" in decision["finding_types"]


def test_specific_citation_must_name_a_specific_list_object():
    """A verbatim but object-less citation ('附件缺失') does not authorize the
    specific code — the anchor set is the professional object lexicon."""
    eng = load("classification_emission")
    source = "培训费报销附件缺失。"
    decision = eng.expense_supporting_finding_gate(
        source_text=source,
        specific_distribution_list_citation="附件缺失",
        generic_supporting_incomplete=True,
    )
    assert "distribution_list_missing" not in decision["finding_types"]
    assert "expense_supporting_documents_incomplete" in decision["finding_types"]


def test_specific_wins_over_generic_and_nonstandard_is_independent():
    eng = load("classification_emission")
    source = "报销附件中发放清单缺失，另有明细不齐、发票抬头不一致。"
    decision = eng.expense_supporting_finding_gate(
        source_text=source,
        specific_distribution_list_citation="发放清单缺失",
        generic_supporting_incomplete=True,
        documents_nonstandard=True,
    )
    assert decision["finding_types"] == [
        "distribution_list_missing",
        "expense_supporting_documents_nonstandard",
    ]


def test_no_attachment_facts_abstain():
    eng = load("classification_emission")
    decision = eng.expense_supporting_finding_gate(
        source_text="正常报销。",
        specific_distribution_list_citation="",
        generic_supporting_incomplete=False,
        documents_nonstandard=False,
    )
    assert decision["decision"] == "no_expense_document_finding"
    assert decision["finding_types"] == []


def test_cli_expense_documents_gate(tmp_path):
    facts = {
        "source_text": "报销附件缺少领用清单。",
        "specific_distribution_list_citation": "附件缺少领用清单",
        "generic_supporting_incomplete": False,
        "documents_nonstandard": False,
    }
    facts_file = tmp_path / "facts.json"
    facts_file.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "classification_emission.py"),
         "expense-documents", "--input", str(facts_file)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["finding_types"] == ["distribution_list_missing"]


# ============ B. decision_required brother codes (case 05) ============


def test_three_facts_yield_three_brother_codes():
    eng = load("classification_emission")
    out = eng.decision_required_codes_gate(
        blank_record=True,
        inclusion_decision_needed=True,
        pending_or_unconfirmed_facts=True,
    )
    assert out["allowed"] is True
    assert set(out["codes"]) == {
        "decision_required_blank_record",
        "decision_required_record_inclusion",
        "decision_required_pending_items",
    }
    assert len(out["codes"]) == 3, "brother codes must not be swallowed"


def test_single_fact_yields_only_its_own_code():
    eng = load("classification_emission")
    for fact, code in (
        ("blank_record", "decision_required_blank_record"),
        ("inclusion_decision_needed", "decision_required_record_inclusion"),
        ("pending_or_unconfirmed_facts", "decision_required_pending_items"),
    ):
        kwargs = {
            name: (name == fact)
            for name in ("blank_record", "inclusion_decision_needed", "pending_or_unconfirmed_facts")
        }
        out = eng.decision_required_codes_gate(**kwargs)
        assert out["codes"] == [code], fact


def test_no_decision_facts_no_codes():
    eng = load("classification_emission")
    out = eng.decision_required_codes_gate(
        blank_record=False, inclusion_decision_needed=False,
        pending_or_unconfirmed_facts=False,
    )
    assert out["allowed"] is False
    assert out["codes"] == []


def test_cli_decision_required_emits_complete_codes(tmp_path):
    facts = {"blank_record": True, "inclusion_decision_needed": True,
             "pending_or_unconfirmed_facts": True}
    facts_file = tmp_path / "facts.json"
    facts_file.write_text(json.dumps(facts), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "classification_emission.py"),
         "decision-required", "--input", str(facts_file)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert set(out["codes"]) == {
        "decision_required_blank_record",
        "decision_required_record_inclusion",
        "decision_required_pending_items",
    }


# ============ C. grounding: field-specific citation support ============


def test_supported_anchor_citation_passes():
    mod = load("conclusion_grounding")
    source = (
        "这是某单位的问题汇总表（其中含一行只有摘要和金额、无问题描述的汇总行，"
        "一条问题描述空白的奖励提成记录，若干标注“待落实”“是否有文件”的记录）。"
    )
    result = {
        "conclusion_codes": [
            "decision_required_blank_record",
            "decision_required_record_inclusion",
            "decision_required_pending_items",
        ],
        "fact_grounding": [
            {"field": "blank_record", "value": True, "citation": "一条问题描述空白的奖励提成记录"},
            {"field": "inclusion_decision_needed", "value": True, "citation": "一行只有摘要和金额、无问题描述的汇总行"},
            {"field": "pending_or_unconfirmed_facts", "value": True, "citation": "若干标注“待落实”“是否有文件”的记录"},
        ],
    }
    assert mod.verify_grounding(result, source) == []


def test_citation_present_but_not_supporting_field_fails():
    """Grounding gap #1: the citation exists verbatim but names an amount, not
    a blank record — presence alone must not license the field."""
    mod = load("conclusion_grounding")
    source = "记录金额2,300元，附件缺少领用清单。"
    result = {
        "conclusion_codes": ["decision_required_blank_record"],
        "fact_grounding": [
            {"field": "blank_record", "value": True, "citation": "金额2,300元"}
        ],
    }
    violations = mod.verify_grounding(result, source)
    assert violations, "present-but-unsupported citation must fail"
    assert any("blank_record" in v for v in violations)


def test_attachment_citation_does_not_support_review_control():
    mod = load("conclusion_grounding")
    source = "报销附件缺少领用清单。"
    result = {
        "conclusion_codes": ["reimbursement_review_insufficient"],
        "fact_grounding": [
            {"field": "required_attachments_missing", "value": True, "citation": "附件缺少领用清单"},
            {"field": "finding_is_review_control", "value": True, "citation": "附件缺少领用清单"},
        ],
    }
    violations = mod.verify_grounding(result, source)
    assert any("finding_is_review_control" in v for v in violations)


def test_review_control_citation_with_explicit_procedure_fact_passes():
    mod = load("conclusion_grounding")
    source = "该笔报销单已经部门负责人签批，但财务审核岗位未履行审核程序即予入账。"
    result = {
        "conclusion_codes": ["reimbursement_review_insufficient"],
        "fact_grounding": [
            {"field": "review_procedure_defect", "value": True, "citation": "财务审核岗位未履行审核程序即予入账"},
            {"field": "finding_is_review_control", "value": True, "citation": "财务审核岗位未履行审核程序即予入账"},
        ],
    }
    assert mod.verify_grounding(result, source) == []


def test_brother_codes_guarded_individually():
    """decision_required_record_inclusion must be grounded by its own fact,
    not by a pending-items citation."""
    mod = load("conclusion_grounding")
    source = "若干标注“待落实”的记录。"
    result = {
        "conclusion_codes": ["decision_required_record_inclusion"],
        "fact_grounding": [
            {"field": "pending_or_unconfirmed_facts", "value": True, "citation": "若干标注“待落实”的记录"},
        ],
    }
    violations = mod.verify_grounding(result, source)
    assert any("decision_required_record_inclusion" in v for v in violations)


def test_evidence_chain_open_citation_does_not_support_pending_facts():
    """V2.2.2 case-04 protection: '证据链未闭合' stays a non-licensing citation."""
    mod = load("conclusion_grounding")
    source = "采购程序中证据链未闭合，需要补充询价资料。"
    result = {
        "conclusion_codes": ["decision_required_pending_items"],
        "fact_grounding": [
            {"field": "pending_or_unconfirmed_facts", "value": True, "citation": "证据链未闭合"}
        ],
    }
    assert mod.verify_grounding(result, source), "evidence-chain wording must not ground pending facts"


# ============ D. enforce: fail-closed, no cross-field mutation ============


def test_enforce_violations_returns_result_unmodified():
    """Grounding gap #2: enforce must not partially rewrite gate_status or
    applicability fields while keeping law bindings — the result comes back
    exactly as submitted and delivery is refused via violations."""
    mod = load("conclusion_grounding")
    source = "附件缺少领用清单。"
    result = {
        "gate_status": "proceed",
        "applicability_status": "applicable",
        "applicability_target": "CN-INVOICE-2023-ART20",
        "law_ids": ["CN-INVOICE-2023-ART20"],
        "conclusion_codes": ["decision_required_pending_items"],
        "fact_grounding": [],
    }
    cleaned, violations = mod.enforce_grounding(result, source)
    assert violations
    assert cleaned == result, "enforce must not mutate the result cross-field"


def test_enforce_clean_result_passes_through_unchanged():
    mod = load("conclusion_grounding")
    source = "若干标注“待落实”的记录。"
    result = {
        "gate_status": "blocked",
        "conclusion_codes": ["decision_required_pending_items"],
        "fact_grounding": [
            {"field": "pending_or_unconfirmed_facts", "value": True, "citation": "若干标注“待落实”的记录"}
        ],
    }
    cleaned, violations = mod.enforce_grounding(result, source)
    assert violations == []
    assert cleaned == result


def test_cli_enforce_blocked_delivers_nothing_on_stdout(tmp_path):
    source_file = tmp_path / "source.txt"
    source_file.write_text("附件缺少领用清单。", encoding="utf-8")
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps({"conclusion_codes": ["reimbursement_review_insufficient"]}),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "conclusion_grounding.py"),
         "--result", str(result_file), "--source", str(source_file), "--enforce"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert proc.stdout.strip() == "", "blocked enforcement must not deliver a result"
    assert "VIOLATION" in proc.stderr


def test_cli_enforce_clean_delivers_result(tmp_path):
    source_file = tmp_path / "source.txt"
    source_file.write_text("若干标注“待落实”的记录。", encoding="utf-8")
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps({
            "conclusion_codes": ["decision_required_pending_items"],
            "fact_grounding": [
                {"field": "pending_or_unconfirmed_facts", "value": True,
                 "citation": "若干标注“待落实”的记录"}
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "conclusion_grounding.py"),
         "--result", str(result_file), "--source", str(source_file), "--enforce"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["conclusion_codes"] == ["decision_required_pending_items"]


# ============ E. applicability pairing (case 26) ============


def test_applicability_pair_required_for_single_direct_basis_law():
    law = load("law_applicability")
    decision = law.applicability_pair_requirement(
        asked_candidate_target=None,
        direct_basis_law_ids=["CN-INVOICE-2023-ART20"],
    )
    assert decision["decision"] == "emit_pair"
    assert decision["applicability_target"] == "CN-INVOICE-2023-ART20"


def test_applicability_pair_target_is_asked_candidate_even_with_multiple_laws():
    law = load("law_applicability")
    decision = law.applicability_pair_requirement(
        asked_candidate_target="CN-OFFICIAL-VEHICLE-2011-HIST",
        direct_basis_law_ids=["CN-A", "CN-B"],
    )
    assert decision["decision"] == "emit_pair"
    assert decision["applicability_target"] == "CN-OFFICIAL-VEHICLE-2011-HIST"


def test_applicability_multi_direct_basis_without_candidate_must_disambiguate():
    law = load("law_applicability")
    decision = law.applicability_pair_requirement(
        asked_candidate_target=None,
        direct_basis_law_ids=["CN-A", "CN-B"],
    )
    assert decision["decision"] == "disambiguate"
    assert decision["applicability_target"] is None, "no guessing a single target"


def test_applicability_no_direct_basis_no_applicable_pair():
    law = load("law_applicability")
    decision = law.applicability_pair_requirement(
        asked_candidate_target=None, direct_basis_law_ids=[],
    )
    assert decision["decision"] == "no_applicable_pair"
    assert decision["applicability_target"] is None


# ============ F. cross-effect regression guards (V2.2.2 wins) ============


def test_review_gate_still_blocked_for_attachment_only_facts():
    """V2.2.2 cases 23/24: attachment-missing facts alone never open the
    review-insufficient gate."""
    eng = load("classification_emission")
    allowed = eng.reimbursement_review_insufficient_gate(
        review_procedure_defect=False,
        required_attachments_missing=True,
        approval_responsibility_facts=False,
        finding_is_review_control=False,
    )
    assert allowed is False


def test_pending_gate_still_closed_without_real_decision_facts():
    """V2.2.2 case-04: no blank/inclusion/pending facts → no pending code."""
    eng = load("classification_emission")
    out = eng.decision_required_codes_gate(
        blank_record=False, inclusion_decision_needed=False,
        pending_or_unconfirmed_facts=False,
    )
    assert out["allowed"] is False
    assert out["codes"] == []


def test_guarded_set_single_source_of_truth_with_scorer():
    """The scorer must derive its guarded set from the module, so the brother
    codes are enforced globally there too."""
    mod = load("conclusion_grounding")
    assert set(mod.CONCLUSION_FACT_REQUIREMENTS) == set(mod.GUARDED_CODES)
    for code, req in mod.CONCLUSION_FACT_REQUIREMENTS.items():
        for field in (req.get("any_of") or []) + (req.get("all_of") or []):
            assert field in mod.FIELD_SUPPORT_ANCHORS, (code, field)
