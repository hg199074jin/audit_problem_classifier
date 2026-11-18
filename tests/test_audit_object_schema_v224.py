"""V2.2.4 audit-object schema contract tests (RED first).

The typed contract frozen in docs/decisions/v224-invoice-audit-object-adjudication.md:
- object_kind / assertion_kind / polarity / directness / decision enums are closed;
- every assertion carries a verbatim quote bound to a real source_id;
- authorization fields (decision, reason_codes) are machine outputs, not free text.
"""

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def load_schema():
    return json.loads((ROOT / "schemas" / "audit-object.schema.json").read_text(encoding="utf-8"))


def validate(obj):
    jsonschema.validate(obj, load_schema())


def base_object(**overrides):
    obj = {
        "object_id": "AO-1",
        "source_record_id": "SR-1",
        "object_kind": "invoice_compliance",
        "directness": "primary",
        "decision": "authorized_sw",
        "assertions": [
            {
                "assertion_kind": "invoice_buyer_mismatch",
                "polarity": "affirmative",
                "source_id": "prompt",
                "quote": "购买方信息与实际报销单位存在不一致",
            }
        ],
    }
    obj.update(overrides)
    return obj


def test_valid_authorized_object_passes_with_cjk_quote():
    validate(base_object())


def test_valid_candidate_shape_passes():
    validate(base_object(decision="candidate", reason_codes=[], review_reason=None))


def test_unknown_object_kind_rejected():
    try:
        validate(base_object(object_kind="expense_reimbursment"))  # typo
    except jsonschema.ValidationError:
        return
    raise AssertionError("unknown object_kind must be rejected")


def test_unknown_assertion_kind_rejected():
    obj = base_object()
    obj["assertions"][0]["assertion_kind"] = "looks_suspicious"
    try:
        validate(obj)
    except jsonschema.ValidationError:
        return
    raise AssertionError("unknown assertion_kind must be rejected")


def test_unknown_polarity_rejected():
    obj = base_object()
    obj["assertions"][0]["polarity"] = "maybe"
    try:
        validate(obj)
    except jsonschema.ValidationError:
        return
    raise AssertionError("unknown polarity must be rejected")


def test_empty_quote_rejected():
    obj = base_object()
    obj["assertions"][0]["quote"] = ""
    try:
        validate(obj)
    except jsonschema.ValidationError:
        return
    raise AssertionError("empty quote must be rejected")


def test_illegal_source_id_rejected():
    obj = base_object()
    obj["assertions"][0]["source_id"] = "expected"
    try:
        validate(obj)
    except jsonschema.ValidationError:
        return
    raise AssertionError("source_id outside {prompt,context} must be rejected")


def test_unknown_decision_rejected():
    try:
        validate(base_object(decision="approved"))
    except jsonschema.ValidationError:
        return
    raise AssertionError("unknown decision must be rejected")


def test_duplicated_object_id_rejected():
    schema = load_schema()
    twin = base_object()
    try:
        jsonschema.validate([twin, twin], schema)
    except jsonschema.ValidationError:
        return
    raise AssertionError("duplicated object_id must be rejected by array-level constraint")


def test_assertions_must_not_be_empty():
    try:
        validate(base_object(assertions=[]))
    except jsonschema.ValidationError:
        return
    raise AssertionError("object without assertions must be rejected")


def test_optional_offsets_must_be_non_negative_ints():
    def with_offset(start, end):
        obj = base_object()
        obj["assertions"][0] = {**obj["assertions"][0], "start": start, "end": end}
        return obj
    validate(with_offset(0, 12))
    try:
        validate(with_offset(-1, 3))
    except jsonschema.ValidationError:
        return
    raise AssertionError("negative offset must be rejected")
