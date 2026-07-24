from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

AUTHORITY_GRAPH_REL = Path("docs/project/project-authority-graph-v0.1.109.json")
AUTHORITY_SCHEMA = "promptbranch.project.authority_graph"
AUTHORITY_SCHEMA_VERSION = "1.0"
VERSION_RE = re.compile(r"\bv\d+\.\d+\.\d+(?:\.\d+)*\b")

_REQUIRED_PROJECT_SETTINGS_TOKENS = (
    "# Project Settings",
    "## Project identity and purpose",
    "## Stable operating policy",
    "## Authority model",
    "## Mutation boundaries",
    "## Validation and adoption",
)
_REQUIRED_AGENTS_TOKENS = (
    "# AGENTS.md",
    "## Read order",
    "## Fail-closed rules",
    "## Release work",
    "## Completion claims",
)
_MUTABLE_POLICY_PATTERNS = (
    re.compile(r"accepted/current\s+(?:version|baseline)\s*:", re.IGNORECASE),
    re.compile(r"active\s+candidate\s*:", re.IGNORECASE),
    re.compile(r"latest\s+accepted/current", re.IGNORECASE),
    re.compile(r"next\s+normal\s+(?:target|slice)\s*:", re.IGNORECASE),
    re.compile(r"current\s+version\s+(?:is|:)\s*v\d", re.IGNORECASE),
)
_FORBIDDEN_AUTHORITY_KEYS = {"precedence", "priority", "fallback", "fallback_authorities", "last_write_wins"}


def _root(repo_path: str | Path) -> Path:
    return Path(repo_path).expanduser().resolve()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing required JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON file {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return value


def load_project_authority_graph(repo_path: str | Path = ".") -> dict[str, Any]:
    root = _root(repo_path)
    return _load_json(root / AUTHORITY_GRAPH_REL)


def _contains_forbidden_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _FORBIDDEN_AUTHORITY_KEYS:
                return key
            found = _contains_forbidden_key(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _contains_forbidden_key(child)
            if found:
                return found
    return None


def _projection_value_from_authority(root: Path, authority: dict[str, Any], projection: dict[str, Any]) -> Any:
    authority_path = root / str(authority.get("path") or "")
    source = str(projection.get("expected_from") or "authority_text")
    if source == "authority_text":
        value: Any = authority_path.read_text(encoding="utf-8").strip()
    elif source.startswith("authority_json:"):
        field = source.split(":", 1)[1]
        value = _load_json(authority_path)
        for part in field.split("."):
            if not isinstance(value, dict) or part not in value:
                raise ValueError(f"authority JSON field not found: {field}")
            value = value[part]
    elif source == "literal":
        value = projection.get("expected")
    else:
        raise ValueError(f"unsupported projection expected_from: {source}")
    normalizer = projection.get("normalizer")
    if normalizer == "strip_v" and isinstance(value, str):
        value = value[1:] if value.startswith("v") else value
    return value


def _validate_projection(root: Path, domain: str, authority: dict[str, Any], projection: dict[str, Any]) -> str | None:
    projection_path = root / str(projection.get("path") or "")
    if not projection_path.is_file():
        return f"{domain}: projection file missing: {projection.get('path')}"
    try:
        expected = _projection_value_from_authority(root, authority, projection)
    except (OSError, ValueError) as exc:
        return f"{domain}: cannot resolve projection expectation: {exc}"

    projection_type = projection.get("type")
    if projection_type == "toml_project_version":
        try:
            data = tomllib.loads(projection_path.read_text(encoding="utf-8"))
            actual = data["project"]["version"]
        except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
            return f"{domain}: cannot read project.version from {projection.get('path')}: {exc}"
        if actual != expected:
            return f"{domain}: projection drift in {projection.get('path')}: expected {expected!r}, got {actual!r}"
        return None

    if projection_type == "python_constant":
        constant = str(projection.get("constant") or "")
        text = projection_path.read_text(encoding="utf-8")
        match = re.search(rf"^\s*{re.escape(constant)}\s*=\s*['\"]([^'\"]+)['\"]", text, re.MULTILINE)
        if not match:
            return f"{domain}: constant {constant!r} not found in {projection.get('path')}"
        actual = match.group(1)
        if actual != expected:
            return f"{domain}: projection drift in {projection.get('path')}: expected {expected!r}, got {actual!r}"
        return None

    if projection_type == "markdown_json_tokens":
        text = projection_path.read_text(encoding="utf-8")
        fields = projection.get("fields") if isinstance(projection.get("fields"), list) else []
        data = _load_json(root / str(authority.get("path")))
        missing_tokens: list[str] = []
        for field in fields:
            value: Any = data
            for part in str(field).split("."):
                if not isinstance(value, dict) or part not in value:
                    return f"{domain}: authority JSON field not found for projection: {field}"
                value = value[part]
            token = str(value)
            if token and token not in text:
                missing_tokens.append(token)
        if missing_tokens:
            return f"{domain}: projection drift in {projection.get('path')}; missing token(s): {missing_tokens}"
        return None

    if projection_type == "literal_contains":
        text = projection_path.read_text(encoding="utf-8")
        tokens = projection.get("tokens") if isinstance(projection.get("tokens"), list) else []
        missing = [str(token) for token in tokens if str(token) not in text]
        if missing:
            return f"{domain}: projection drift in {projection.get('path')}; missing token(s): {missing}"
        return None

    return f"{domain}: unsupported projection type: {projection_type!r}"


def _validate_policy_document(path: Path, required_tokens: tuple[str, ...], *, agents: bool) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"authority file missing: {path.name}"]
    text = path.read_text(encoding="utf-8")
    for token in required_tokens:
        if token not in text:
            errors.append(f"{path.name} missing required section token: {token}")
    for pattern in _MUTABLE_POLICY_PATTERNS:
        if pattern.search(text):
            errors.append(f"{path.name} duplicates mutable release state matched by {pattern.pattern!r}")
    if agents:
        version = VERSION_RE.search(text)
        if version:
            errors.append(f"AGENTS.md must not pin a concrete mutable release version: {version.group(0)}")
    return errors


def build_project_authority_show_payload(repo_path: str | Path = ".") -> dict[str, Any]:
    root = _root(repo_path)
    try:
        graph = load_project_authority_graph(root)
    except ValueError as exc:
        return {
            "ok": False,
            "action": "project_authority_show",
            "status": "authority_missing",
            "repo_path": str(root),
            "graph_path": str(root / AUTHORITY_GRAPH_REL),
            "error": str(exc),
        }
    domains = graph.get("domains") if isinstance(graph.get("domains"), list) else []
    return {
        "ok": True,
        "action": "project_authority_show",
        "status": "authority_graph_loaded",
        "repo_path": str(root),
        "graph_path": str(root / AUTHORITY_GRAPH_REL),
        "schema": graph.get("schema"),
        "schema_version": graph.get("schema_version"),
        "graph_version": graph.get("graph_version"),
        "validation_mode": graph.get("validation_mode"),
        "remote_mutation_allowed": graph.get("remote_mutation_allowed"),
        "domain_count": len(domains),
        "domains": domains,
        "mutation_performed": False,
        "writes_attempted": 0,
    }


def validate_project_authority_graph(repo_path: str | Path = ".", *, include_runtime: bool = False) -> dict[str, Any]:
    root = _root(repo_path)
    errors: list[str] = []
    warnings: list[str] = []
    projection_errors: list[str] = []
    missing_errors: list[str] = []
    ambiguous_errors: list[str] = []
    runtime_domains: list[dict[str, Any]] = []
    external_domains: list[dict[str, Any]] = []

    try:
        graph = load_project_authority_graph(root)
    except ValueError as exc:
        return {
            "ok": False,
            "action": "project_authority_validate",
            "status": "authority_missing",
            "repo_path": str(root),
            "graph_path": str(root / AUTHORITY_GRAPH_REL),
            "errors": [str(exc)],
            "error_count": 1,
            "mutation_performed": False,
            "writes_attempted": 0,
        }

    if graph.get("schema") != AUTHORITY_SCHEMA:
        errors.append(f"authority graph schema must be {AUTHORITY_SCHEMA}")
    if graph.get("schema_version") != AUTHORITY_SCHEMA_VERSION:
        errors.append(f"authority graph schema_version must be {AUTHORITY_SCHEMA_VERSION}")
    if graph.get("validation_mode") != "read_only":
        errors.append("authority graph validation_mode must be read_only")
    if graph.get("remote_mutation_allowed") is not False:
        errors.append("authority graph remote_mutation_allowed must be false")
    if graph.get("default_conflict_policy") != "fail_closed":
        errors.append("authority graph default_conflict_policy must be fail_closed")

    domains = graph.get("domains")
    if not isinstance(domains, list) or not domains:
        errors.append("authority graph domains must be a non-empty list")
        domains = []

    names: set[str] = set()
    for index, item in enumerate(domains):
        if not isinstance(item, dict):
            ambiguous_errors.append(f"authority domain {index} must be an object")
            continue
        domain = str(item.get("domain") or "")
        if not domain:
            ambiguous_errors.append(f"authority domain {index} missing domain name")
            continue
        if domain in names:
            ambiguous_errors.append(f"duplicate authority domain: {domain}")
        names.add(domain)
        forbidden = _contains_forbidden_key(item)
        if forbidden:
            ambiguous_errors.append(f"{domain}: precedence/fallback key is forbidden: {forbidden}")
        if item.get("conflict_policy") != "fail_closed":
            ambiguous_errors.append(f"{domain}: conflict_policy must be fail_closed")
        authority = item.get("authority")
        if not isinstance(authority, dict) or not authority:
            ambiguous_errors.append(f"{domain}: exactly one authority object is required")
            continue
        kind = authority.get("kind")
        path_value = authority.get("path")
        if kind == "repository_file":
            if not path_value:
                missing_errors.append(f"{domain}: repository authority path is required")
            elif not (root / str(path_value)).is_file():
                missing_errors.append(f"{domain}: authority file missing: {path_value}")
        elif kind in {"runtime_file", "runtime_registry"}:
            resolver = authority.get("resolver")
            present = bool(path_value) and (root / str(path_value)).exists()
            runtime_domains.append({
                "domain": domain,
                "kind": kind,
                "path": path_value,
                "resolver": resolver,
                "status": "available" if present else "deferred_runtime",
                "required_for_static_validation": False,
            })
            if include_runtime and not present:
                target = path_value or resolver or "unresolved runtime authority"
                missing_errors.append(f"{domain}: runtime authority unavailable: {target}")
        elif kind == "external_observation":
            external_domains.append({
                "domain": domain,
                "kind": kind,
                "status": "not_observed_read_only",
                "remote_mutation_allowed": False,
                "required_for_static_validation": False,
            })
            if include_runtime and item.get("required_for_runtime_validation") is True:
                missing_errors.append(f"{domain}: external authority observation unresolved")
        else:
            ambiguous_errors.append(f"{domain}: unsupported authority kind: {kind!r}")

        projections = item.get("projections") if isinstance(item.get("projections"), list) else []
        for projection in projections:
            if not isinstance(projection, dict):
                projection_errors.append(f"{domain}: projection must be an object")
                continue
            error = _validate_projection(root, domain, authority, projection)
            if error:
                projection_errors.append(error)

    policy_errors = _validate_policy_document(root / "PROJECT_SETTINGS.md", _REQUIRED_PROJECT_SETTINGS_TOKENS, agents=False)
    agent_errors = _validate_policy_document(root / "AGENTS.md", _REQUIRED_AGENTS_TOKENS, agents=True)
    missing_errors.extend(error for error in policy_errors + agent_errors if "missing" in error.lower())
    projection_errors.extend(error for error in policy_errors + agent_errors if "missing" not in error.lower())

    errors.extend(ambiguous_errors)
    errors.extend(missing_errors)
    errors.extend(projection_errors)
    if external_domains:
        warnings.append("External ChatGPT Project Settings are declared as read-only observations and are not fetched during deterministic repository validation.")

    if ambiguous_errors:
        status = "authority_ambiguous"
    elif missing_errors:
        status = "authority_missing"
    elif projection_errors:
        status = "projection_drift"
    else:
        status = "authority_consistent"

    return {
        "ok": not errors,
        "action": "project_authority_validate",
        "status": status,
        "repo_path": str(root),
        "graph_path": str(root / AUTHORITY_GRAPH_REL),
        "schema": graph.get("schema"),
        "schema_version": graph.get("schema_version"),
        "graph_version": graph.get("graph_version"),
        "validation_mode": graph.get("validation_mode"),
        "include_runtime": include_runtime,
        "domain_count": len(domains),
        "domain_names": sorted(names),
        "runtime_domains": runtime_domains,
        "external_domains": external_domains,
        "error_count": len(errors),
        "errors": errors,
        "warnings": warnings,
        "mutation_performed": False,
        "writes_attempted": 0,
        "remote_mutation_allowed": False,
    }
