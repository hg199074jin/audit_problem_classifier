#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

SUPPORTED_RULES = {
    "no_ascii_chinese_quotes",
    "normalized_voucher_reference",
    "no_raw_dot_date",
}

_ASCII_CHINESE_QUOTES = re.compile(r'["\'][^"\'\n]*[\u4e00-\u9fff][^"\'\n]*["\']')
_UNNORMALIZED_VOUCHER = re.compile(r'(?:记账|转账|收款|付款)\s*[-—－]?\s*\d+\s*号凭证')
_RAW_DOT_DATE = re.compile(r'\b20\d{2}\.\d{1,2}(?:\.\d{1,2})?\b')


def lint_report_text(text: str) -> list[str]:
    if not isinstance(text, str):
        raise TypeError("report text must be a string")

    violations: list[str] = []
    if _ASCII_CHINESE_QUOTES.search(text):
        violations.append("ascii_chinese_quotes")
    if _UNNORMALIZED_VOUCHER.search(text):
        violations.append("unnormalized_voucher_reference")
    if _RAW_DOT_DATE.search(text):
        violations.append("raw_dot_date")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint hard-format rules in audit report text")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    text = args.path.read_text(encoding="utf-8")
    violations = lint_report_text(text)
    if violations:
        for item in violations:
            print(f"FAIL {item}")
        return 1
    print("PASS report format lint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
