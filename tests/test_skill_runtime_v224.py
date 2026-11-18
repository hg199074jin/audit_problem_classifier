"""V2.2.4 runtime delivery boundary tests (RED first).

The Skill can only deliver a machine result containing an invoice
(irregularity/SW) finding when the SAME delivery carries verified audit
objects; `verify_skill_delivery` is the pre-final enforcement the workflow
must run (SKILL step 13), and `invoice-object` is the runtime CLI of the
production gate.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROMPT = (
    "报销发票记载的购买方信息与实际报销单位存在不一致，但交易真实、货物确已取得，"
    "目前没有虚构交易、无真实业务开票或其他虚开发票证据。请定性。"
)
SOURCES = {"prompt": PROMPT, "context": ""}


def authorized_objects():
    return [{
        "object_id": "AO-1",
        "source_record_id": None,
        "object_kind": "invoice_compliance",
        "directness": "primary",
        "decision": "authorized_sw",
        "assertions": [
            {"assertion_kind": "invoice_buyer_mismatch", "polarity": "affirmative",
             "source_id": "prompt", "quote": "购买方信息与实际报销单位存在不一致"},
            {"assertion_kind": "explicit_invoice_characterization_request", "polarity": "affirmative",
             "source_id": "prompt", "quote": "请定性"},
        ],
    }]


def sw_result(with_objects=True):
    result = {
        "gate_status": "proceed",
        "category": "SW",
        "finding_types": ["invoice_information_irregularity"],
        "conclusion_codes": ["invoice_irregularity_not_false_invoicing_established"],
    }
    if with_objects:
        result["audit_objects"] = authorized_objects()
    return result


def load_delivery():
    spec = importlib.util.spec_from_file_location(
        "verify_skill_delivery_v224", ROOT / "scripts" / "verify_skill_delivery.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sw_delivery_with_verified_objects_passes():
    mod = load_delivery()
    failures = mod.verify_delivery(sw_result(with_objects=True), SOURCES)
    assert failures == []


def test_sw_delivery_without_audit_objects_is_refused():
    mod = load_delivery()
    failures = mod.verify_delivery(sw_result(with_objects=False), SOURCES)
    assert any("SW_WITHOUT_AUTHORIZED_OBJECT" in f for f in failures)


def test_sw_delivery_with_unverifiable_quote_is_refused():
    mod = load_delivery()
    result = sw_result(with_objects=True)
    result["audit_objects"][0]["assertions"][0]["quote"] = "伪造的引文"
    failures = mod.verify_delivery(result, SOURCES)
    assert failures, "delivery with fabricated quote must be refused"


def test_fy_delivery_without_objects_passes():
    mod = load_delivery()
    result = {
        "gate_status": "proceed",
        "category": "FY",
        "finding_types": ["expense_supporting_documents_nonstandard"],
    }
    assert mod.verify_delivery(result, SOURCES) == []


def test_needs_review_without_objects_passes():
    mod = load_delivery()
    result = {"gate_status": "needs_review"}
    assert mod.verify_delivery(result, SOURCES) == []


def test_cli_delivery_enforcement(tmp_path):
    result_file = tmp_path / "result.json"
    result_file.write_text(json.dumps(sw_result(with_objects=False), ensure_ascii=False), encoding="utf-8")
    source_file = tmp_path / "source.json"
    source_file.write_text(json.dumps(SOURCES, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_skill_delivery.py"),
         "--result", str(result_file), "--source", str(source_file)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert proc.stdout.strip() == "", "refused delivery must not emit a result"
    assert "VIOLATION" in proc.stderr


def test_cli_invoice_object_subcommand(tmp_path):
    facts = {
        "audit_objects": authorized_objects(),
        "sources": SOURCES,
    }
    facts_file = tmp_path / "facts.json"
    facts_file.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "classification_emission.py"),
         "invoice-object", "--input", str(facts_file)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["decision"] == "sw_independent"
    assert out["emit_invoice_information_irregularity"] is True
