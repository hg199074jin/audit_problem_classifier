from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    full = ROOT / path
    assert full.exists(), f"missing {path}"
    return full.read_text(encoding="utf-8")


def test_skill_is_orchestrator_and_workflow_order_is_fixed():
    text = read("SKILL.md")
    workflow = text.split("## 固定工作流", 1)[1].split("## 法规使用原则", 1)[0]
    stages = [
        "1. **读取材料**",
        "2. **建立 Project Context**",
        "3. **生成待决策事项**",
        "4. **HARD-GATE**",
        "5. **构建 Source Records**",
        "6. **拆分 Findings**",
        "7. **分类**",
        "8. **证据等级**",
        "9. **法规适用过滤**",
        "10. **定性措辞**",
        "11. **报告化输出**",
        "12. **覆盖/金额/法规/格式自检**",
    ]
    positions = [workflow.index(stage) for stage in stages]
    assert positions == sorted(positions)
    for ref in (
        "rules/decision-gate.md",
        "rules/classification.md",
        "rules/evidence-and-wording.md",
        "rules/law-applicability.md",
        "rules/coverage-and-amount.md",
    ):
        assert ref in text


def test_decision_gate_separates_blocking_decisions_from_profile_defaults():
    text = read("rules/decision-gate.md")
    assert "必须阻断" in text
    assert "不再反复询问" in text
    assert "profiles/firm-default.yaml" in text
    for token in ("记录取舍", "拆分", "金额口径", "重大定性", "法规适用"):
        assert token in text


def test_classification_preserves_all_twelve_main_categories():
    text = read("rules/classification.md")
    for code in ("ZD", "YS", "ZJ", "ZC", "CG", "XM", "FY", "SJ", "KJ", "NK", "SW", "QT"):
        assert f"| {code} |" in text
    assert "FY、KJ、SW" in text
    assert "一个主类" in text


def test_evidence_wording_keeps_high_risk_boundaries():
    text = read("rules/evidence-and-wording.md")
    for required in ("串通报价嫌疑", "占用不写挪用", "少收不写损失", "虚开", "倒签"):
        assert required in text
    assert "管理不规范" in text and "涉嫌违法违规" in text


def test_coverage_rule_forbids_duplicate_record_and_voucher_totals():
    text = read("rules/coverage-and-amount.md")
    assert "Source Record" in text
    assert "多个 Finding" in text
    assert "原始记录数" in text
    assert "voucher_amount" in text
    assert "不得重复" in text


def test_firm_profile_contains_stable_format_defaults_only():
    path = ROOT / "profiles" / "firm-default.yaml"
    assert path.exists()
    profile = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert profile["date_format"] == "YYYY/MM"
    assert profile["amount_format"] == "#,##0.00元"
    assert profile["quote_style"] == "chinese_curly"
    assert profile["voucher_reference"] == "{number}号凭证"
    assert profile["ordinary_expense_grouping"] == "by_issue_nature"
    assert set(profile["report_modes"]) == {"classification_report", "special_audit_report"}
