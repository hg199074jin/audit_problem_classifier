"""V2.2.4 evidence-grounded audit object authorization tests (RED first).

Frozen semantics: docs/decisions/v224-invoice-audit-object-adjudication.md
- every assertion's quote must be verbatim in its declared immutable source;
- negative/hypothetical statements never authorize a defect or focus;
- the invoice gate turns verified objects into authorized_sw / incidental_fy /
  needs_review / no_invoice_finding / rejected — naked booleans are not authority.
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


def load_module():
    spec = importlib.util.spec_from_file_location(
        "audit_object_grounding_v224", ROOT / "scripts" / "audit_object_grounding.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assertion(kind, quote, polarity="affirmative", source_id="prompt", **extra):
    a = {"assertion_kind": kind, "polarity": polarity, "source_id": source_id, "quote": quote}
    a.update(extra)
    return a


def case10_object(decision="candidate", directness="primary"):
    return {
        "object_id": "AO-1",
        "source_record_id": None,
        "object_kind": "invoice_compliance",
        "directness": directness,
        "decision": decision,
        "assertions": [
            assertion("invoice_buyer_mismatch", "购买方信息与实际报销单位存在不一致"),
            assertion("explicit_invoice_characterization_request", "请定性"),
            assertion("true_transaction", "交易真实"),
            assertion("false_invoicing_evidence_absent", "目前没有虚构交易、无真实业务开票或其他虚开发票证据", polarity="negative"),
        ],
    }


# ---------------- quote/source verification ----------------


def test_verbatim_quote_in_declared_source_passes():
    mod = load_module()
    assert mod.verify_audit_objects([case10_object()], SOURCES) == []


def test_quote_not_in_source_is_invalid():
    mod = load_module()
    obj = case10_object()
    obj["assertions"][0]["quote"] = "购买方名称完全错误"
    violations = mod.verify_audit_objects([obj], SOURCES)
    assert any("QUOTE_NOT_IN_SOURCE" in v for v in violations)


def test_quote_from_wrong_source_id_is_invalid():
    mod = load_module()
    obj = case10_object()
    obj["assertions"][0]["source_id"] = "context"  # text only exists in prompt
    violations = mod.verify_audit_objects([obj], SOURCES)
    assert any("QUOTE_NOT_IN_SOURCE" in v for v in violations)


def test_wrong_offsets_rejected():
    mod = load_module()
    obj = case10_object()
    obj["assertions"][0]["start"] = 99
    obj["assertions"][0]["end"] = 120
    violations = mod.verify_audit_objects([obj], SOURCES)
    assert any("OFFSET_MISMATCH" in v for v in violations)


def test_correct_offsets_accepted():
    mod = load_module()
    obj = case10_object()
    quote = obj["assertions"][0]["quote"]
    start = PROMPT.index(quote)
    obj["assertions"][0]["start"] = start
    obj["assertions"][0]["end"] = start + len(quote)
    assert mod.verify_audit_objects([obj], SOURCES) == []


def test_unknown_source_id_rejected():
    mod = load_module()
    obj = case10_object()
    obj["assertions"][0]["source_id"] = "expected"
    violations = mod.verify_audit_objects([obj], SOURCES)
    assert any("SOURCE_ID_UNKNOWN" in v for v in violations)


def test_anchor_unsupported_quote_rejected_even_if_verbatim():
    """A verbatim span that does not support the claimed fact kind fails
    closed (semantic support, not just presence)."""
    mod = load_module()
    obj = case10_object()
    obj["assertions"][0] = assertion("invoice_buyer_mismatch", "货物确已取得")
    violations = mod.verify_audit_objects([obj], SOURCES)
    assert any("ANCHOR_NOT_SUPPORTED" in v for v in violations)


def test_negative_polarity_cannot_authorize_defect():
    mod = load_module()
    obj = case10_object()
    obj["assertions"][0]["polarity"] = "negative"
    decision = mod.authorize_audit_objects([obj], SOURCES)
    assert decision["objects"][0]["decision"] == "needs_review"
    assert any("FOCUS_WITHOUT_DEFECT" in rc for rc in decision["objects"][0]["reason_codes"])


def test_hypothetical_assertion_never_authorizes():
    mod = load_module()
    obj = case10_object()
    obj["assertions"][0]["polarity"] = "hypothetical"
    decision = mod.authorize_audit_objects([obj], SOURCES)
    assert decision["objects"][0]["decision"] == "needs_review"


# ---------------- authorization decision table ----------------


def test_case10_shape_authorizes_sw():
    mod = load_module()
    decision = mod.authorize_audit_objects([case10_object()], SOURCES)
    obj = decision["objects"][0]
    assert obj["decision"] == "authorized_sw"
    assert any("SW_AUTHORIZED" in rc for rc in obj["reason_codes"])
    # negative evidence must appear as a restriction, not an authorizer
    assert any(rc.startswith("RESTRICT") for rc in obj["reason_codes"])


def test_incidental_defect_without_focus_is_fy():
    mod = load_module()
    obj = case10_object(directness="incidental")
    obj["assertions"] = [assertion("invoice_buyer_mismatch", "购买方信息与实际报销单位存在不一致")]
    decision = mod.authorize_audit_objects([obj], SOURCES)
    assert decision["objects"][0]["decision"] == "incidental_fy"


def test_primary_without_focus_needs_review():
    mod = load_module()
    obj = case10_object()
    obj["assertions"] = [assertion("invoice_buyer_mismatch", "购买方信息与实际报销单位存在不一致")]
    decision = mod.authorize_audit_objects([obj], SOURCES)
    assert decision["objects"][0]["decision"] == "needs_review"
    assert any("PRIMARY_WITHOUT_FOCUS" in rc for rc in decision["objects"][0]["reason_codes"])


def test_focus_without_defect_needs_review():
    mod = load_module()
    obj = case10_object()
    obj["assertions"] = [assertion("explicit_invoice_characterization_request", "请定性")]
    decision = mod.authorize_audit_objects([obj], SOURCES)
    assert decision["objects"][0]["decision"] == "needs_review"
    assert any("FOCUS_WITHOUT_DEFECT" in rc for rc in decision["objects"][0]["reason_codes"])


def test_negative_only_assertions_yield_no_invoice_finding():
    mod = load_module()
    obj = case10_object()
    obj["assertions"] = [
        assertion("true_transaction", "交易真实"),
        assertion("false_invoicing_evidence_absent", "目前没有虚构交易、无真实业务开票或其他虚开发票证据", polarity="negative"),
    ]
    decision = mod.authorize_audit_objects([obj], SOURCES)
    assert decision["objects"][0]["decision"] == "no_invoice_finding"
    assert any("NEGATIVE_ONLY" in rc for rc in decision["objects"][0]["reason_codes"])


def test_noncompliant_invoice_object_authorizes_sw_without_focus():
    mod = load_module()
    src = {"prompt": "某事业单位报销取得不符合规定的发票并作为财务报销凭证，交易真实。请形成完整审计问题报告。", "context": ""}
    obj = case10_object()
    obj["assertions"] = [
        assertion("noncompliant_invoice_obtained", "取得不符合规定的发票并作为财务报销凭证"),
        assertion("true_transaction", "交易真实"),
    ]
    decision = mod.authorize_audit_objects([obj], src)
    assert decision["objects"][0]["decision"] == "authorized_sw"


def test_all_invalid_assertions_rejected():
    mod = load_module()
    obj = case10_object()
    obj["assertions"] = [assertion("invoice_buyer_mismatch", "这句不在源输入里")]
    decision = mod.authorize_audit_objects([obj], SOURCES)
    assert decision["objects"][0]["decision"] == "rejected"


# ---------------- metamorphic properties ----------------


def test_whitespace_mutation_breaks_quote():
    mod = load_module()
    mutated = {"prompt": PROMPT.replace("请定性", "请 定性"), "context": ""}
    violations = mod.verify_audit_objects([case10_object()], mutated)
    assert any("QUOTE_NOT_IN_SOURCE" in v for v in violations)


def test_characterization_request_paraphrases_are_supported():
    """Anchor family must cover professional paraphrases of the 定性 request
    ('请对该发票问题定性'), not only the formal-case wording ('请定性')."""
    mod = load_module()
    src = "某单位一笔报销发票购买方信息与实际报销单位不一致，交易真实。请对该发票问题定性。"
    obj = case10_object()
    obj["assertions"] = [
        assertion("invoice_buyer_mismatch", "购买方信息与实际报销单位不一致"),
        assertion("explicit_invoice_characterization_request", "请对该发票问题定性"),
    ]
    decision = mod.authorize_audit_objects([obj], {"prompt": src, "context": ""})
    assert decision["objects"][0]["decision"] == "authorized_sw", decision["objects"][0]["reason_codes"]


def test_false_invoicing_absent_alone_cannot_authorize_sw():
    """The negative sentence alone must never trigger SW (R3 root cause)."""
    mod = load_module()
    obj = case10_object()
    obj["assertions"] = [
        assertion("false_invoicing_evidence_absent", "目前没有虚构交易、无真实业务开票或其他虚开发票证据", polarity="negative"),
        assertion("explicit_invoice_characterization_request", "请定性"),
    ]
    decision = mod.authorize_audit_objects([obj], SOURCES)
    assert decision["objects"][0]["decision"] == "needs_review"


# ---------------- CLI contract ----------------


def test_cli_authorize(tmp_path):
    objects_file = tmp_path / "objects.json"
    objects_file.write_text(json.dumps([case10_object()], ensure_ascii=False), encoding="utf-8")
    source_file = tmp_path / "source.json"
    source_file.write_text(json.dumps(SOURCES, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_object_grounding.py"),
         "authorize", "--input", str(objects_file), "--source", str(source_file)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["objects"][0]["decision"] == "authorized_sw"


def test_cli_rejected_object_exits_nonzero(tmp_path):
    objects_file = tmp_path / "objects.json"
    bad = case10_object()
    bad["assertions"] = [assertion("invoice_buyer_mismatch", "源输入中不存在的引文")]
    objects_file.write_text(json.dumps([bad], ensure_ascii=False), encoding="utf-8")
    source_file = tmp_path / "source.json"
    source_file.write_text(json.dumps(SOURCES, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_object_grounding.py"),
         "authorize", "--input", str(objects_file), "--source", str(source_file)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
