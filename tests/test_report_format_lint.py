import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINTER = ROOT / "scripts" / "report_format_lint.py"


def load_module():
    assert LINTER.exists(), "missing report format linter"
    spec = importlib.util.spec_from_file_location("report_format_lint", LINTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_clean_report_text_has_no_hard_format_violations():
    module = load_module()
    text = "2025/05，66号凭证，列支“优抚对象疗养纪念水壶”2,300.00元。"
    assert module.lint_report_text(text) == []


def test_ascii_quotes_around_chinese_are_rejected():
    module = load_module()
    violations = module.lint_report_text('列支 "优抚对象疗养纪念水壶" 2,300.00元。')
    assert "ascii_chinese_quotes" in violations


def test_ledger_prefix_in_voucher_reference_is_rejected():
    module = load_module()
    violations = module.lint_report_text("2025/05，记账-66号凭证，列支办公费。")
    assert "unnormalized_voucher_reference" in violations


def test_raw_dot_date_is_rejected():
    module = load_module()
    violations = module.lint_report_text("2025.5.31，66号凭证，列支办公费。")
    assert "raw_dot_date" in violations
