from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    full = ROOT / path
    assert full.exists(), f"missing reference file: {path}"
    return full.read_text(encoding="utf-8")

def test_new_reference_layers_exist():
    for path in (
        "references/cases/README.md",
        "references/cases/core-boundaries.md",
        "references/cases/2026-09-retirement-center-anonymized.md",
        "references/management-suggestions/index.md",
        "references/report-templates/classification-report.md",
        "references/report-templates/special-audit-report.md",
    ):
        assert (ROOT / path).exists(), f"missing {path}"

def test_cases_are_non_normative_and_rules_win_conflicts():
    readme = read("references/cases/README.md")
    core = read("references/cases/core-boundaries.md")
    project = read("references/cases/2026-09-retirement-center-anonymized.md")
    for text in (readme, core, project):
        assert "规则" in text
        assert "优先" in text or "权威" in text
    assert "匿名化" in project
    assert "非规范性" in project
    assert "军休中心" not in project

def test_core_boundaries_link_to_rules_instead_of_redefining_category_system():
    core = read("references/cases/core-boundaries.md")
    assert "rules/classification.md" in core
    assert "rules/evidence-and-wording.md" in core
    assert "rules/law-applicability.md" in core
    assert "| ZD |" not in core
    assert "| YS |" not in core
    assert "河南现行分散采购限额100万元" not in core

def test_report_templates_reference_firm_profile_and_preserve_mode_contracts():
    mode_a = read("references/report-templates/classification-report.md")
    mode_b = read("references/report-templates/special-audit-report.md")
    for text in (mode_a, mode_b):
        assert "profiles/firm-default.yaml" in text
    assert "模式A" in mode_a or "模式 A" in mode_a
    assert "覆盖校验" in mode_a
    assert "模式B" in mode_b or "模式 B" in mode_b
    assert "超过 3 条" in mode_b
    assert "三段式" in mode_b

def test_legacy_reference_entrypoints_are_compatibility_wrappers_only():
    examples = read("references/audit-problem-examples.md")
    suggestions = read("references/management-suggestions.md")
    structure = read("references/report-structure.md")
    assert "兼容" in examples and "references/cases/" in examples
    assert "不定义" in examples or "不得覆盖" in examples
    assert "references/management-suggestions/index.md" in suggestions
    assert "references/report-templates/" in structure
    assert "河南现行分散采购限额100万元" not in examples
    assert "豫财购〔2020〕4号" not in examples

def test_management_suggestions_cannot_change_classification_or_professional_rules():
    text = read("references/management-suggestions/index.md")
    assert "不得反向改变" in text or "不得覆盖" in text
    assert "rules/classification.md" in text
    assert "rules/evidence-and-wording.md" in text
