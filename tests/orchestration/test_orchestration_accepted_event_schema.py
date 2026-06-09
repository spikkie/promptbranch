from __future__ import annotations

import copy
import json
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "orchestration" / "validate_accepted_event.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_accepted_event", VALIDATOR)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_accepted_event_examples_are_valid() -> None:
    module = _load_validator()
    paths = module.example_paths()
    assert len(paths) == 7
    assert module.validate_paths(paths) == []


def test_committed_accepted_event_examples_cover_all_grill_stages() -> None:
    module = _load_validator()
    stages = {module.read_json(path)["source_grill"]["stage"] for path in module.example_paths()}
    assert stages == {
        "G0_intent",
        "G1_mvp",
        "G2_architecture",
        "G3_slice",
        "G4_implementation",
        "G5_release_deployment",
        "G6_maintenance",
    }


def test_accepted_event_foundation_files_exist() -> None:
    expected = [
        "docs/design/orchestration/schemas/accepted_event.schema.json",
        "docs/design/orchestration/examples/accepted_events/G0_intent.accepted_event.example.json",
        "docs/design/orchestration/examples/accepted_events/G1_mvp.accepted_event.example.json",
        "docs/design/orchestration/examples/accepted_events/G2_architecture.accepted_event.example.json",
        "docs/design/orchestration/examples/accepted_events/G3_slice.accepted_event.example.json",
        "docs/design/orchestration/examples/accepted_events/G4_implementation.accepted_event.example.json",
        "docs/design/orchestration/examples/accepted_events/G5_release_deployment.accepted_event.example.json",
        "docs/design/orchestration/examples/accepted_events/G6_maintenance.accepted_event.example.json",
        "scripts/orchestration/validate_accepted_event.py",
        "docs/release-v0.1.57.md",
    ]
    missing = [path for path in expected if not (ROOT / path).exists()]
    assert missing == []


def test_accepted_event_schema_file_is_valid_json() -> None:
    schema = json.loads(
        (ROOT / "docs/design/orchestration/schemas/accepted_event.schema.json").read_text(encoding="utf-8")
    )
    assert schema["$id"] == "promptbranch.orchestration.accepted_event.schema.json"
    assert schema["properties"]["schema"]["const"] == "promptbranch.orchestration.accepted_event"
    constraints = schema["properties"]["constraints"]["properties"]
    assert constraints["runtime_state_mutation_allowed"]["const"] is False
    assert constraints["source_mutation_allowed"]["const"] is False
    assert constraints["artifact_adoption_allowed"]["const"] is False
    assert constraints["deployment_allowed"]["const"] is False


def test_accepted_event_rejects_runtime_state_mutation() -> None:
    module = _load_validator()
    example = module.read_json(module.example_paths()[0])
    candidate = copy.deepcopy(example)
    candidate["constraints"]["runtime_state_mutation_allowed"] = True

    errors = module.validate_accepted_event(candidate)

    assert any("constraints.runtime_state_mutation_allowed" in error for error in errors)


def test_accepted_event_transition_must_match_source_grill_recommendation() -> None:
    module = _load_validator()
    example = module.read_json(module.example_paths()[0])
    candidate = copy.deepcopy(example)
    candidate["accepted_transition"]["from"] = "intake_accepted"
    candidate["accepted_transition"]["to"] = "grill_me_accepted"

    errors = module.validate_accepted_event(candidate)

    assert any("must match source grill recommendation" in error for error in errors)


def test_accepted_event_rejects_non_state_machine_transition() -> None:
    module = _load_validator()
    example = module.read_json(module.example_paths()[0])
    candidate = copy.deepcopy(example)
    candidate["accepted_transition"]["from"] = "draft"
    candidate["accepted_transition"]["to"] = "maintenance_ready"

    errors = module.validate_accepted_event(candidate)

    assert any("is not a k8s-game MVP state-machine transition" in error for error in errors)


def test_accepted_event_rejects_stale_source_grill_hash() -> None:
    module = _load_validator()
    example = module.read_json(module.example_paths()[0])
    candidate = copy.deepcopy(example)
    candidate["source_grill"]["sha256"] = "0" * 64

    errors = module.validate_accepted_event(candidate)

    assert any("source_grill.sha256 mismatch" in error for error in errors)


def test_accepted_event_rejects_external_source_grill_path() -> None:
    module = _load_validator()
    example = module.read_json(module.example_paths()[0])
    candidate = copy.deepcopy(example)
    candidate["source_grill"]["path"] = "/tmp/G0_intent.example.json"

    errors = module.validate_accepted_event(candidate)

    assert any("source_grill.path must be a repo-relative path" in error for error in errors)
