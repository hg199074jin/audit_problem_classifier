"""V2.2.2 fact-grounding boundary tests (RED → GREEN).

Negative scenarios mirror the V2.2.1 Gate D over-emissions
(procurement-specificity, mode-a/b-complete-regression); positive scenarios
protect legitimate emissions (question-first-gate, explicit review-control
failure).
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "conclusion_grounding_v222", ROOT / "scripts" / "conclusion_grounding.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------- negative: evidence-chain uncertainty is NOT a decision item


def test_negative_evidence_chain_open_is_not_a_decision_item():
    """V2.2.1 case-04: 'evidence chain not closed' must not license
    decision_required_pending_items."""
    mod = load_module()
    source = (
        "采购清单中同时存在三家报价异常一致、未附询价资料、报价单盖章不规范、"
        "成交公告供应商名称错误和长期租赁未做成本比较，请分类整理。"
    )
    result = {
        "conclusion_codes": ["decision_required_pending_items"],
        # runtime derived the flag from "evidence not closed", no real citation
        "fact_grounding": [
            {"field": "pending_or_unconfirmed_facts", "value": True, "citation": "证据链未闭合需要补证"}
        ],
    }
    violations = mod.verify_grounding(result, source)
    assert violations, "ungrounded pending-items flag must be rejected"
    cleaned, _ = mod.enforce_grounding(result, source)
    assert "decision_required_pending_items" not in cleaned["conclusion_codes"]


def test_negative_missing_attachment_is_not_review_failure():
    """V2.2.1 case-23/24: a missing distribution list is not an independent
    review-control failure."""
    mod = load_module()
    source = (
        "某事业单位2025年5月一笔办公用品报销，66号凭证，金额2,300元，附件缺少领用清单。"
        "事实和金额已确认，不存在其他待决策事项。"
    )
    result = {
        "conclusion_codes": ["reimbursement_review_insufficient"],
        "fact_grounding": [
            {"field": "required_attachments_missing", "value": True, "citation": "附件缺少领用清单"},
            {"field": "finding_is_review_control", "value": True, "citation": "附件缺少领用清单"},
        ],
    }
    violations = mod.verify_grounding(result, source)
    assert violations, "attachment-missing must not license review failure"
    cleaned, _ = mod.enforce_grounding(result, source)
    assert "reimbursement_review_insufficient" not in cleaned["conclusion_codes"]


def test_negative_citation_must_be_verbatim_in_source():
    """A hallucinated citation (not present in the input) is not grounding."""
    mod = load_module()
    source = "某单位问题汇总表，其中一行只有摘要和金额、无问题描述的汇总行。"
    result = {
        "conclusion_codes": ["decision_required_pending_items"],
        "fact_grounding": [
            {"field": "blank_record", "value": True, "citation": "用户已确认该记录可予排除"}
        ],
    }
    violations = mod.verify_grounding(result, source)
    assert any("citation" in v for v in violations)


def test_negative_enforce_downgrades_proceed_to_needs_review():
    mod = load_module()
    source = "采购清单中同时存在三家报价异常一致、未附询价资料，请分类整理。"
    result = {
        "gate_status": "proceed",
        "conclusion_codes": ["decision_required_pending_items"],
    }
    cleaned, violations = mod.enforce_grounding(result, source)
    assert violations
    assert cleaned["gate_status"] == "needs_review"
    assert cleaned["conclusion_codes"] == []


# ---------------- positive: grounded legitimate emissions


def test_positive_blank_record_with_citation_is_allowed():
    """question-first-gate: a genuinely blank record licenses the code."""
    mod = load_module()
    source = (
        "这是某单位的问题汇总表（其中含一行只有摘要和金额、无问题描述的汇总行，"
        "一条问题描述空白的奖励提成记录，若干标注“待落实”“是否有文件”的记录）。"
        "请直接整理成专项审核报告。"
    )
    result = {
        "conclusion_codes": ["decision_required_pending_items"],
        "fact_grounding": [
            {"field": "blank_record", "value": True, "citation": "一条问题描述空白的奖励提成记录"},
            {"field": "pending_or_unconfirmed_facts", "value": True, "citation": "若干标注“待落实”“是否有文件”的记录"},
        ],
    }
    violations = mod.verify_grounding(result, source)
    assert violations == [], violations
    cleaned, _ = mod.enforce_grounding(result, source)
    assert cleaned["conclusion_codes"] == ["decision_required_pending_items"]


def test_positive_explicit_review_procedure_failure_is_allowed():
    """An explicit, cited review-procedure failure licenses the code."""
    mod = load_module()
    source = (
        "该笔报销单已经部门负责人签批，但财务审核岗位未履行审核程序即予入账，"
        "审核记录缺失。"
    )
    result = {
        "conclusion_codes": ["reimbursement_review_insufficient"],
        "fact_grounding": [
            {"field": "review_procedure_defect", "value": True, "citation": "财务审核岗位未履行审核程序即予入账"},
            {"field": "finding_is_review_control", "value": True, "citation": "财务审核岗位未履行审核程序即予入账"},
        ],
    }
    violations = mod.verify_grounding(result, source)
    assert violations == [], violations


def test_positive_unguarded_codes_are_untouched():
    mod = load_module()
    source = "三家供应商报价异常一致，存在串通报价嫌疑。"
    result = {"conclusion_codes": ["collusive_bidding_not_established"]}
    assert mod.verify_grounding(result, source) == []


# ---------------- CLI behaviour


def test_cli_enforce_returns_nonzero_and_cleaned_json(tmp_path):
    mod = load_module()
    source_file = tmp_path / "source.txt"
    source_file.write_text("附件缺少领用清单。", encoding="utf-8")
    result_file = tmp_path / "result.json"
    result_file.write_text(
        json.dumps({"conclusion_codes": ["reimbursement_review_insufficient"]}),
        encoding="utf-8",
    )
    import subprocess, sys
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "conclusion_grounding.py"),
         "--result", str(result_file), "--source", str(source_file), "--enforce"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    cleaned = json.loads(proc.stdout)
    assert cleaned["conclusion_codes"] == []
