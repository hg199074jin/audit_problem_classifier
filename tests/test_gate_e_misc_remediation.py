import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_linter():
    path=ROOT/"scripts"/"report_format_lint.py"
    spec=importlib.util.spec_from_file_location("fmt_gatee",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_format_lint_catches_unclosed_ascii_quote_and_ji_zhang_variant():
    module=load_linter()
    assert "ascii_chinese_quotes" in module.lint_report_text('列支 "中文项目。')
    assert "unnormalized_voucher_reference" in module.lint_report_text("记帐-66号凭证")


def test_release_contract_checks_section_anchors_not_historical_numbers():
    text=(ROOT/"tests"/"test_release_contracts.py").read_text(encoding="utf-8")
    assert '"48"' not in text
    assert "Gate D" in (ROOT/"docs"/"v2-verification-report.md").read_text(encoding="utf-8")


def test_migration_documents_spec_implementation_drift():
    text=(ROOT/"docs"/"v2-migration.md").read_text(encoding="utf-8")
    assert "Implementation deviations from frozen spec" in text
    assert "evals/cases/" in text
    assert "references/laws/kaifeng/" in text
