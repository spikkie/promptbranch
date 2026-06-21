from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_ID = "promptbranch.orchestration.event_intake"
SCHEMA_VERSION = "1.0"
ROOT = Path(__file__).resolve().parent
DEFAULT_EXAMPLES_RELATIVE_DIR = Path("docs") / "design" / "orchestration" / "examples" / "events"
SCHEMA_RELATIVE_PATH = Path("docs") / "design" / "orchestration" / "schemas" / "event_intake.schema.json"
DEFAULT_EXAMPLES_DIR = ROOT / DEFAULT_EXAMPLES_RELATIVE_DIR
SCHEMA_PATH = ROOT / SCHEMA_RELATIVE_PATH
VERSION_PATTERN = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)*$")
EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")

REQUIRED_AUTHORITY = {
    "proposal_only": True,
    "runtime_state_mutation_allowed": False,
    "source_mutation_allowed": False,
    "artifact_adoption_allowed": False,
    "deployment_allowed": False,
    "model_may_execute": False,
    "promptbranch_must_validate": True,
}
ALLOWED_EVENT_TYPES = {"slice_proposal", "validation_proposal", "release_proposal"}
ALLOWED_SLICE_TYPES = {"normal", "repair"}
ALLOWED_ACTION_KINDS = {
    "define_schema",
    "validate_event",
    "record_proposal_fixture",
    "plan_next_slice",
    "release_candidate_request",
}


def display_path(path: Path, *, root: Path | None = None) -> str:
    base = (root or ROOT).resolve()
    try:
        resolved = path.resolve()
    except OSError:
        return str(path)
    try:
        return str(resolved.relative_to(base))
    except ValueError:
        return str(resolved)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"{display_path(path)} must contain a JSON object")
    return value


def repo_relative_path(value: Any, *, root: Path = ROOT) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved


def _require_string(value: dict[str, Any], key: str, source: str, errors: list[str]) -> str:
    text = str(value.get(key) or "").strip()
    if not text:
        errors.append(f"{source}: {key} is required")
    return text


def _validate_authority(value: dict[str, Any], source: str, errors: list[str]) -> None:
    authority = value.get("authority") or {}
    if not isinstance(authority, dict):
        errors.append(f"{source}: authority must be an object")
        authority = {}
    for key, expected in REQUIRED_AUTHORITY.items():
        if authority.get(key) is not expected:
            errors.append(f"{source}: authority.{key} must be {expected!r}")


def _validate_release(value: dict[str, Any], source: str, errors: list[str]) -> None:
    release = value.get("release") or {}
    if not isinstance(release, dict):
        errors.append(f"{source}: release must be an object")
        return
    baseline = _require_string(release, "baseline_version", f"{source}: release", errors)
    target = _require_string(release, "target_version", f"{source}: release", errors)
    slice_type = _require_string(release, "slice_type", f"{source}: release", errors)
    if baseline and not VERSION_PATTERN.match(baseline):
        errors.append(f"{source}: release.baseline_version must be canonical v-prefixed version text")
    if target and not VERSION_PATTERN.match(target):
        errors.append(f"{source}: release.target_version must be canonical v-prefixed version text")
    if baseline and target and baseline == target:
        errors.append(f"{source}: release.target_version must differ from baseline_version")
    if slice_type and slice_type not in ALLOWED_SLICE_TYPES:
        errors.append(f"{source}: release.slice_type must be one of {sorted(ALLOWED_SLICE_TYPES)}")


def _validate_repo(value: dict[str, Any], source: str, errors: list[str]) -> None:
    repo = value.get("repo") or {}
    if not isinstance(repo, dict):
        errors.append(f"{source}: repo must be an object")
        return
    repo_id = _require_string(repo, "id", f"{source}: repo", errors)
    if repo_id and not EVENT_ID_PATTERN.match(repo_id):
        errors.append(f"{source}: repo.id contains unsupported characters")
    path_value = repo.get("path")
    if path_value is not None and repo_relative_path(path_value) is None:
        errors.append(f"{source}: repo.path must be repo-relative and must not contain '..'")


def _validate_proposed_action(value: dict[str, Any], source: str, errors: list[str]) -> None:
    action = value.get("proposed_action") or {}
    if not isinstance(action, dict):
        errors.append(f"{source}: proposed_action must be an object")
        return
    kind = _require_string(action, "kind", f"{source}: proposed_action", errors)
    if kind and kind not in ALLOWED_ACTION_KINDS:
        errors.append(f"{source}: proposed_action.kind must be one of {sorted(ALLOWED_ACTION_KINDS)}")
    _require_string(action, "summary", f"{source}: proposed_action", errors)
    writes = action.get("writes") or []
    if not isinstance(writes, list):
        errors.append(f"{source}: proposed_action.writes must be a list")
        return
    for index, item in enumerate(writes):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{source}: proposed_action.writes[{index}] must be a non-empty string")
            continue
        if repo_relative_path(item) is None:
            errors.append(f"{source}: proposed_action.writes[{index}] must be repo-relative and must not contain '..'")


def _validate_evidence(value: dict[str, Any], source: str, errors: list[str]) -> None:
    evidence = value.get("evidence") or {}
    if not isinstance(evidence, dict):
        errors.append(f"{source}: evidence must be an object")
        return
    status = str(evidence.get("validation_status") or "").strip()
    if status != "proposal_validated_read_only":
        errors.append(f"{source}: evidence.validation_status must be proposal_validated_read_only")
    validated_by = evidence.get("validated_by") or []
    if not isinstance(validated_by, list) or not validated_by:
        errors.append(f"{source}: evidence.validated_by must be a non-empty list")
    elif "scripts/orchestration/validate_event_intake.py" not in validated_by and "pb orchestration validate-event" not in validated_by:
        errors.append(
            f"{source}: evidence.validated_by must include scripts/orchestration/validate_event_intake.py "
            "or pb orchestration validate-event"
        )
    notes = evidence.get("notes") or []
    if not isinstance(notes, list) or not notes:
        errors.append(f"{source}: evidence.notes must be a non-empty list")


def validate_event_intake(value: dict[str, Any], *, source: str = "<memory>") -> list[str]:
    errors: list[str] = []
    if value.get("schema") != SCHEMA_ID:
        errors.append(f"{source}: schema must be {SCHEMA_ID}")
    if value.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{source}: schema_version must be {SCHEMA_VERSION}")
    event_id = _require_string(value, "event_id", source, errors)
    if event_id and not EVENT_ID_PATTERN.match(event_id):
        errors.append(f"{source}: event_id contains unsupported characters")
    event_type = _require_string(value, "event_type", source, errors)
    if event_type and event_type not in ALLOWED_EVENT_TYPES:
        errors.append(f"{source}: event_type must be one of {sorted(ALLOWED_EVENT_TYPES)}")

    _validate_repo(value, source, errors)
    _validate_release(value, source, errors)
    _validate_authority(value, source, errors)
    _validate_proposed_action(value, source, errors)
    _validate_evidence(value, source, errors)
    return errors


def _candidate_repo_roots(start: Path | None = None) -> list[Path]:
    roots: list[Path] = []
    for candidate in (start or Path.cwd()).resolve(), ROOT.resolve():
        for root in (candidate, *candidate.parents):
            if root not in roots:
                roots.append(root)
    return roots


def resolve_examples_root(start: Path | None = None) -> Path:
    for root in _candidate_repo_roots(start):
        examples_dir = root / DEFAULT_EXAMPLES_RELATIVE_DIR
        if examples_dir.is_dir() and any(examples_dir.glob("*.example.json")):
            return root
    return ROOT


def example_paths(root: Path | None = None) -> list[Path]:
    base = root if root is not None else resolve_examples_root()
    examples_dir = base / DEFAULT_EXAMPLES_RELATIVE_DIR
    return sorted(examples_dir.glob("*.example.json"))


def validate_paths(paths: list[Path], *, root: Path | None = None, require_non_empty: bool = False) -> dict[str, Any]:
    display_root = root if root is not None else resolve_examples_root()
    errors: list[str] = []
    validated: list[str] = []
    if require_non_empty and not paths:
        errors.append(
            f"no event-intake JSON files found under {display_path(display_root / DEFAULT_EXAMPLES_RELATIVE_DIR, root=display_root)}; "
            "pass explicit event JSON paths or run from a repository containing committed orchestration examples"
        )
    for path in paths:
        try:
            value = read_json(path)
        except Exception as exc:  # noqa: BLE001 - CLI validator should collect deterministic file errors.
            errors.append(f"{display_path(path, root=display_root)}: failed to read JSON: {exc}")
            continue
        source = display_path(path, root=display_root)
        event_errors = validate_event_intake(value, source=source)
        if event_errors:
            errors.extend(event_errors)
        else:
            validated.append(source)
    return {
        "ok": not errors,
        "action": "orchestration_validate_event",
        "status": "event_intake_valid" if not errors else "event_intake_invalid",
        "schema": SCHEMA_ID,
        "schema_version": SCHEMA_VERSION,
        "validated_count": len(validated),
        "validated_paths": validated,
        "errors": errors,
        "proposal_only": True,
        "runtime_state_mutation_allowed": False,
        "source_mutation_allowed": False,
        "artifact_adoption_allowed": False,
        "deployment_allowed": False,
        "accepted_state_written": False,
        "operator_action": "fix_event_json_and_rerun_validator" if errors else "proposal_may_be_reviewed; no state was mutated",
    }


def render_text(payload: dict[str, Any]) -> str:
    if payload.get("ok"):
        return (
            f"{payload['status']}: validated_count={payload['validated_count']} "
            "proposal_only=true accepted_state_written=false"
        )
    lines = [f"{payload['status']}: {len(payload.get('errors') or [])} error(s)"]
    lines.extend(f"- {error}" for error in payload.get("errors") or [])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate proposal-only Promptbranch orchestration event-intake JSON.")
    parser.add_argument("paths", nargs="*", help="Event-intake JSON files. Defaults to committed examples.")
    parser.add_argument("--json", action="store_true", help="Emit structured validation result as JSON.")
    args = parser.parse_args(argv)

    examples_root = resolve_examples_root()
    paths = [Path(p) for p in args.paths] if args.paths else example_paths(examples_root)
    payload = validate_paths(paths, root=examples_root, require_non_empty=not args.paths)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text(payload))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
