from __future__ import annotations

import copy
import json
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "orchestration" / "validate_grill.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_grill", VALIDATOR)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_grill_examples_are_valid_and_complete() -> None:
    module = _load_validator()
    paths = module.example_paths()
    assert len(paths) == 7
    assert module.validate_paths(paths) == []


def test_grill_provider_policy_rejects_ollama_local_and_unknown() -> None:
    module = _load_validator()
    example = module.read_json(module.example_paths()[0])
    for provider_kind in ("ollama", "local_llm", "unknown"):
        candidate = copy.deepcopy(example)
        candidate["provider"]["kind"] = provider_kind
        errors = module.validate_grill_envelope(candidate)
        assert any("provider.kind rejected" in error for error in errors)


def test_grill_rejects_model_execution_and_unvalidated_output() -> None:
    module = _load_validator()
    example = module.read_json(module.example_paths()[0])

    may_execute = copy.deepcopy(example)
    may_execute["constraints"]["model_may_execute"] = True
    errors = module.validate_grill_envelope(may_execute)
    assert any("constraints.model_may_execute" in error for error in errors)

    unvalidated = copy.deepcopy(example)
    unvalidated["constraints"]["promptbranch_must_validate"] = False
    errors = module.validate_grill_envelope(unvalidated)
    assert any("constraints.promptbranch_must_validate" in error for error in errors)


def test_grill_foundation_files_exist() -> None:
    expected = [
        "docs/design/orchestration/schemas/grill.schema.json",
        "scripts/orchestration/validate_grill.py",
        "docs/design/orchestration/docs/current_status.md",
        "docs/design/orchestration/docs/release_line_reconciliation.md",
        "docs/release-v0.1.40.md",
    ]
    expected.extend(
        f"docs/design/orchestration/examples/grills/{stage}.example.json"
        for stage in [
            "G0_intent",
            "G1_mvp",
            "G2_architecture",
            "G3_slice",
            "G4_implementation",
            "G5_release_deployment",
            "G6_maintenance",
        ]
    )
    missing = [path for path in expected if not (ROOT / path).exists()]
    assert missing == []


def test_grill_schema_file_is_valid_json() -> None:
    schema = json.loads((ROOT / "docs/design/orchestration/schemas/grill.schema.json").read_text(encoding="utf-8"))
    assert schema["$id"] == "promptbranch.orchestration.grill.schema.json"
    assert schema["properties"]["schema"]["const"] == "promptbranch.orchestration.grill"
    assert "ollama" not in schema["properties"]["provider"]["properties"]["kind"]["enum"]
    assert "local_llm" not in schema["properties"]["provider"]["properties"]["kind"]["enum"]
