#!/usr/bin/env python3
import argparse
import json
from datetime import date
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"


def load_data(path: Path) -> dict:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise TypeError(f"expected object at {path}, got {type(data).__name__}")
    return data


def load_schema(name: str) -> dict:
    path = SCHEMA_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"unknown schema: {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a valid ISO date: {value!r}") from exc


def _validate_semantics(data: dict, schema_name: str) -> None:
    if schema_name == "project-context":
        period = data.get("audit_period") or {}
        start = period.get("start")
        end = period.get("end")
        if start is not None and end is not None:
            if _parse_iso_date(start, "audit_period.start") > _parse_iso_date(end, "audit_period.end"):
                raise ValueError("audit_period.start must not be after audit_period.end")

    if schema_name == "finding":
        evidence = data.get("evidence_status")
        decision = data.get("decision_status")
        if decision == "final":
            if evidence != "confirmed":
                raise ValueError("final finding requires evidence_status=confirmed")
            wording = data.get("final_wording")
            if not isinstance(wording, str) or not wording.strip():
                raise ValueError("final finding requires non-empty final_wording")

    if schema_name == "law":
        start = data.get("effective_from")
        end = data.get("effective_to")
        if start is not None and end is not None:
            if _parse_iso_date(start, "effective_from") > _parse_iso_date(end, "effective_to"):
                raise ValueError("effective_from must not be after effective_to")

        if data.get("status") == "effective":
            if not start:
                raise ValueError("effective law requires effective_from")
            source = data.get("source") or {}
            if source.get("type") not in {"official", "official_archive"}:
                raise ValueError("effective law requires official or official_archive source")
            if source.get("verified") is not True:
                raise ValueError("effective law requires verified source")
            if not (source.get("url") or source.get("identifier")):
                raise ValueError("effective law requires traceable source url or identifier")


def validate_file(path: Path, schema_name: str) -> None:
    data = load_data(Path(path))
    schema = load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)
    _validate_semantics(data, schema_name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Audit Problem Classifier V2 data")
    parser.add_argument("--schema", required=True, help="schema name, e.g. law or finding")
    parser.add_argument("path", type=Path, help="YAML or JSON file to validate")
    args = parser.parse_args()
    validate_file(args.path, args.schema)
    print(f"PASS: {args.path} validates against {args.schema}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
