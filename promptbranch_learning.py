from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

LEARNING_SKILL = "promptbranch-learning"
OPERATOR_SKILL = "promptbranch-operator"
LEARNING_SCHEMA = "promptbranch.learning.bundle"
OPERATOR_SCHEMA = "promptbranch.operator.bundle"
BUNDLE_SCHEMA_VERSION = "1.0"
FIXED_ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)

LEARNING_SKILL_REL = Path(".promptbranch/skills/promptbranch-learning/SKILL.md")
OPERATOR_SKILL_REL = Path(".promptbranch/skills/promptbranch-operator/SKILL.md")
LEARNING_MATERIAL_DIR = Path(".promptbranch/skills/promptbranch-learning/materials")
OPERATOR_MATERIAL_DIR = Path(".promptbranch/skills/promptbranch-operator/materials")
REGISTRY_REL = Path(".promptbranch/ai-registry.json")
RELATED_SKILL_RELS = (
    Path(".promptbranch/skills/repo-inspection/SKILL.md"),
    Path(".promptbranch/skills/promptbranch-final-mvp/SKILL.md"),
    Path(".promptbranch/skills/application-architecture-proof/SKILL.md"),
    Path(".promptbranch/skills/promptbranch-tool-authoring/SKILL.md"),
    OPERATOR_SKILL_REL,
)

LEARNING_MATERIALS = (
    "PROMPTBRANCH_OVERVIEW.md",
    "AUTHORITY_MODEL.md",
    "LEARNING_PATH.md",
    "QUICKSTART.md",
    "OPERATOR_GUIDE.md",
    "DEVELOPER_GUIDE.md",
    "EXERCISES.md",
    "GLOSSARY.md",
)
OPERATOR_MATERIALS = (
    "OPERATOR_RUNBOOK.md",
    "SAFE_INSPECTION.md",
    "FAILURE_CLASSIFICATION.md",
)

NO_AUTHORITY = {
    "execution_authority_granted": False,
    "mutation_authority_granted": False,
    "release_authority_granted": False,
    "publication_authority_granted": False,
    "acceptance_authority_granted": False,
    "adoption_authority_granted": False,
    "deployment_authority_granted": False,
}

AUDIENCE_MATRIX = {
    "human": {"entrypoint": "LEARNING_PATH.md", "adapter": "markdown"},
    "chatgpt_project": {"entrypoint": "PROJECT_SOURCE.md", "adapter": "project_source"},
    "claude_coding_agent": {"entrypoint": "CLAUDE.md", "adapter": "coding_agent"},
    "generic_coding_agent": {"entrypoint": "AGENTS.md", "adapter": "coding_agent"},
    "promptbranch_aware_agent": {"entrypoint": "SKILL.md", "adapter": "skill_manifest"},
}

COVERAGE_DOMAINS = (
    "mental_model",
    "authority_model",
    "read_only_quickstart",
    "operator_model",
    "developer_model",
    "skills_and_tools",
    "artifact_authority",
    "browser_conversation_causality",
    "release_lifecycle",
    "external_application_boundary",
    "exercises",
    "glossary",
)


class LearningBundleError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(data: Any) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _repo(repo_path: str | Path) -> Path:
    return Path(repo_path).expanduser().resolve()


def _version(repo: Path) -> str:
    try:
        value = (repo / "VERSION").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise LearningBundleError(f"version_unavailable:{exc}") from exc
    if not value.startswith("v"):
        raise LearningBundleError("version_must_be_v_prefixed")
    return value


def _read(repo: Path, rel: Path) -> bytes:
    target = (repo / rel).resolve()
    try:
        target.relative_to(repo)
    except ValueError as exc:
        raise LearningBundleError(f"source_outside_repo:{rel.as_posix()}") from exc
    try:
        return target.read_bytes()
    except OSError as exc:
        raise LearningBundleError(f"source_unavailable:{rel.as_posix()}:{exc}") from exc


def _skill_registry_entry(registry: dict[str, Any], name: str) -> dict[str, Any] | None:
    rows = registry.get("skills")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("name") == name:
            return row
    return None


def _validate_skill_source(
    repo: Path,
    *,
    name: str,
    skill_rel: Path,
    material_dir: Path,
    material_names: tuple[str, ...],
    required_phrases: tuple[str, ...],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        skill_text = _read(repo, skill_rel).decode("utf-8")
        registry = json.loads(_read(repo, REGISTRY_REL).decode("utf-8"))
        materials = {name_: _read(repo, material_dir / name_).decode("utf-8") for name_ in material_names}
    except (LearningBundleError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "action": "learning_validate_source",
            "status": "invalid",
            "skill": name,
            "repo_path": str(repo),
            "errors": [str(exc)],
        }

    if f"name: {name}" not in skill_text:
        errors.append("skill_name_missing")
    if "risk: read" not in skill_text:
        errors.append("skill_not_read_only")
    for phrase in required_phrases:
        if phrase not in skill_text:
            errors.append(f"skill_required_phrase_missing:{phrase}")
    for material_name, text in materials.items():
        if not text.strip().startswith("#"):
            errors.append(f"material_not_markdown:{material_name}")
        if len(text.strip()) < 80:
            errors.append(f"material_too_small:{material_name}")

    entry = _skill_registry_entry(registry if isinstance(registry, dict) else {}, name)
    if entry is None:
        errors.append("registry_skill_missing")
    else:
        expected_path = skill_rel.as_posix()
        if entry.get("path") != expected_path:
            errors.append("registry_skill_path_mismatch")
        tools = entry.get("tools")
        if not isinstance(tools, list) or not tools:
            errors.append("registry_tools_missing")
        elif any(tool not in {"filesystem.read", "filesystem.list", "git.status", "git.diff.summary", "artifact.registry.current"} for tool in tools):
            errors.append("registry_skill_not_read_only")

    return {
        "ok": not errors,
        "action": "learning_validate_source",
        "status": "valid" if not errors else "invalid",
        "skill": name,
        "repo_path": str(repo),
        "version": _version(repo) if not errors else None,
        "materials": list(material_names),
        "errors": errors,
        "authority": dict(NO_AUTHORITY),
    }


def validate_learning_source(repo_path: str | Path = ".") -> dict[str, Any]:
    repo = _repo(repo_path)
    payload = _validate_skill_source(
        repo,
        name=LEARNING_SKILL,
        skill_rel=LEARNING_SKILL_REL,
        material_dir=LEARNING_MATERIAL_DIR,
        material_names=LEARNING_MATERIALS,
        required_phrases=(
            "human, ChatGPT, Claude/coding agent, or another PB-aware agent",
            "Canonical learning order",
            "Completion criterion",
            "grants no repository mutation",
        ),
    )
    if payload.get("ok"):
        try:
            combined = "\n".join(
                _read(repo, LEARNING_MATERIAL_DIR / name).decode("utf-8") for name in LEARNING_MATERIALS
            )
        except (LearningBundleError, UnicodeDecodeError) as exc:
            payload["ok"] = False
            payload["status"] = "invalid"
            payload["errors"] = [str(exc)]
            return payload
        domain_phrases = {
            "mental_model": "Canonical mental model",
            "authority_model": "Authority layers",
            "read_only_quickstart": "read-first",
            "operator_model": "Promptbranch operator guide",
            "developer_model": "Promptbranch developer guide",
            "skills_and_tools": "Skills",
            "artifact_authority": "Artifact authority",
            "browser_conversation_causality": "Browser and conversation authority",
            "release_lifecycle": "Release discipline",
            "external_application_boundary": "External application boundary",
            "exercises": "Promptbranch learning exercises",
            "glossary": "Promptbranch glossary",
        }
        missing = [domain for domain, phrase in domain_phrases.items() if phrase not in combined]
        if missing:
            payload["ok"] = False
            payload["status"] = "invalid"
            payload["errors"] = [f"coverage_missing:{item}" for item in missing]
        payload["coverage_domains"] = list(COVERAGE_DOMAINS)
        payload["audiences"] = sorted(AUDIENCE_MATRIX)
    return payload


def validate_operator_source(repo_path: str | Path = ".") -> dict[str, Any]:
    return _validate_skill_source(
        _repo(repo_path),
        name=OPERATOR_SKILL,
        skill_rel=OPERATOR_SKILL_REL,
        material_dir=OPERATOR_MATERIAL_DIR,
        material_names=OPERATOR_MATERIALS,
        required_phrases=(
            "after the `promptbranch-learning` curriculum",
            "Classify the requested operation",
            "independently verify",
            "requires the separate deterministic PB control-plane path",
        ),
    )


def _project_source(version: str, skill: str, docs: dict[str, bytes]) -> bytes:
    sections = [
        "# Promptbranch Learning — portable Project Source",
        "",
        f"Release: `{version}`",
        "",
        "This is the canonical self-contained learning source for Promptbranch. It teaches the same mental model and authority boundaries used by humans and coding agents. It grants no execution or mutation authority.",
        "",
        "## Skill",
        "",
        skill.rstrip(),
    ]
    for name in LEARNING_MATERIALS:
        sections.extend(["", f"## {name}", "", docs[name].decode("utf-8").rstrip()])
    sections.extend([
        "",
        "## Authority reminder",
        "",
        "Use this Project Source for learning and reasoning only. Any PB mutation, publication, acceptance, adoption or deployment still requires the canonical deterministic control-plane path and its evidence.",
        "",
    ])
    return "\n".join(sections).encode("utf-8")


def _learning_agents(version: str) -> bytes:
    return f"""# Agent bootstrap: learn Promptbranch\n\nBundle release: `{version}`\n\n1. Read `SKILL.md`, then `AUTHORITY_MODEL.md`, then `LEARNING_PATH.md`.\n2. This bundle does not grant execution or mutation authority. Do not infer such authority from learning material.\n3. Use `QUICKSTART.md` read-only inspection before any operational proposal.\n4. Read `OPERATOR_GUIDE.md` before proposing stateful PB actions.\n5. Read `DEVELOPER_GUIDE.md` and embedded related skills before extending PB.\n6. Complete the evidence-oriented exercises in `EXERCISES.md`.\n7. Treat the current canonical PB mechanism as authoritative; do not resurrect superseded PB internals as compatibility paths.\n8. When state, identity, causality or authority is ambiguous, fail closed.\n\nThis file adapts the same canonical learning contract for coding agents; it does not define a separate PB behavior.\n""".encode("utf-8")


def _learning_claude(version: str) -> bytes:
    return f"""# Claude bootstrap for Promptbranch\n\nRelease: `{version}`\n\nRead `AGENTS.md` and follow the same canonical curriculum. Preserve PB's separation between reasoning and deterministic authority. A successful analysis, skill validation or tool proposal is not permission to mutate, publish, accept, adopt or deploy. Use the embedded `promptbranch-tool-authoring` skill when designing tools and the `promptbranch-operator` skill when reasoning about operator procedure.\n""".encode("utf-8")


def _operator_project_source(version: str, skill: str, docs: dict[str, bytes]) -> bytes:
    sections = [
        "# Promptbranch Operator — portable Project Source",
        "",
        f"Release: `{version}`",
        "",
        "This source teaches safe Promptbranch operation. It is read-only guidance and grants no mutation authority.",
        "",
        skill.rstrip(),
    ]
    for name in OPERATOR_MATERIALS:
        sections.extend(["", f"## {name}", "", docs[name].decode("utf-8").rstrip()])
    sections.append("")
    return "\n".join(sections).encode("utf-8")


def _operator_agents(version: str) -> bytes:
    return f"""# Coding-agent instructions: Promptbranch operator\n\nBundle release: `{version}`\n\nRead `SKILL.md` and the runbook before proposing PB operations. Start read-only, classify risk, resolve exact identities, state required authority/evidence, and fail closed on ambiguity. This bundle does not authorize browser/repository/Project Source mutation, publication, release transitions, acceptance, adoption, deployment, Git commit or Git push.\n""".encode("utf-8")


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


def _manifest(*, schema: str, skill: str, version: str, root: str, payload: dict[str, bytes], purpose: str, audiences: dict[str, Any] | None = None, coverage: list[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": schema,
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "skill": skill,
        "source_version": version,
        "bundle_root": root,
        "purpose": purpose,
        "determinism": {
            "entry_order": "lexicographic",
            "zip_compression": "stored",
            "zip_timestamp": "2020-01-01T00:00:00Z",
            "file_mode": "0644",
        },
        "files": [
            {"path": path, "sha256": _sha256(payload[path]), "size_bytes": len(payload[path])}
            for path in sorted(payload)
        ],
        "authority": dict(NO_AUTHORITY),
        "failure_semantics": "fail_closed",
    }
    if audiences is not None:
        out["audiences"] = audiences
    if coverage is not None:
        out["coverage_domains"] = coverage
    return out


def _build_learning(repo: Path) -> dict[str, Any]:
    validation = validate_learning_source(repo)
    operator_validation = validate_operator_source(repo)
    if not validation.get("ok") or not operator_validation.get("ok"):
        errors = list(validation.get("errors") or []) + [f"operator:{e}" for e in operator_validation.get("errors") or []]
        raise LearningBundleError("learning_source_invalid:" + ";".join(errors))
    version = _version(repo)
    skill_bytes = _read(repo, LEARNING_SKILL_REL)
    docs = {name: _read(repo, LEARNING_MATERIAL_DIR / name) for name in LEARNING_MATERIALS}
    root = LEARNING_SKILL
    payload: dict[str, bytes] = {f"{root}/SKILL.md": skill_bytes}
    payload.update({f"{root}/{name}": value for name, value in docs.items()})
    payload[f"{root}/PROJECT_SOURCE.md"] = _project_source(version, skill_bytes.decode("utf-8"), docs)
    payload[f"{root}/AGENTS.md"] = _learning_agents(version)
    payload[f"{root}/CLAUDE.md"] = _learning_claude(version)
    for rel in RELATED_SKILL_RELS:
        name = rel.parent.name
        payload[f"{root}/related-skills/{name}/SKILL.md"] = _read(repo, rel)
    manifest = _manifest(
        schema=LEARNING_SCHEMA,
        skill=LEARNING_SKILL,
        version=version,
        root=root,
        payload=payload,
        purpose="bootstrap a human, ChatGPT Project, Claude/coding agent, or PB-aware agent into the canonical Promptbranch mental, authority, operator and developer models",
        audiences=AUDIENCE_MATRIX,
        coverage=list(COVERAGE_DOMAINS),
    )
    files = dict(payload)
    files[f"{root}/manifest.json"] = _canonical_json(manifest)
    return {"version": version, "root": root, "files": files, "manifest": manifest, "validation": validation}


def _build_operator(repo: Path) -> dict[str, Any]:
    validation = validate_operator_source(repo)
    if not validation.get("ok"):
        raise LearningBundleError("operator_source_invalid:" + ";".join(validation.get("errors") or []))
    version = _version(repo)
    skill_bytes = _read(repo, OPERATOR_SKILL_REL)
    docs = {name: _read(repo, OPERATOR_MATERIAL_DIR / name) for name in OPERATOR_MATERIALS}
    root = OPERATOR_SKILL
    payload: dict[str, bytes] = {f"{root}/SKILL.md": skill_bytes}
    payload.update({f"{root}/{name}": value for name, value in docs.items()})
    payload[f"{root}/PROJECT_SOURCE.md"] = _operator_project_source(version, skill_bytes.decode("utf-8"), docs)
    payload[f"{root}/AGENTS.md"] = _operator_agents(version)
    payload[f"{root}/CLAUDE.md"] = _operator_agents(version)
    manifest = _manifest(
        schema=OPERATOR_SCHEMA,
        skill=OPERATOR_SKILL,
        version=version,
        root=root,
        payload=payload,
        purpose="portable read-only Promptbranch operator learning/runbook bundle",
    )
    files = dict(payload)
    files[f"{root}/manifest.json"] = _canonical_json(manifest)
    return {"version": version, "root": root, "files": files, "manifest": manifest, "validation": validation}


_BUILDERS: dict[str, Callable[[Path], dict[str, Any]]] = {
    LEARNING_SKILL: _build_learning,
    OPERATOR_SKILL: _build_operator,
}


def export_learning_bundle(skill: str, repo_path: str | Path = ".", output: str | Path | None = None, *, force: bool = False) -> dict[str, Any]:
    if skill not in _BUILDERS:
        raise LearningBundleError(f"unsupported_learning_bundle:{skill}")
    repo = _repo(repo_path)
    built = _BUILDERS[skill](repo)
    version = built["version"]
    target = Path(output).expanduser().resolve() if output is not None else (Path.cwd() / f"{skill}_{version}.zip").resolve()
    if target.exists() and not force:
        raise LearningBundleError(f"output_exists:{target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    files: dict[str, bytes] = built["files"]
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED, strict_timestamps=True) as archive:
        archive.comment = b""
        for path in sorted(files):
            archive.writestr(_zip_info(path), files[path], compress_type=zipfile.ZIP_STORED)
    verification = verify_learning_bundle(target)
    if not verification.get("ok"):
        target.unlink(missing_ok=True)
        raise LearningBundleError("export_verification_failed:" + ";".join(verification.get("errors") or []))
    return {
        "ok": True,
        "action": "skill_export_bundle",
        "status": "bundle_exported",
        "skill": skill,
        "source_version": version,
        "output": str(target),
        "sha256": _sha256(target.read_bytes()),
        "size_bytes": target.stat().st_size,
        "entry_count": len(files),
        "entries": sorted(files),
        "verification": verification,
        "authority": dict(NO_AUTHORITY),
    }


def verify_learning_bundle(path: str | Path) -> dict[str, Any]:
    target = Path(path).expanduser().resolve()
    errors: list[str] = []
    files: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(target, "r") as archive:
            names = archive.namelist()
            if names != sorted(names) or len(names) != len(set(names)):
                errors.append("bundle_entry_order_or_duplicate_mismatch")
            for info in archive.infolist():
                pure = PurePosixPath(info.filename)
                if pure.is_absolute() or ".." in pure.parts or info.filename.endswith("/"):
                    errors.append(f"unsafe_entry:{info.filename}")
                    continue
                if info.date_time != FIXED_ZIP_TIMESTAMP:
                    errors.append(f"non_deterministic_timestamp:{info.filename}")
                if ((info.external_attr >> 16) & 0o777) != 0o644:
                    errors.append(f"non_deterministic_mode:{info.filename}")
                if info.compress_type != zipfile.ZIP_STORED:
                    errors.append(f"non_deterministic_compression:{info.filename}")
                files[info.filename] = archive.read(info.filename)
    except (OSError, zipfile.BadZipFile) as exc:
        return {"ok": False, "action": "skill_verify_bundle", "status": "invalid_zip", "path": str(target), "errors": [str(exc)]}

    roots = {PurePosixPath(name).parts[0] for name in files if PurePosixPath(name).parts}
    if len(roots) != 1:
        errors.append("bundle_root_mismatch")
        root = None
    else:
        root = next(iter(roots))
    manifest = None
    if root:
        manifest_path = f"{root}/manifest.json"
        raw = files.get(manifest_path)
        if raw is None:
            errors.append("manifest_missing")
        else:
            try:
                parsed = json.loads(raw.decode("utf-8"))
                manifest = parsed if isinstance(parsed, dict) else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                manifest = None
            if manifest is None:
                errors.append("manifest_invalid_json")
    if manifest is not None:
        schema = manifest.get("schema")
        if schema not in {LEARNING_SCHEMA, OPERATOR_SCHEMA} or manifest.get("schema_version") != BUNDLE_SCHEMA_VERSION:
            errors.append("manifest_schema_mismatch")
        skill = manifest.get("skill")
        if skill != root or skill not in {LEARNING_SKILL, OPERATOR_SKILL}:
            errors.append("manifest_skill_mismatch")
        if manifest.get("authority") != NO_AUTHORITY:
            errors.append("manifest_authority_escalation")
        if manifest.get("failure_semantics") != "fail_closed":
            errors.append("manifest_failure_semantics_mismatch")
        rows = manifest.get("files")
        if not isinstance(rows, list):
            errors.append("manifest_files_invalid")
        else:
            indexed = {row.get("path"): row for row in rows if isinstance(row, dict) and isinstance(row.get("path"), str)}
            expected_payload = set(files) - {f"{root}/manifest.json"}
            if set(indexed) != expected_payload:
                errors.append("manifest_payload_entries_mismatch")
            for name in sorted(expected_payload):
                row = indexed.get(name)
                if row is None:
                    continue
                content = files[name]
                if row.get("sha256") != _sha256(content):
                    errors.append(f"digest_mismatch:{name}")
                if row.get("size_bytes") != len(content):
                    errors.append(f"size_mismatch:{name}")
        if schema == LEARNING_SCHEMA:
            if manifest.get("audiences") != AUDIENCE_MATRIX:
                errors.append("audience_matrix_mismatch")
            if manifest.get("coverage_domains") != list(COVERAGE_DOMAINS):
                errors.append("coverage_domains_mismatch")
            required = {
                f"{root}/SKILL.md", f"{root}/PROJECT_SOURCE.md", f"{root}/AGENTS.md", f"{root}/CLAUDE.md",
                *(f"{root}/{name}" for name in LEARNING_MATERIALS),
                *(f"{root}/related-skills/{rel.parent.name}/SKILL.md" for rel in RELATED_SKILL_RELS),
            }
            missing = sorted(required - set(files))
            if missing:
                errors.append("learning_bundle_missing:" + ",".join(missing))
        elif schema == OPERATOR_SCHEMA:
            required = {
                f"{root}/SKILL.md", f"{root}/PROJECT_SOURCE.md", f"{root}/AGENTS.md", f"{root}/CLAUDE.md",
                *(f"{root}/{name}" for name in OPERATOR_MATERIALS),
            }
            missing = sorted(required - set(files))
            if missing:
                errors.append("operator_bundle_missing:" + ",".join(missing))

    return {
        "ok": not errors,
        "action": "skill_verify_bundle",
        "status": "bundle_verified" if not errors else "bundle_invalid",
        "path": str(target),
        "sha256": _sha256(target.read_bytes()) if target.is_file() else None,
        "size_bytes": target.stat().st_size if target.is_file() else None,
        "entry_count": len(files),
        "skill": manifest.get("skill") if isinstance(manifest, dict) else None,
        "manifest": manifest,
        "errors": errors,
        **({key: False for key in NO_AUTHORITY} if not errors else {}),
    }
