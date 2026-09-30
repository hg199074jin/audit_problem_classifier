#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

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


def validate_file(path: Path, schema_name: str) -> None:
    data = load_data(Path(path))
    schema = load_schema(schema_name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(data)


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
