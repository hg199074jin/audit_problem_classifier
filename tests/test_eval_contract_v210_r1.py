"""GPT-002-R1 contract-completion tests: global applicability status/target pairing."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_scorer():
    path = ROOT / "evals" / "score.py"
    spec = importlib.util.spec_from_file_location("score_v210_r1", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _all_cases():
    rows = []
    for path in sorted((ROOT / "evals" / "cases").glob("*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                rows.append(json.loads(raw))
    return rows


def _fixture_rows(name):
    return {
        row["id"]: row
        for line in (ROOT / "evals/fixtures" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in [json.loads(line)]
    }


LAW_ID = "CN-INVOICE-2023-ART20"


def test_result_schema_rejects_status_without_target():
    schema = json.loads((ROOT / "evals/result.schema.json").read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator
    validator = Draft202012Validator(schema)
    result = {
        "id": "x", "contract_version": "2.1.1", "text": "",
        "applicability_status": "applicable",
        "law_ids": [LAW_ID],
        "law_roles": {LAW_ID: "direct_basis"},
    }
    errors = list(validator.iter_errors(result))
    assert errors, "status without target must fail result schema"
    assert any("applicability_target" in str(list(e.path)) or "applicability_target" in e.message for e in errors)


def test_result_schema_rejects_target_without_status():
    schema = json.loads((ROOT / "evals/result.schema.json").read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator
    validator = Draft202012Validator(schema)
    result = {
        "id": "x", "contract_version": "2.1.1", "text": "",
        "applicability_target": LAW_ID,
        "law_ids": [LAW_ID],
        "law_roles": {LAW_ID: "direct_basis"},
    }
    errors = list(validator.iter_errors(result))
    assert errors, "target without status must fail result schema"


def test_case_schema_rejects_expected_status_without_target():
    schema = json.loads((ROOT / "evals/case.schema.json").read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator
    validator = Draft202012Validator(schema)
    case = {
        "contract_version": "2.1.1", "id": "x", "domain": "law-applicability", "prompt": "p",
        "context": {}, "expected": {"applicability_status": "applicable"},
    }
    errors = list(validator.iter_errors(case))
    assert errors, "expected status without target must fail case schema"


def test_scorer_rejects_status_without_target_globally():
    scorer = load_scorer()
    case = {
        "contract_version": "2.1.1", "id": "x", "domain": "law-applicability", "prompt": "p", "context": {},
        "expected": {"law_ids": [LAW_ID]},
    }
    result = {
        "contract_version": "2.1.1", "id": "x", "text": "",
        "applicability_status": "applicable",
        "law_ids": [LAW_ID],
        "law_roles": {LAW_ID: "direct_basis"},
    }
    outcome = scorer.score_case(case, result)
    assert not outcome.passed
    assert any("applicability_target" in failure for failure in outcome.failures)


def test_scorer_rejects_target_without_status_globally():
    scorer = load_scorer()
    case = {
        "contract_version": "2.1.1", "id": "x", "domain": "law-applicability", "prompt": "p", "context": {},
        "expected": {"law_ids": [LAW_ID]},
    }
    result = {
        "contract_version": "2.1.1", "id": "x", "text": "",
        "applicability_target": LAW_ID,
        "law_ids": [LAW_ID],
        "law_roles": {LAW_ID: "direct_basis"},
    }
    outcome = scorer.score_case(case, result)
    assert not outcome.passed
    assert any("applicability_status" in failure for failure in outcome.failures)


def test_scorer_applicable_structured_target_must_be_in_law_ids():
    scorer = load_scorer()
    case = {
        "contract_version": "2.1.1", "id": "x", "domain": "law-applicability", "prompt": "p", "context": {},
        "expected": {},
    }
    result = {
        "contract_version": "2.1.1", "id": "x", "text": "",
        "applicability_status": "applicable",
        "applicability_target": LAW_ID,
        "law_ids": ["CN-GOV-PURCHASE-SERVICES-2020-ART18-PUBLIC-INSTITUTION-REF"],
        "law_roles": {"CN-GOV-PURCHASE-SERVICES-2020-ART18-PUBLIC-INSTITUTION-REF": "direct_basis"},
    }
    outcome = scorer.score_case(case, result)
    assert not outcome.passed
    assert any("law_ids" in failure and "applicability_target" in failure for failure in outcome.failures)


def test_scorer_not_applicable_structured_target_must_be_in_excluded():
    scorer = load_scorer()
    case = {
        "contract_version": "2.1.1", "id": "x", "domain": "law-applicability", "prompt": "p", "context": {},
        "expected": {},
    }
    result = {
        "contract_version": "2.1.1", "id": "x", "text": "",
        "applicability_status": "not_applicable",
        "applicability_target": "CN-OFFICIAL-VEHICLE-2011-HIST",
        "excluded_law_ids": [],
    }
    outcome = scorer.score_case(case, result)
    assert not outcome.passed
    assert any("excluded_law_ids" in failure and "applicability_target" in failure for failure in outcome.failures)


def test_scorer_needs_review_structured_target_cannot_enter_law_ids():
    scorer = load_scorer()
    case = {
        "contract_version": "2.1.1", "id": "x", "domain": "law-applicability", "prompt": "p", "context": {},
        "expected": {},
    }
    result = {
        "contract_version": "2.1.1", "id": "x", "text": "",
        "applicability_status": "needs_review",
        "applicability_target": "CN-INVOICE-2023-ART20",
        "law_ids": ["CN-INVOICE-2023-ART20"],
        "law_roles": {"CN-INVOICE-2023-ART20": "direct_basis"},
    }
    outcome = scorer.score_case(case, result)
    assert not outcome.passed
    assert any("needs_review" in failure and "law_ids" in failure for failure in outcome.failures)


def test_scorer_accepts_paired_status_target_structured_binding():
    scorer = load_scorer()
    case = {
        "contract_version": "2.1.1", "id": "x", "domain": "law-applicability", "prompt": "p", "context": {},
        "expected": {},
    }
    result = {
        "contract_version": "2.1.1", "id": "x", "text": "",
        "applicability_status": "applicable",
        "applicability_target": LAW_ID,
        "law_ids": [LAW_ID],
        "law_roles": {LAW_ID: "direct_basis"},
    }
    outcome = scorer.score_case(case, result)
    assert outcome.passed, outcome.failures


def test_scorer_accepts_paired_user_claim_target_without_membership():
    scorer = load_scorer()
    case = {
        "contract_version": "2.1.1", "id": "x", "domain": "law-applicability", "prompt": "p", "context": {},
        "expected": {},
    }
    result = {
        "contract_version": "2.1.1", "id": "x", "text": "",
        "applicability_status": "not_applicable",
        "applicability_target": "candidate_rule:policy-effective-2026-01-01",
    }
    outcome = scorer.score_case(case, result)
    assert outcome.passed, outcome.failures


def test_every_status_bearing_case_has_expected_target():
    missing = [
        row["id"]
        for row in _all_cases()
        if "applicability_status" in row.get("expected", {}) and "applicability_target" not in row.get("expected", {})
    ]
    assert missing == [], f"cases missing expected applicability_target: {missing}"


def test_every_status_bearing_case_target_is_law_id_or_context_declared():
    law_catalog_ids = {
        data["id"]
        for data in _iter_law_objects()
    }
    problems = []
    for row in _all_cases():
        exp = row.get("expected", {})
        target = exp.get("applicability_target")
        if target is None:
            continue
        if target in law_catalog_ids:
            continue
        context = json.dumps(row.get("context", {}), ensure_ascii=False)
        if target in context:
            continue
        problems.append(f"{row['id']}: target {target!r} is neither a structured Law ID nor declared in context")
    assert problems == [], problems


def _iter_law_objects():
    import yaml
    for path in (ROOT / "references" / "laws").rglob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("id"), str):
            yield data


def test_passing_fixtures_status_bearing_rows_have_targets():
    rows = _fixture_rows("passing-results")
    missing = [
        cid
        for cid, row in rows.items()
        if "applicability_status" in row and "applicability_target" not in row
    ]
    assert missing == [], f"passing fixtures missing applicability_target: {missing}"


def test_failing_fixtures_status_bearing_rows_have_targets():
    rows = _fixture_rows("failing-results")
    missing = [
        cid
        for cid, row in rows.items()
        if "applicability_status" in row and "applicability_target" not in row
    ]
    assert missing == [], f"failing fixtures missing applicability_target: {missing}"


def test_full_deterministic_suite_passes_after_target_completion():
    import subprocess
    proc = subprocess.run(
        ["python", str(ROOT / "evals" / "score.py"), "--cases", str(ROOT / "evals" / "cases"),
         "--results", str(ROOT / "evals" / "fixtures" / "passing-results.jsonl")],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "SUMMARY 26/26 passed" in proc.stdout
