from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "orchestration" / "validate_examples.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_examples", VALIDATOR)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_orchestration_examples_are_safe_and_consistent() -> None:
    module = _load_validator()
    assert module.validate() == []


def test_orchestration_foundation_files_exist() -> None:
    expected = [
        "orchestration/README.md",
        "orchestration/docs/json_orchestration_state_mvp.md",
        "orchestration/docs/k8s_game_mvp_contract.md",
        "orchestration/docs/proposal_vs_accepted_event.md",
        "orchestration/docs/branching_strategy.md",
        "orchestration/docs/global_mvp_plan.md",
        "orchestration/docs/detailed_mvp_setup_plan.md",
        "orchestration/docs/llm_provider_policy.md",
        "orchestration/docs/json_orchestration_state_mvp_v0_1_0_high_level_canvas.md",
        "orchestration/docs/json_orchestration_state_mvp_v0_1_0_low_level_canvas.md",
        "orchestration/decisions/ADR-0001-json-orchestration-state-mvp.md",
        "orchestration/decisions/ADR-0002-chatgpt-proposal-vs-promptbranch-accepted-event.md",
        "orchestration/decisions/ADR-0003-chatgpt-only-llm-provider.md",
        "orchestration/decisions/ADR-0004-ollama-bakeoff-failed-threshold.md",
        "orchestration/schemas/context.schema.json",
        "orchestration/schemas/decision.schema.json",
        "orchestration/schemas/evidence.schema.json",
        "orchestration/examples/k8s_game_context.example.json",
        "orchestration/examples/k8s_game_decision.example.json",
        "orchestration/examples/k8s_game_evidence.example.json",
        "orchestration/state_machines/k8s_game_mvp.state_machine.json",
        "docs/release-v0.1.0.md",
    ]
    missing = [path for path in expected if not (ROOT / path).exists()]
    assert missing == []
