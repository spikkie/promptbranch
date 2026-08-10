from __future__ import annotations

import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

TOOL_SPEC_SCHEMA = "promptbranch.tool.authoring"
TOOL_SPEC_SCHEMA_VERSION = "1.0"
BUNDLE_SCHEMA = "promptbranch.tool_authoring.bundle"
BUNDLE_SCHEMA_VERSION = "1.0"
SKILL_NAME = "promptbranch-tool-authoring"
SKILL_REL = Path(".promptbranch/skills/promptbranch-tool-authoring/SKILL.md")
EXAMPLE_REL = Path(".promptbranch/skills/promptbranch-tool-authoring/examples/read-version.tool.json")
SCHEMA_REL = Path("promptbranch_protocol/schemas/tool.authoring.schema.json")
FIXED_ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)
BUNDLE_ROOT = SKILL_NAME
ID_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)+$")
FAILURE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
RISK_VALUES = {"read", "external_process", "write", "destructive"}
AUTHORITY_EXPECTED = {
    "registration": "proposal_only",
    "execution": "not_granted",
    "mutation": "not_granted",
    "release": "not_granted",
    "publication": "not_granted",
    "adoption": "not_granted",
}
REQUIRED_SPEC_KEYS = {
    "schema", "schema_version", "id", "description", "provider", "risk", "read_only",
    "input_schema", "authority", "validation", "evidence", "failure",
}
BUNDLE_PAYLOAD_ENTRIES = (
    f"{BUNDLE_ROOT}/SKILL.md",
    f"{BUNDLE_ROOT}/TOOL_SPEC.schema.json",
    f"{BUNDLE_ROOT}/examples/read-version.tool.json",
    f"{BUNDLE_ROOT}/PROJECT_SOURCE.md",
    f"{BUNDLE_ROOT}/AGENTS.md",
)
BUNDLE_ENTRIES = (*BUNDLE_PAYLOAD_ENTRIES, f"{BUNDLE_ROOT}/manifest.json")


class ToolAuthoringError(ValueError):
    pass


def _canonical_json(data: Any) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _version(repo: Path) -> str:
    path = repo / "VERSION"
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ToolAuthoringError(f"version_unavailable:{exc}") from exc
    if not value.startswith("v"):
        raise ToolAuthoringError("version_must_be_v_prefixed")
    return value


def _read_required(repo: Path, rel: Path) -> bytes:
    path = (repo / rel).resolve()
    try:
        path.relative_to(repo.resolve())
    except ValueError as exc:
        raise ToolAuthoringError(f"source_outside_repo:{rel.as_posix()}") from exc
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ToolAuthoringError(f"source_unavailable:{rel.as_posix()}:{exc}") from exc


def _string_list(value: Any, *, nonempty: bool = False) -> bool:
    if not isinstance(value, list) or (nonempty and not value):
        return False
    return all(isinstance(item, str) and bool(item.strip()) for item in value) and len(value) == len(set(value))


def validate_tool_spec(spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    keys = set(spec)
    missing = sorted(REQUIRED_SPEC_KEYS - keys)
    extra = sorted(keys - REQUIRED_SPEC_KEYS)
    if missing:
        errors.append("missing_fields:" + ",".join(missing))
    if extra:
        errors.append("unknown_fields:" + ",".join(extra))
    if spec.get("schema") != TOOL_SPEC_SCHEMA:
        errors.append("schema_mismatch")
    if spec.get("schema_version") != TOOL_SPEC_SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    tool_id = spec.get("id")
    if not isinstance(tool_id, str) or not ID_RE.fullmatch(tool_id):
        errors.append("invalid_id")
    for field in ("description", "provider"):
        if not isinstance(spec.get(field), str) or not str(spec.get(field)).strip():
            errors.append(f"invalid_{field}")
    risk = spec.get("risk")
    read_only = spec.get("read_only")
    if risk not in RISK_VALUES:
        errors.append("invalid_risk")
    if not isinstance(read_only, bool):
        errors.append("read_only_must_be_boolean")
    elif risk == "read" and read_only is not True:
        errors.append("read_risk_requires_read_only")
    elif risk in (RISK_VALUES - {"read"}) and read_only is not False:
        errors.append("non_read_risk_requires_read_only_false")

    input_schema = spec.get("input_schema")
    if not isinstance(input_schema, dict):
        errors.append("input_schema_must_be_object")
    else:
        if input_schema.get("type") != "object":
            errors.append("input_schema_type_must_be_object")
        if not isinstance(input_schema.get("properties"), dict):
            errors.append("input_schema_properties_must_be_object")
        if input_schema.get("additionalProperties") is not False:
            errors.append("input_schema_must_reject_additional_properties")
        required = input_schema.get("required", [])
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required) or len(required) != len(set(required)):
            errors.append("input_schema_required_invalid")
        elif isinstance(input_schema.get("properties"), dict) and any(item not in input_schema["properties"] for item in required):
            errors.append("input_schema_required_not_declared")

    authority = spec.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority_must_be_object")
    else:
        if set(authority) != set(AUTHORITY_EXPECTED):
            errors.append("authority_fields_mismatch")
        for key, expected in AUTHORITY_EXPECTED.items():
            if authority.get(key) != expected:
                errors.append(f"authority_not_fail_closed:{key}")

    validation = spec.get("validation")
    if not isinstance(validation, dict) or set(validation) != {"preconditions", "validators"}:
        errors.append("validation_contract_invalid")
    else:
        if not _string_list(validation.get("preconditions")):
            errors.append("preconditions_invalid")
        if not _string_list(validation.get("validators"), nonempty=True):
            errors.append("validators_required")

    evidence = spec.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != {"required", "contract", "fields"}:
        errors.append("evidence_contract_invalid")
    else:
        if evidence.get("required") is not True:
            errors.append("evidence_must_be_required")
        if not isinstance(evidence.get("contract"), str) or not evidence.get("contract", "").strip():
            errors.append("evidence_contract_required")
        if not _string_list(evidence.get("fields"), nonempty=True):
            errors.append("evidence_fields_required")

    failure = spec.get("failure")
    if not isinstance(failure, dict) or set(failure) != {"mode", "codes"}:
        errors.append("failure_contract_invalid")
    else:
        if failure.get("mode") != "fail_closed":
            errors.append("failure_mode_must_be_fail_closed")
        codes = failure.get("codes")
        if not _string_list(codes, nonempty=True) or not all(FAILURE_CODE_RE.fullmatch(code) for code in codes or []):
            errors.append("failure_codes_invalid")

    return {
        "ok": not errors,
        "action": "tool_authoring_validate_spec",
        "status": "valid" if not errors else "invalid",
        "schema": TOOL_SPEC_SCHEMA,
        "schema_version": TOOL_SPEC_SCHEMA_VERSION,
        "tool_id": tool_id,
        "errors": errors,
        "authority": dict(AUTHORITY_EXPECTED),
        "execution_authority_granted": False,
        "mutation_authority_granted": False,
    }


def validate_tool_spec_file(path: str | Path) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "action": "tool_authoring_validate_spec", "status": "invalid_json", "path": str(target), "errors": [str(exc)]}
    if not isinstance(data, dict):
        return {"ok": False, "action": "tool_authoring_validate_spec", "status": "invalid", "path": str(target), "errors": ["spec_must_be_object"]}
    payload = validate_tool_spec(data)
    payload["path"] = str(target)
    return payload


def validate_tool_authoring_source(repo_path: str | Path = ".") -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    errors: list[str] = []
    try:
        skill = _read_required(repo, SKILL_REL).decode("utf-8")
        schema = json.loads(_read_required(repo, SCHEMA_REL).decode("utf-8"))
        example = json.loads(_read_required(repo, EXAMPLE_REL).decode("utf-8"))
    except (ToolAuthoringError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"ok": False, "action": "tool_authoring_validate_source", "status": "invalid", "repo_path": str(repo), "errors": [str(exc)]}
    if "name: promptbranch-tool-authoring" not in skill:
        errors.append("skill_name_missing")
    for phrase in (
        "Authoring is proposal-only",
        "additionalProperties: false",
        "fail closed",
        "does not register a tool",
    ):
        if phrase not in skill:
            errors.append(f"skill_required_phrase_missing:{phrase}")
    if not isinstance(schema, dict) or schema.get("title") != "Promptbranch deterministic tool authoring specification":
        errors.append("schema_document_invalid")
    example_validation = validate_tool_spec(example if isinstance(example, dict) else {})
    if not example_validation.get("ok"):
        errors.extend(f"example:{item}" for item in example_validation.get("errors") or [])
    return {
        "ok": not errors,
        "action": "tool_authoring_validate_source",
        "status": "valid" if not errors else "invalid",
        "repo_path": str(repo),
        "version": _version(repo) if not errors else None,
        "skill": SKILL_NAME,
        "schema_path": SCHEMA_REL.as_posix(),
        "example_path": EXAMPLE_REL.as_posix(),
        "example_validation": example_validation,
        "errors": errors,
        "authority": dict(AUTHORITY_EXPECTED),
        "execution_authority_granted": False,
        "mutation_authority_granted": False,
        "release_authority_granted": False,
        "publication_authority_granted": False,
        "adoption_authority_granted": False,
    }


def _project_source_text(*, version: str, skill_text: str, schema_text: str, example_text: str) -> bytes:
    text = f"""# Promptbranch Tool Authoring — portable Project Source\n\nRelease: `{version}`\n\nThis source teaches deterministic Promptbranch tool authoring. It is **proposal-only** and grants no execution, mutation, release, publication, or adoption authority.\n\n## Skill procedure\n\n{skill_text.rstrip()}\n\n## Canonical tool-spec schema\n\n```json\n{schema_text.rstrip()}\n```\n\n## Minimal valid example\n\n```json\n{example_text.rstrip()}\n```\n\n## Control-plane boundary\n\nA tool specification is not a registered or executable tool. Separate Promptbranch validation and operator-authorized control-plane transitions are required before any implementation or execution. Unknown or ambiguous state fails closed.\n"""
    return text.encode("utf-8")


def _agents_text(*, version: str) -> bytes:
    return f"""# Coding-agent instructions: Promptbranch tool authoring\n\nBundle release: `{version}`\n\n1. Read `SKILL.md` before proposing a tool.\n2. Validate authored JSON against `TOOL_SPEC.schema.json` and the semantic rules in the skill.\n3. Keep `authority.registration=proposal_only`. All execution, mutation, release, publication, and adoption authority fields remain `not_granted`.\n4. Do not register, implement, execute, publish, or adopt a proposed tool merely because the authoring contract validates.\n5. Reject undeclared input properties, ambiguous risk, missing validators/evidence, and non-fail-closed failure semantics.\n6. Use `examples/read-version.tool.json` only as a structural example, not as execution permission.\n\nThis bundle is guidance and validation material only.\n""".encode("utf-8")


def build_tool_authoring_bundle(repo_path: str | Path = ".") -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    source_validation = validate_tool_authoring_source(repo)
    if not source_validation.get("ok"):
        raise ToolAuthoringError("tool_authoring_source_invalid:" + ";".join(source_validation.get("errors") or []))
    version = _version(repo)
    skill_bytes = _read_required(repo, SKILL_REL)
    schema_bytes = _read_required(repo, SCHEMA_REL)
    example_bytes = _read_required(repo, EXAMPLE_REL)
    payload_files: dict[str, bytes] = {
        f"{BUNDLE_ROOT}/SKILL.md": skill_bytes,
        f"{BUNDLE_ROOT}/TOOL_SPEC.schema.json": schema_bytes,
        f"{BUNDLE_ROOT}/examples/read-version.tool.json": example_bytes,
        f"{BUNDLE_ROOT}/PROJECT_SOURCE.md": _project_source_text(
            version=version,
            skill_text=skill_bytes.decode("utf-8"),
            schema_text=schema_bytes.decode("utf-8"),
            example_text=example_bytes.decode("utf-8"),
        ),
        f"{BUNDLE_ROOT}/AGENTS.md": _agents_text(version=version),
    }
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "skill": SKILL_NAME,
        "source_version": version,
        "bundle_root": BUNDLE_ROOT,
        "determinism": {
            "entry_order": "lexicographic",
            "zip_compression": "stored",
            "zip_timestamp": "2020-01-01T00:00:00Z",
            "file_mode": "0644",
        },
        "files": [
            {"path": path, "sha256": _sha256(payload_files[path]), "size_bytes": len(payload_files[path])}
            for path in sorted(payload_files)
        ],
        "authority": {
            "tool_authoring_only": True,
            "execution_authority_granted": False,
            "mutation_authority_granted": False,
            "release_authority_granted": False,
            "publication_authority_granted": False,
            "adoption_authority_granted": False,
        },
        "failure_semantics": "fail_closed",
    }
    files = dict(payload_files)
    files[f"{BUNDLE_ROOT}/manifest.json"] = _canonical_json(manifest)
    return {
        "ok": True,
        "action": "tool_authoring_build_bundle",
        "status": "bundle_built",
        "version": version,
        "skill": SKILL_NAME,
        "manifest": manifest,
        "files": files,
        "source_validation": source_validation,
    }


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=FIXED_ZIP_TIMESTAMP)
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.flag_bits = 0
    info.internal_attr = 0
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.compress_type = zipfile.ZIP_STORED
    info.extra = b""
    info.comment = b""
    return info


def export_tool_authoring_bundle(
    repo_path: str | Path = ".",
    output: str | Path | None = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    repo = Path(repo_path).expanduser().resolve()
    built = build_tool_authoring_bundle(repo)
    version = built["version"]
    target = Path(output).expanduser() if output is not None else Path.cwd() / f"{SKILL_NAME}_{version}.zip"
    target = target.resolve()
    if target.exists() and not force:
        raise ToolAuthoringError(f"output_exists:{target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    files: dict[str, bytes] = built["files"]
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED, strict_timestamps=True) as archive:
        archive.comment = b""
        for path in sorted(files):
            archive.writestr(_zip_info(path), files[path], compress_type=zipfile.ZIP_STORED)
    verification = verify_tool_authoring_bundle(target)
    if not verification.get("ok"):
        target.unlink(missing_ok=True)
        raise ToolAuthoringError("export_verification_failed:" + ";".join(verification.get("errors") or []))
    return {
        "ok": True,
        "action": "tool_authoring_export_bundle",
        "status": "bundle_exported",
        "skill": SKILL_NAME,
        "source_version": version,
        "output": str(target),
        "sha256": _sha256(target.read_bytes()),
        "size_bytes": target.stat().st_size,
        "entry_count": len(BUNDLE_ENTRIES),
        "entries": list(sorted(BUNDLE_ENTRIES)),
        "verification": verification,
        "authority": built["manifest"]["authority"],
    }


def verify_tool_authoring_bundle(path: str | Path) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    errors: list[str] = []
    try:
        with zipfile.ZipFile(target, "r") as archive:
            names = archive.namelist()
            expected = sorted(BUNDLE_ENTRIES)
            if names != expected:
                errors.append("bundle_entries_mismatch")
            file_bytes: dict[str, bytes] = {}
            for info in archive.infolist():
                pure = PurePosixPath(info.filename)
                if pure.is_absolute() or ".." in pure.parts or info.filename.endswith("/"):
                    errors.append(f"unsafe_entry:{info.filename}")
                    continue
                if info.date_time != FIXED_ZIP_TIMESTAMP:
                    errors.append(f"non_deterministic_timestamp:{info.filename}")
                mode = (info.external_attr >> 16) & 0o777
                if mode != 0o644:
                    errors.append(f"non_deterministic_mode:{info.filename}:{oct(mode)}")
                if info.compress_type != zipfile.ZIP_STORED:
                    errors.append(f"non_deterministic_compression:{info.filename}")
                file_bytes[info.filename] = archive.read(info.filename)
    except (OSError, zipfile.BadZipFile) as exc:
        return {"ok": False, "action": "tool_authoring_verify_bundle", "status": "invalid_zip", "path": str(target), "errors": [str(exc)]}

    manifest_path = f"{BUNDLE_ROOT}/manifest.json"
    manifest: dict[str, Any] | None = None
    if manifest_path not in file_bytes:
        errors.append("manifest_missing")
    else:
        try:
            parsed = json.loads(file_bytes[manifest_path].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            errors.append("manifest_invalid_json")
        else:
            if isinstance(parsed, dict):
                manifest = parsed
            else:
                errors.append("manifest_must_be_object")
    if manifest is not None:
        if manifest.get("schema") != BUNDLE_SCHEMA or manifest.get("schema_version") != BUNDLE_SCHEMA_VERSION:
            errors.append("manifest_schema_mismatch")
        if manifest.get("skill") != SKILL_NAME:
            errors.append("manifest_skill_mismatch")
        if manifest.get("failure_semantics") != "fail_closed":
            errors.append("manifest_failure_semantics_mismatch")
        authority = manifest.get("authority")
        expected_authority = {
            "tool_authoring_only": True,
            "execution_authority_granted": False,
            "mutation_authority_granted": False,
            "release_authority_granted": False,
            "publication_authority_granted": False,
            "adoption_authority_granted": False,
        }
        if authority != expected_authority:
            errors.append("manifest_authority_escalation")
        rows = manifest.get("files")
        if not isinstance(rows, list):
            errors.append("manifest_files_invalid")
        else:
            indexed = {row.get("path"): row for row in rows if isinstance(row, dict) and isinstance(row.get("path"), str)}
            if set(indexed) != set(BUNDLE_PAYLOAD_ENTRIES):
                errors.append("manifest_payload_entries_mismatch")
            for name in BUNDLE_PAYLOAD_ENTRIES:
                row = indexed.get(name)
                content = file_bytes.get(name)
                if row is None or content is None:
                    continue
                if row.get("sha256") != _sha256(content):
                    errors.append(f"digest_mismatch:{name}")
                if row.get("size_bytes") != len(content):
                    errors.append(f"size_mismatch:{name}")
    example_path = f"{BUNDLE_ROOT}/examples/read-version.tool.json"
    if example_path in file_bytes:
        try:
            example = json.loads(file_bytes[example_path].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            errors.append("example_invalid_json")
        else:
            validation = validate_tool_spec(example if isinstance(example, dict) else {})
            errors.extend(f"example:{item}" for item in validation.get("errors") or [])
    else:
        validation = None

    return {
        "ok": not errors,
        "action": "tool_authoring_verify_bundle",
        "status": "bundle_verified" if not errors else "bundle_invalid",
        "path": str(target),
        "sha256": _sha256(target.read_bytes()) if target.is_file() else None,
        "size_bytes": target.stat().st_size if target.is_file() else None,
        "entry_count": len(file_bytes),
        "errors": errors,
        "manifest": manifest,
        "example_validation": validation,
        "execution_authority_granted": False if not errors else None,
        "mutation_authority_granted": False if not errors else None,
    }
