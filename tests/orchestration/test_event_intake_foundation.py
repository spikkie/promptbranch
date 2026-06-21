from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "promptbranch_orchestration.py"
VALIDATOR = ROOT / "scripts" / "orchestration" / "validate_event_intake.py"
EXAMPLE = ROOT / "docs" / "design" / "orchestration" / "examples" / "events" / "v0.1.79_event_intake.example.json"
SCHEMA = ROOT / "docs" / "design" / "orchestration" / "schemas" / "event_intake.schema.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("promptbranch_orchestration", MODULE)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _read_example() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_event_intake_schema_and_example_exist() -> None:
    assert VALIDATOR.is_file()
    assert SCHEMA.is_file()
    assert EXAMPLE.is_file()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["$id"] == "promptbranch.orchestration.event_intake.schema.json"
    assert schema["properties"]["schema"]["const"] == "promptbranch.orchestration.event_intake"


def test_event_intake_committed_example_is_valid() -> None:
    module = _load_module()
    payload = module.validate_paths([EXAMPLE])
    assert payload["ok"] is True
    assert payload["status"] == "event_intake_valid"
    assert payload["validated_count"] == 1
    assert payload["proposal_only"] is True
    assert payload["accepted_state_written"] is False
    assert payload["source_mutation_allowed"] is False
    assert payload["artifact_adoption_allowed"] is False


def test_event_intake_rejects_mutating_authority_flags() -> None:
    module = _load_module()
    candidate = _read_example()
    authority = candidate["authority"]
    assert isinstance(authority, dict)
    authority["artifact_adoption_allowed"] = True
    authority["source_mutation_allowed"] = True
    authority["runtime_state_mutation_allowed"] = True

    errors = module.validate_event_intake(candidate, source="candidate.json")

    assert any("authority.artifact_adoption_allowed must be False" in error for error in errors)
    assert any("authority.source_mutation_allowed must be False" in error for error in errors)
    assert any("authority.runtime_state_mutation_allowed must be False" in error for error in errors)


def test_event_intake_rejects_absolute_and_parent_relative_paths() -> None:
    module = _load_module()
    candidate = _read_example()
    repo = candidate["repo"]
    assert isinstance(repo, dict)
    repo["path"] = "/tmp/outside"
    action = candidate["proposed_action"]
    assert isinstance(action, dict)
    action["writes"] = ["../outside.json"]

    errors = module.validate_event_intake(candidate, source="candidate.json")

    assert any("repo.path must be repo-relative" in error for error in errors)
    assert any("proposed_action.writes[0] must be repo-relative" in error for error in errors)


def test_event_intake_rejects_same_baseline_and_target_version() -> None:
    module = _load_module()
    candidate = _read_example()
    release = candidate["release"]
    assert isinstance(release, dict)
    release["target_version"] = release["baseline_version"]

    errors = module.validate_event_intake(candidate, source="candidate.json")

    assert any("target_version must differ" in error for error in errors)


def test_event_intake_cli_payload_is_fail_closed(tmp_path: Path) -> None:
    module = _load_module()
    candidate = copy.deepcopy(_read_example())
    authority = candidate["authority"]
    assert isinstance(authority, dict)
    authority["model_may_execute"] = True
    path = tmp_path / "bad-event.json"
    path.write_text(json.dumps(candidate), encoding="utf-8")

    payload = module.validate_paths([path])

    assert payload["ok"] is False
    assert payload["status"] == "event_intake_invalid"
    assert payload["accepted_state_written"] is False
    assert payload["source_mutation_allowed"] is False
    assert payload["artifact_adoption_allowed"] is False
    assert any("authority.model_may_execute must be False" in error for error in payload["errors"])
