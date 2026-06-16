from __future__ import annotations

import fnmatch
import json
import zipfile
from pathlib import Path
from typing import Any


DEFAULT_POLICY_NAME = ".artifact-guardian.yml"


class ArtifactGuardianPolicyError(ValueError):
    """Raised when an artifact guardian policy cannot be loaded or validated."""


def _parse_scalar(value: str) -> Any:
    text = value.strip()
    if not text:
        return ""
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if text == "[]":
        return []
    if text == "{}":
        return {}
    try:
        return int(text)
    except ValueError:
        return text


def _minimal_yaml_load(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by .artifact-guardian.yml.

    This intentionally supports only repo-local policy files with nested mappings
    and scalar lists.  It exists as a no-dependency fallback when PyYAML is not
    installed.
    """

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    pending_list_key: tuple[int, dict[str, Any], str] | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise ArtifactGuardianPolicyError("invalid_yaml_indentation")
        container = stack[-1][1]
        if line.startswith("- "):
            item = _parse_scalar(line[2:])
            if isinstance(container, list):
                container.append(item)
                continue
            if isinstance(container, dict) and not container and len(stack) >= 2:
                parent = stack[-2][1]
                if isinstance(parent, dict):
                    for parent_key, parent_value in list(parent.items()):
                        if parent_value is container:
                            parent[parent_key] = [item]
                            stack[-1] = (stack[-1][0], parent[parent_key])
                            pending_list_key = None
                            break
                    else:
                        raise ArtifactGuardianPolicyError("invalid_yaml_list")
                    continue
            raise ArtifactGuardianPolicyError("invalid_yaml_list")
        if ":" not in line:
            raise ArtifactGuardianPolicyError("invalid_yaml_line")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not isinstance(container, dict):
            raise ArtifactGuardianPolicyError("invalid_yaml_mapping")
        if value == "":
            child: dict[str, Any] = {}
            container[key] = child
            pending_list_key = (indent, container, key)
            stack.append((indent, child))
        else:
            container[key] = _parse_scalar(value)
            pending_list_key = None
    return root


def load_artifact_guardian_policy(policy_path: str | Path) -> dict[str, Any]:
    path = Path(policy_path).expanduser().resolve()
    if not path.is_file():
        raise ArtifactGuardianPolicyError("policy_not_found")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactGuardianPolicyError("policy_unreadable") from exc
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(text)
    except ModuleNotFoundError:
        payload = _minimal_yaml_load(text)
    except Exception as exc:  # pragma: no cover - PyYAML-specific parser detail
        raise ArtifactGuardianPolicyError("policy_invalid_yaml") from exc
    if not isinstance(payload, dict):
        raise ArtifactGuardianPolicyError("policy_not_mapping")
    validate_artifact_guardian_policy(payload)
    return payload


def validate_artifact_guardian_policy(policy: dict[str, Any]) -> None:
    if policy.get("schema_version") != 1:
        raise ArtifactGuardianPolicyError("unsupported_schema_version")
    project = policy.get("project")
    if not isinstance(project, dict):
        raise ArtifactGuardianPolicyError("project_policy_missing")
    if not isinstance(project.get("artifact_pattern"), str) or "{version}" not in project.get("artifact_pattern", ""):
        raise ArtifactGuardianPolicyError("artifact_pattern_invalid")
    if not isinstance(project.get("version_file"), str) or not project.get("version_file"):
        raise ArtifactGuardianPolicyError("version_file_invalid")
    zip_policy = policy.get("zip")
    if not isinstance(zip_policy, dict):
        raise ArtifactGuardianPolicyError("zip_policy_missing")
    for list_key in ("required_entries", "forbidden_entries", "executable_entries"):
        value = policy.get(list_key)
        if value is None:
            if list_key == "executable_entries":
                policy[list_key] = []
                continue
            raise ArtifactGuardianPolicyError(f"{list_key}_missing")
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise ArtifactGuardianPolicyError(f"{list_key}_invalid")
    version_checks = policy.get("version_checks")
    if version_checks is not None and not isinstance(version_checks, dict):
        raise ArtifactGuardianPolicyError("version_checks_invalid")


def _normalize_zip_name(name: str) -> str:
    return str(name or "").replace("\\", "/").lstrip("./").strip()


def _path_matches(name: str, pattern: str) -> bool:
    rel = _normalize_zip_name(name).strip("/")
    pat = _normalize_zip_name(pattern).strip()
    if not rel or not pat:
        return False
    if pat.endswith("/"):
        prefix = pat.strip("/")
        return rel == prefix or rel.startswith(prefix + "/")
    return fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(Path(rel).name, pat)


def _required_entry_present(names: set[str], required: str) -> bool:
    req = _normalize_zip_name(required).strip("/")
    if not req:
        return False
    if req in names:
        return True
    if required.endswith("/"):
        return any(name.startswith(req + "/") for name in names)
    return False


def _zip_wrapper_folder(names: list[str]) -> str | None:
    file_names = [name.strip("/") for name in names if name and not name.endswith("/")]
    top_levels = {name.split("/", 1)[0] for name in file_names}
    if len(top_levels) != 1:
        return None
    only = next(iter(top_levels))
    has_root_file = any("/" not in name for name in file_names)
    return None if has_root_file else only


def _zip_is_executable(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0o777
    return bool(mode & 0o111)


def _failure(failure_class: str, *, path: str | None = None, healable: bool = False, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"failure_class": failure_class, "healable": healable}
    if path is not None:
        payload["path"] = path
    payload.update(extra)
    return payload


def guard_zip_artifact(
    *,
    repo: str | Path,
    zip_path: str | Path,
    version: str,
    policy_path: str | Path | None = None,
) -> dict[str, Any]:
    repo_path = Path(repo).expanduser().resolve()
    policy_file = Path(policy_path).expanduser().resolve() if policy_path else repo_path / DEFAULT_POLICY_NAME
    artifact_path = Path(zip_path).expanduser().resolve()
    failures: list[dict[str, Any]] = []
    checks: dict[str, str] = {
        "policy": "pending",
        "zip_readable": "pending",
        "required_entries": "pending",
        "forbidden_entries": "pending",
        "wrapper_folder": "pending",
        "nested_zip": "pending",
        "version_file": "pending",
        "artifact_name": "pending",
        "executable_bits": "pending",
    }
    try:
        policy = load_artifact_guardian_policy(policy_file)
        checks["policy"] = "passed"
    except ArtifactGuardianPolicyError as exc:
        checks["policy"] = "failed"
        failures.append(_failure("policy_invalid", path=str(policy_file), reason=str(exc), healable=False))
        return _result(repo_path, policy_file, artifact_path, version, checks, failures, entry_count=0)
    if not artifact_path.is_file():
        checks["zip_readable"] = "failed"
        failures.append(_failure("artifact_not_found", path=str(artifact_path), healable=False))
        return _result(repo_path, policy_file, artifact_path, version, checks, failures, entry_count=0)
    try:
        with zipfile.ZipFile(artifact_path) as archive:
            names_list = [_normalize_zip_name(name).strip("/") for name in archive.namelist() if _normalize_zip_name(name).strip("/")]
            names = set(names_list)
            bad_entry = archive.testzip()
            infos = { _normalize_zip_name(info.filename).strip("/"): info for info in archive.infolist() if _normalize_zip_name(info.filename).strip("/") }
            version_file = str(policy["project"].get("version_file") or "VERSION").strip("/")
            try:
                actual_version = archive.read(version_file).decode("utf-8", errors="replace").strip()
            except KeyError:
                actual_version = None
    except zipfile.BadZipFile:
        checks["zip_readable"] = "failed"
        failures.append(_failure("bad_zip", path=str(artifact_path), healable=False))
        return _result(repo_path, policy_file, artifact_path, version, checks, failures, entry_count=0)
    checks["zip_readable"] = "passed" if not bad_entry else "failed"
    if bad_entry:
        failures.append(_failure("bad_zip_entry", path=bad_entry, healable=False))

    missing = [entry for entry in policy["required_entries"] if not _required_entry_present(names, entry)]
    checks["required_entries"] = "passed" if not missing else "failed"
    failures.extend(_failure("required_entry_missing", path=entry, healable=True) for entry in missing)

    forbidden_hits = sorted({name for name in names_list for pattern in policy["forbidden_entries"] if _path_matches(name, pattern)})
    checks["forbidden_entries"] = "passed" if not forbidden_hits else "failed"
    failures.extend(_failure("forbidden_entry_present", path=entry, healable=True) for entry in forbidden_hits)

    wrapper = _zip_wrapper_folder(names_list)
    forbid_wrapper = bool(policy.get("zip", {}).get("forbid_wrapper_folder", False))
    checks["wrapper_folder"] = "passed" if not (forbid_wrapper and wrapper) else "failed"
    if forbid_wrapper and wrapper:
        failures.append(_failure("wrapper_folder_present", path=wrapper, healable=True))

    nested = sorted(name for name in names_list if name.lower().endswith(".zip"))
    forbid_nested = bool(policy.get("zip", {}).get("forbid_nested_zip", False))
    checks["nested_zip"] = "passed" if not (forbid_nested and nested) else "failed"
    if forbid_nested:
        failures.extend(_failure("nested_zip_present", path=entry, healable=True) for entry in nested)

    version_checks = policy.get("version_checks") if isinstance(policy.get("version_checks"), dict) else {}
    if version_checks.get("require_version_file_equals_cli_version", True):
        checks["version_file"] = "passed" if actual_version == version else "failed"
        if actual_version != version:
            failures.append(_failure("version_mismatch", path=version_file, expected_version=version, actual_version=actual_version, healable=False))
    else:
        checks["version_file"] = "skipped"

    artifact_pattern = str(policy["project"].get("artifact_pattern") or "").strip()
    expected_name = artifact_pattern.format(version=version)
    if version_checks.get("require_artifact_name_contains_version", True):
        checks["artifact_name"] = "passed" if artifact_path.name == expected_name else "failed"
        if artifact_path.name != expected_name:
            failures.append(_failure("artifact_name_mismatch", expected_pattern=artifact_pattern, expected_filename=expected_name, actual_filename=artifact_path.name, healable=False))
    else:
        checks["artifact_name"] = "skipped"

    executable_entries = policy.get("executable_entries") or []
    missing_exec = []
    if executable_entries:
        for entry in executable_entries:
            normalized = entry.strip("/")
            info = infos.get(normalized)
            if info is None or not _zip_is_executable(info):
                missing_exec.append(normalized)
        checks["executable_bits"] = "passed" if not missing_exec else "failed"
        failures.extend(_failure("executable_bit_missing", path=entry, healable=True) for entry in missing_exec)
    else:
        checks["executable_bits"] = "passed"
    return _result(repo_path, policy_file, artifact_path, version, checks, failures, entry_count=len(names_list))


def _result(
    repo_path: Path,
    policy_file: Path,
    artifact_path: Path,
    version: str,
    checks: dict[str, str],
    failures: list[dict[str, Any]],
    *,
    entry_count: int,
) -> dict[str, Any]:
    ok = not failures and all(value in {"passed", "skipped"} for value in checks.values())
    return {
        "ok": ok,
        "action": "artifact_guard",
        "repo": str(repo_path),
        "policy": str(policy_file),
        "artifact": str(artifact_path),
        "artifact_filename": artifact_path.name,
        "version": version,
        "status": "guard_passed" if ok else "guard_failed",
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "entry_count": entry_count,
        "healed": False,
        "release_ready": ok,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate a release ZIP against an Artifact Guardian policy.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--zip", dest="zip_path", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--policy")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = guard_zip_artifact(repo=args.repo, zip_path=args.zip_path, version=args.version, policy_path=args.policy)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"ok={result.get('ok')}")
        print(f"status={result.get('status')}")
        print(f"release_ready={result.get('release_ready')}")
        if result.get("failures"):
            print(f"failures={result.get('failure_count')}")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
