import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    full = ROOT / path
    assert full.exists(), f"missing release artifact: {path}"
    return full.read_text(encoding="utf-8")


def test_readme_describes_v2_architecture_and_maintenance_paths():
    text = read("README.md")
    for token in (
        "V2",
        "Audit Finding Engine",
        "Project Context",
        "Source Record",
        "Finding",
        "Law Object",
        "HARD-GATE",
        "references/laws/",
        "historical",
        "evals/score.py",
        "docs/v2-migration.md",
        "docs/v2-verification-report.md",
    ):
        assert token in text, f"README missing {token!r}"


def test_agent_default_prompt_preserves_hard_gate_and_applicability_order():
    data = yaml.safe_load(read("agents/openai.yaml"))
    prompt = data["interface"]["default_prompt"]
    for token in ("HARD-GATE", "Project Context", "law applicability"):
        assert token in prompt
    assert data["interface"]["display_name"]


def test_legacy_test_prompts_explicitly_point_to_v2_evals_without_losing_six_cases():
    data = json.loads(read("test-prompts.json"))
    assert isinstance(data, list) and len(data) == 6
    ids = {row["id"] for row in data}
    assert len(ids) == 6
    for row in data:
        assert row.get("v2_eval_case")
        assert row["v2_eval_case"].startswith("evals/cases/")


def test_migration_and_verification_reports_exist_and_state_runtime_limit():
    migration = read("docs/v2-migration.md")
    verification = read("docs/v2-verification-report.md")
    assert "V1" in migration and "V2" in migration
    assert "references/laws-legacy-v1.md" in migration
    for heading in ("Gate C", "Gate D", "Gate E"):
        assert heading in verification
    assert "Skill runtime" in verification


def test_ci_workflow_runs_tests_law_validation_and_deterministic_eval():
    text = read(".github/workflows/v2-ci.yml")
    assert "pytest -q" in text
    assert "validate_v2_data.py --schema law" in text
    assert "evals/score.py" in text
