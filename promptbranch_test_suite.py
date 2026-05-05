from __future__ import annotations

import argparse
import ast
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Optional, Sequence

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None  # type: ignore[assignment]

from promptbranch_full_integration_test import make_parser as make_integration_parser, run_integration
from promptbranch_mcp import (
    agent_run,
    agent_summarize_log,
    agent_tool_call,
    mcp_host_smoke,
    mcp_tool_call_via_stdio,
    skill_list,
    skill_show,
    skill_validate,
)
from promptbranch_version import PACKAGE_VERSION, normalize_version, version_tag


DEFAULT_ONLY: tuple[str, ...] = ()
DEFAULT_SKIP: tuple[str, ...] = ()
TEST_SUITE_PROFILES = ("browser", "agent", "full")


def build_test_suite_namespace(
    *,
    project_url: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    password_file: Optional[str] = None,
    profile_dir: Optional[str] = None,
    headless: Optional[bool] = None,
    use_playwright: Optional[bool] = None,
    browser_channel: Optional[str] = None,
    enable_fedcm: Optional[bool] = None,
    keep_no_sandbox: Optional[bool] = None,
    max_retries: Optional[int] = None,
    retry_backoff_seconds: Optional[float] = None,
    debug: Optional[bool] = None,
    keep_open: Optional[bool] = None,
    keep_project: bool = False,
    step_delay_seconds: Optional[float] = None,
    post_ask_delay_seconds: Optional[float] = None,
    task_list_visible_timeout_seconds: Optional[float] = None,
    task_list_visible_poll_min_seconds: Optional[float] = None,
    task_list_visible_poll_max_seconds: Optional[float] = None,
    task_list_visible_max_attempts: Optional[int] = None,
    allow_recent_state_task_fallback: bool = False,
    skip: Sequence[str] = DEFAULT_SKIP,
    only: Sequence[str] = DEFAULT_ONLY,
    strict_remove_ui: bool = False,
    project_name: Optional[str] = None,
    project_name_prefix: Optional[str] = None,
    run_id: Optional[str] = None,
    memory_mode: Optional[str] = None,
    link_url: Optional[str] = None,
    ask_prompt: Optional[str] = None,
    json_out: Optional[str] = None,
    project_list_debug_scroll_rounds: Optional[int] = None,
    project_list_debug_wait_ms: Optional[int] = None,
    project_list_debug_manual_pause: bool = False,
    service_base_url: Optional[str] = None,
    service_token: Optional[str] = None,
    service_timeout_seconds: Optional[float] = None,
    clear_singleton_locks: Optional[bool] = None,
    profile: str = "browser",
    path: str = ".",
    package_zip: Optional[str] = None,
    rate_limit_safe: Optional[bool] = None,
) -> argparse.Namespace:
    parser = make_integration_parser()
    args = parser.parse_args([])
    overrides = {
        'project_url': project_url,
        'email': email,
        'password': password,
        'password_file': password_file,
        'profile_dir': profile_dir,
        'headless': headless,
        'use_playwright': use_playwright,
        'browser_channel': browser_channel,
        'enable_fedcm': enable_fedcm,
        'keep_no_sandbox': keep_no_sandbox,
        'max_retries': max_retries,
        'retry_backoff_seconds': retry_backoff_seconds,
        'debug': debug,
        'keep_open': keep_open,
        'keep_project': keep_project,
        'step_delay_seconds': step_delay_seconds,
        'post_ask_delay_seconds': post_ask_delay_seconds,
        'task_list_visible_timeout_seconds': task_list_visible_timeout_seconds,
        'task_list_visible_poll_min_seconds': task_list_visible_poll_min_seconds,
        'task_list_visible_poll_max_seconds': task_list_visible_poll_max_seconds,
        'task_list_visible_max_attempts': task_list_visible_max_attempts,
        'allow_recent_state_task_fallback': allow_recent_state_task_fallback,
        'skip': list(skip),
        'only': list(only),
        'strict_remove_ui': strict_remove_ui,
        'project_name': project_name,
        'project_name_prefix': project_name_prefix,
        'run_id': run_id,
        'memory_mode': memory_mode,
        'link_url': link_url,
        'ask_prompt': ask_prompt,
        'json_out': json_out,
        'project_list_debug_scroll_rounds': project_list_debug_scroll_rounds,
        'project_list_debug_wait_ms': project_list_debug_wait_ms,
        'project_list_debug_manual_pause': project_list_debug_manual_pause,
        'service_base_url': service_base_url,
        'service_token': service_token,
        'service_timeout_seconds': service_timeout_seconds,
        'clear_singleton_locks': clear_singleton_locks,
        'rate_limit_safe': rate_limit_safe,
    }
    for key, value in overrides.items():
        if value is not None:
            setattr(args, key, value)
    return args


def _read_version(repo_path: Path) -> str | None:
    try:
        return (repo_path / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _read_pyproject_version_from_text(text: str) -> str | None:
    data = _load_pyproject_from_text(text)
    if not isinstance(data, dict):
        return None
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    return str(project.get("version") or "").strip() or None


def _read_pyproject_version(repo_path: Path) -> str | None:
    try:
        return _read_pyproject_version_from_text((repo_path / "pyproject.toml").read_text(encoding="utf-8"))
    except OSError:
        return None


def _extract_package_version_constant(source: str) -> str | None:
    match = re.search(r'^PACKAGE_VERSION\s*=\s*["\']([^"\']+)["\']', source, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _version_observation(label: str, value: object) -> dict[str, Any]:
    return {"name": label, "value": value, "normalized": normalize_version(value)}


def _summarize_version_consistency(observations: list[dict[str, Any]], *, expected_version: object | None) -> dict[str, Any]:
    expected = normalize_version(expected_version)
    mismatches: list[dict[str, Any]] = []
    missing: list[str] = []
    for item in observations:
        observed = item.get("normalized")
        if not observed:
            missing.append(str(item.get("name")))
            continue
        if expected and observed != expected:
            mismatches.append(item)
    ok = bool(expected) and not missing and not mismatches
    return {
        "ok": ok,
        "expected_version": expected,
        "expected_version_tag": version_tag(expected) if expected else None,
        "observations": observations,
        "missing": missing,
        "mismatches": mismatches,
    }


def _step(name: str, payload: dict[str, Any], *, expected_failure: bool = False, expected_status: str | None = None) -> dict[str, Any]:
    ok = bool(payload.get("ok"))
    status = payload.get("status")
    passed = ok if not expected_failure else (not ok and (expected_status is None or status == expected_status))
    return {
        "name": name,
        "ok": passed,
        "expected_failure": expected_failure,
        "expected_status": expected_status,
        "status": status,
        "payload": payload,
    }


def _empty_rate_limit_telemetry() -> dict[str, Any]:
    return {
        "rate_limit_modal_detected": False,
        "conversation_history_429_seen": False,
        "cooldown_wait_seconds_total": 0.0,
        "cooldown_wait_count": 0,
        "planned_cooldown_wait_seconds_total": 0.0,
        "planned_cooldown_wait_count": 0,
        "service_rate_limit_events": [],
    }


def _merge_rate_limit_telemetry(target: dict[str, Any], telemetry: Any) -> None:
    if not isinstance(telemetry, dict):
        return
    target["rate_limit_modal_detected"] = bool(target.get("rate_limit_modal_detected")) or bool(telemetry.get("rate_limit_modal_detected"))
    target["conversation_history_429_seen"] = bool(target.get("conversation_history_429_seen")) or bool(telemetry.get("conversation_history_429_seen"))
    try:
        target["cooldown_wait_seconds_total"] = round(float(target.get("cooldown_wait_seconds_total") or 0.0) + float(telemetry.get("cooldown_wait_seconds_total") or 0.0), 3)
    except (TypeError, ValueError):
        pass
    try:
        target["cooldown_wait_count"] = int(target.get("cooldown_wait_count") or 0) + int(telemetry.get("cooldown_wait_count") or 0)
    except (TypeError, ValueError):
        pass
    events = telemetry.get("service_rate_limit_events")
    if isinstance(events, list):
        target.setdefault("service_rate_limit_events", []).extend(event for event in events if isinstance(event, dict))


def extract_rate_limit_telemetry(summary: dict[str, Any]) -> dict[str, Any]:
    """Aggregate rate-limit telemetry from a browser/full test-suite summary.

    Service-backed and direct browser operations attach per-operation
    ``rate_limit_telemetry`` payloads. The integration harness also records
    planned ``rate_limit_cooldown`` steps after ask operations; those are
    kept separate from actual ChatGPT 429/modal cooldown waits so operators
    can distinguish pacing from throttling.
    """
    aggregate = _empty_rate_limit_telemetry()

    def visit_step(step: Any) -> None:
        if not isinstance(step, dict):
            return
        details = step.get("details")
        if isinstance(details, dict):
            _merge_rate_limit_telemetry(aggregate, details.get("rate_limit_telemetry"))
            if step.get("name") == "rate_limit_cooldown":
                try:
                    delay = float(details.get("delay_seconds") or 0.0)
                except (TypeError, ValueError):
                    delay = 0.0
                aggregate["planned_cooldown_wait_seconds_total"] = round(float(aggregate.get("planned_cooldown_wait_seconds_total") or 0.0) + max(0.0, delay), 3)
                aggregate["planned_cooldown_wait_count"] = int(aggregate.get("planned_cooldown_wait_count") or 0) + 1

    for key in ("steps", "cleanup_steps"):
        for step in summary.get(key) or []:
            visit_step(step)

    aggregate["service_rate_limit_events"] = list(aggregate.get("service_rate_limit_events") or [])
    aggregate["event_count"] = len(aggregate["service_rate_limit_events"])
    return aggregate



def _find_release_zip(package_zip: str | None, *, repo_path: Path | str) -> tuple[Path | None, list[Path]]:
    repo_path = Path(repo_path).expanduser().resolve()
    version = _read_version(repo_path)
    candidates: list[Path] = []
    if package_zip:
        candidates.append((repo_path / package_zip).expanduser() if not Path(package_zip).is_absolute() else Path(package_zip).expanduser())
    if version:
        candidates.append(repo_path / f"chatgpt_claudecode_workflow_{version}.zip")
    candidates.extend(sorted(repo_path.glob("chatgpt_claudecode_workflow_v*.zip"), reverse=True))
    zip_path = next((candidate.resolve() for candidate in candidates if candidate.exists()), None)
    return zip_path, candidates


def _load_pyproject_from_text(text: str) -> dict[str, Any]:
    if tomllib is None:
        return {}
    try:
        return tomllib.loads(text)
    except Exception:
        return {}


def _declared_py_modules_from_pyproject_text(text: str) -> list[str]:
    data = _load_pyproject_from_text(text)
    modules = (((data.get("tool") or {}).get("setuptools") or {}).get("py-modules") or []) if isinstance(data, dict) else []
    return sorted({str(item).strip() for item in modules if str(item).strip()})


def _declared_py_modules(repo_path: Path) -> list[str]:
    try:
        return _declared_py_modules_from_pyproject_text((repo_path / "pyproject.toml").read_text(encoding="utf-8"))
    except OSError:
        return []


def _promptbranch_imports_from_source(source: str) -> set[str]:
    modules: set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return modules
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = str(alias.name or "").split(".", 1)[0]
                if root.startswith("promptbranch_"):
                    modules.add(root)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            root = str(node.module).split(".", 1)[0]
            if root.startswith("promptbranch_"):
                modules.add(root)
    return modules


def source_version_consistency(*, repo_path: str | Path = ".") -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    expected = _read_version(root)
    observations = [
        _version_observation("VERSION", expected),
        _version_observation("pyproject.project.version", _read_pyproject_version(root)),
        _version_observation("promptbranch_version.PACKAGE_VERSION", PACKAGE_VERSION),
    ]
    consistency = _summarize_version_consistency(observations, expected_version=expected)
    return {
        "ok": bool(consistency.get("ok")),
        "action": "version_consistency",
        "status": "verified" if consistency.get("ok") else "failed",
        "repo_path": str(root),
        **consistency,
    }


def _package_import_metadata(package_zip: str | None, *, repo_path: Path | str) -> dict[str, Any]:
    zip_path, candidates = _find_release_zip(package_zip, repo_path=repo_path)
    if zip_path is None:
        return {
            "ok": True,
            "action": "package_import_metadata",
            "status": "expected_missing",
            "diagnostic": "No release ZIP found under repo_path; import metadata check skipped.",
            "candidates": [str(candidate) for candidate in candidates],
        }
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = set(archive.namelist())
            try:
                pyproject_text = archive.read("pyproject.toml").decode("utf-8")
            except KeyError:
                return {"ok": False, "action": "package_import_metadata", "status": "missing_pyproject", "zip_path": str(zip_path)}
            declared = _declared_py_modules_from_pyproject_text(pyproject_text)
            pyproject_version = _read_pyproject_version_from_text(pyproject_text)
            try:
                version_file = archive.read("VERSION").decode("utf-8").strip()
            except KeyError:
                version_file = None
            try:
                version_module = _extract_package_version_constant(archive.read("promptbranch_version.py").decode("utf-8"))
            except KeyError:
                version_module = None
            version_consistency = _summarize_version_consistency(
                [
                    _version_observation("zip.VERSION", version_file),
                    _version_observation("zip.pyproject.project.version", pyproject_version),
                    _version_observation("zip.promptbranch_version.PACKAGE_VERSION", version_module),
                ],
                expected_version=version_file,
            )
            missing_declared_files = [f"{module}.py" for module in declared if f"{module}.py" not in names]
            package_roots = {name.split("/", 1)[0] for name in names if name.endswith("/__init__.py") and name.split("/", 1)[0].startswith("promptbranch_")}
            imported: set[str] = set()
            for name in names:
                parts = [part for part in name.split("/") if part]
                if len(parts) != 1 or not name.endswith(".py") or not parts[0].startswith("promptbranch_"):
                    continue
                try:
                    imported.update(_promptbranch_imports_from_source(archive.read(name).decode("utf-8")))
                except Exception:
                    continue
            missing_import_declarations = sorted(imported.difference(declared).difference(package_roots))
    except zipfile.BadZipFile as exc:
        return {"ok": False, "action": "package_import_metadata", "status": "bad_zip", "zip_path": str(zip_path), "error": str(exc)}
    ok = not missing_declared_files and not missing_import_declarations and bool(version_consistency.get("ok"))
    return {
        "ok": ok,
        "action": "package_import_metadata",
        "status": "verified" if ok else "failed",
        "zip_path": str(zip_path),
        "declared_py_modules": declared,
        "declared_py_module_count": len(declared),
        "imported_promptbranch_modules": sorted(imported),
        "package_roots": sorted(package_roots),
        "missing_declared_files": missing_declared_files,
        "missing_import_declarations": missing_import_declarations,
        "version_consistency": version_consistency,
    }


def package_import_smoke(*, repo_path: str | Path = ".", python_executable: str | None = None) -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    declared = _declared_py_modules(root)
    modules = sorted({"promptbranch", "promptbranch.cli", *declared})
    expected_version = normalize_version(_read_version(root))
    if not declared:
        return {"ok": False, "action": "package_import_smoke", "status": "pyproject_missing_or_unreadable", "repo_path": str(root), "modules": modules}
    executable = python_executable or sys.executable
    code = "\n".join([
        "import contextlib",
        "import importlib",
        "import io",
        "import json",
        "import sys",
        "modules = json.loads(sys.argv[1])",
        "expected_version = sys.argv[2] or None",
        "results = []",
        "for module in modules:",
        "    try:",
        "        importlib.import_module(module)",
        "        results.append({'module': module, 'ok': True})",
        "    except Exception as exc:",
        "        results.append({'module': module, 'ok': False, 'error_type': type(exc).__name__, 'error': str(exc)})",
        "def norm(value):",
        "    text = str(value or '').strip()",
        "    if text.lower().startswith('v'):",
        "        text = text[1:]",
        "    return text or None",
        "observations = []",
        "def observe(name, value):",
        "    observations.append({'name': name, 'value': value, 'normalized': norm(value)})",
        "try:",
        "    from importlib import metadata as importlib_metadata",
        "    observe('installed_distribution.promptbranch', importlib_metadata.version('promptbranch'))",
        "except Exception as exc:",
        "    observe('installed_distribution.promptbranch', None)",
        "try:",
        "    import promptbranch_version",
        "    observe('promptbranch_version.PACKAGE_VERSION', getattr(promptbranch_version, 'PACKAGE_VERSION', None))",
        "    observe('promptbranch_version.VERSION_TAG', getattr(promptbranch_version, 'VERSION_TAG', None))",
        "except Exception:",
        "    observe('promptbranch_version.PACKAGE_VERSION', None)",
        "try:",
        "    import promptbranch_cli",
        "    observe('promptbranch_cli.CLI_VERSION', getattr(promptbranch_cli, 'CLI_VERSION', None))",
        "    buf = io.StringIO()",
        "    with contextlib.redirect_stdout(buf):",
        "        rc = promptbranch_cli.main(['version'])",
        "    output = buf.getvalue().strip()",
        "    observe('promptbranch version output', output.split()[-1] if output else None)",
        "except Exception:",
        "    observe('promptbranch_cli.CLI_VERSION', None)",
        "try:",
        "    import promptbranch_mcp",
        "    observe('promptbranch_mcp.MCP_SERVER_VERSION', getattr(promptbranch_mcp, 'MCP_SERVER_VERSION', None))",
        "    init = promptbranch_mcp.handle_mcp_jsonrpc_message({'jsonrpc':'2.0','id':1,'method':'initialize','params':{}})",
        "    observe('mcp server_info.version', (((init or {}).get('result') or {}).get('serverInfo') or {}).get('version'))",
        "except Exception:",
        "    observe('promptbranch_mcp.MCP_SERVER_VERSION', None)",
        "try:",
        "    import promptbranch_container_api",
        "    observe('promptbranch_container_api.SERVICE_VERSION', getattr(promptbranch_container_api, 'SERVICE_VERSION', None))",
        "except Exception:",
        "    observe('promptbranch_container_api.SERVICE_VERSION', None)",
        "missing = [item['name'] for item in observations if not item.get('normalized')]",
        "mismatches = [item for item in observations if item.get('normalized') and expected_version and item.get('normalized') != expected_version]",
        "version_consistency = {'ok': bool(expected_version) and not missing and not mismatches, 'expected_version': expected_version, 'observations': observations, 'missing': missing, 'mismatches': mismatches}",
        "payload = {'imports': results, 'version_consistency': version_consistency}",
        "print(json.dumps(payload, ensure_ascii=False))",
        "sys.exit(0 if all(item.get('ok') for item in results) and version_consistency.get('ok') else 1)",
    ])
    env = dict(os.environ)
    kept = []
    for entry in (env.get("PYTHONPATH") or "").split(os.pathsep):
        if not entry:
            continue
        try:
            resolved = Path(entry).expanduser().resolve()
            if resolved == root or root in resolved.parents:
                continue
        except OSError:
            pass
        kept.append(entry)
    if kept:
        env["PYTHONPATH"] = os.pathsep.join(kept)
    else:
        env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="promptbranch-import-smoke-") as tmp:
        completed = subprocess.run([executable, "-c", code, json.dumps(modules), expected_version or ""], cwd=tmp, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
    try:
        subprocess_payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        subprocess_payload = {}
    results = subprocess_payload.get("imports") if isinstance(subprocess_payload, dict) else []
    if not isinstance(results, list):
        results = []
    failures = [item for item in results if isinstance(item, dict) and not item.get("ok")]
    version_consistency = subprocess_payload.get("version_consistency") if isinstance(subprocess_payload, dict) else None
    if not isinstance(version_consistency, dict):
        version_consistency = {"ok": False, "expected_version": expected_version, "observations": [], "missing": ["runtime_version_payload"], "mismatches": []}
    ok = completed.returncode == 0 and not failures and bool(version_consistency.get("ok"))
    return {
        "ok": ok,
        "action": "package_import_smoke",
        "status": "verified" if ok else "failed",
        "repo_path": str(root),
        "python_executable": executable,
        "module_count": len(modules),
        "modules": modules,
        "failures": failures,
        "version_consistency": version_consistency,
        "returncode": completed.returncode,
        "stdout_bytes": len(completed.stdout or ""),
        "stderr": completed.stderr[-4000:] if completed.stderr else "",
        "source_tree_masking_prevented": True,
    }

def _package_hygiene(package_zip: str | None, *, repo_path: Path | str) -> dict[str, Any]:
    repo_path = Path(repo_path).expanduser().resolve()
    zip_path, candidates = _find_release_zip(package_zip, repo_path=repo_path)
    if zip_path is None:
        return {
            "ok": True,
            "action": "package_hygiene",
            "status": "expected_missing",
            "diagnostic": "No release ZIP found under repo_path; package hygiene check skipped.",
            "candidates": [str(candidate) for candidate in candidates],
        }

    bad_entries: list[str] = []
    testzip: str | None = None
    try:
        with zipfile.ZipFile(zip_path) as archive:
            testzip = archive.testzip()
            for name in archive.namelist():
                parts = [part for part in name.split("/") if part]
                if ".pytest_cache" in parts or "__pycache__" in parts or name.endswith((".pyc", ".pyo")):
                    bad_entries.append(name)
            wrapper_folder = False
            top_levels = {parts[0] for parts in ([part for part in item.split("/") if part] for item in archive.namelist()) if parts}
            if len(top_levels) == 1 and not any(name in archive.namelist() for name in ("VERSION", "README.md")):
                wrapper_folder = True
    except zipfile.BadZipFile as exc:
        return {"ok": False, "action": "package_hygiene", "status": "bad_zip", "zip_path": str(zip_path), "error": str(exc)}

    ok = not bad_entries and testzip is None and not wrapper_folder
    return {
        "ok": ok,
        "action": "package_hygiene",
        "status": "verified" if ok else "failed",
        "zip_path": str(zip_path),
        "testzip": testzip,
        "bad_entries": bad_entries,
        "wrapper_folder": wrapper_folder,
    }


def _run_agent_profile_sync(*, repo_path: str | Path = ".", profile_dir: str | Path | None = None, package_zip: str | None = None) -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    steps: list[dict[str, Any]] = []
    artifacts: dict[str, Any] = {}

    steps.append(_step("agent_host_smoke", mcp_host_smoke(repo_path=root, profile_dir=profile_dir)))
    steps.append(_step("agent_mcp_read_version", mcp_tool_call_via_stdio("filesystem.read", {"path": "VERSION", "max_bytes": 2000}, repo_path=root, profile_dir=profile_dir)))
    steps.append(_step("agent_run_readonly", agent_run("read VERSION and git status", repo_path=root, profile_dir=profile_dir)))
    steps.append(_step("skill_list", skill_list(repo_path=root, profile_dir=profile_dir)))
    steps.append(_step("skill_show_repo_inspection", skill_show("repo-inspection", repo_path=root, profile_dir=profile_dir)))
    steps.append(_step("skill_validate_repo_inspection", skill_validate(".promptbranch/skills/repo-inspection", repo_path=root, profile_dir=profile_dir)))
    steps.append(_step("agent_run_skill_repo_inspection", agent_run("inspect repo", repo_path=root, profile_dir=profile_dir, skill="repo-inspection")))
    steps.append(_step("agent_tool_call_test_smoke", agent_tool_call("test.smoke", {}, repo_path=root, profile_dir=profile_dir)))
    steps.append(_step("agent_run_smoke_tests", agent_run("run smoke tests", repo_path=root, profile_dir=profile_dir)))

    summarize_target = "VERSION" if (root / "VERSION").is_file() else "README.md"
    if (root / summarize_target).is_file():
        steps.append(_step("agent_summarize_log", agent_summarize_log(summarize_target, repo_path=root, max_bytes=12000)))
    else:
        steps.append(_step("agent_summarize_log", {"ok": False, "action": "agent_summarize_log", "status": "read_target_missing", "diagnostic": "VERSION/README.md not found for repo-bounded summarizer check"}))

    steps.append(_step("agent_summarize_log_path_escape", agent_summarize_log("/etc/hosts", repo_path=root), expected_failure=True, expected_status="path_outside_repo"))
    steps.append(_step("agent_reject_sync_sources", agent_run("sync sources", repo_path=root, profile_dir=profile_dir), expected_failure=True, expected_status="risk_rejected"))
    steps.append(_step("agent_reject_artifact_release", agent_run("create artifact release", repo_path=root, profile_dir=profile_dir), expected_failure=True, expected_status="risk_rejected"))
    steps.append(_step("agent_reject_arbitrary_pytest", agent_run("run pytest", repo_path=root, profile_dir=profile_dir), expected_failure=True, expected_status="risk_rejected"))
    steps.append(_step("version_consistency", source_version_consistency(repo_path=root)))
    steps.append(_step("package_import_metadata", _package_import_metadata(package_zip, repo_path=root)))
    steps.append(_step("package_import_smoke", package_import_smoke(repo_path=root)))
    steps.append(_step("package_hygiene", _package_hygiene(package_zip, repo_path=root)))

    ok = all(bool(step.get("ok")) for step in steps)
    return {
        "ok": ok,
        "action": "test_suite",
        "profile": "agent",
        "repo_path": str(root),
        "version": _read_version(root),
        "steps": steps,
        "artifacts": artifacts,
        "safety": {
            "browser_required": False,
            "write_tools_blocked": True,
            "model_has_execution_authority": False,
            "source_or_artifact_mutation_allowed": False,
        },
        "rate_limit_telemetry": _empty_rate_limit_telemetry(),
    }


async def run_test_suite_async(**kwargs: Any) -> dict[str, Any]:
    profile = str(kwargs.pop("profile", "browser") or "browser").strip().lower()
    repo_path = kwargs.pop("path", ".")
    package_zip = kwargs.pop("package_zip", None)
    requested_rate_limit_safe = kwargs.pop("rate_limit_safe", None)
    rate_limit_safe = (profile == "full") if requested_rate_limit_safe is None else bool(requested_rate_limit_safe)
    if profile not in TEST_SUITE_PROFILES:
        return {"ok": False, "action": "test_suite", "status": "invalid_profile", "profile": profile, "valid_profiles": list(TEST_SUITE_PROFILES)}

    rate_limit_strategy = {
        "enabled": bool(rate_limit_safe),
        "default_for_profile": profile == "full",
        "cooldown_signal": "conversation_history_429_or_modal",
        "telemetry_fields": [
            "rate_limit_modal_detected",
            "conversation_history_429_seen",
            "cooldown_wait_seconds_total",
            "cooldown_wait_count",
            "planned_cooldown_wait_seconds_total",
            "planned_cooldown_wait_count",
            "service_rate_limit_events",
        ],
        "operator_message": "If ChatGPT shows 'You're making requests too quickly', the live browser profile will honor persisted cooldowns and report rate-limit telemetry in the suite JSON.",
    }

    if profile == "agent":
        summary = _run_agent_profile_sync(repo_path=repo_path, profile_dir=kwargs.get("profile_dir"), package_zip=package_zip)
        summary["rate_limit_strategy"] = {**rate_limit_strategy, "browser_required": False}
        return summary

    browser_args = build_test_suite_namespace(**kwargs, rate_limit_safe=rate_limit_safe)
    browser_summary = await run_integration(browser_args)
    browser_summary["rate_limit_telemetry"] = extract_rate_limit_telemetry(browser_summary)
    browser_summary["rate_limit_strategy"] = {
        **rate_limit_strategy,
        "step_delay_seconds": getattr(browser_args, "step_delay_seconds", None),
        "post_ask_delay_seconds": getattr(browser_args, "post_ask_delay_seconds", None),
        "task_list_visible_poll_min_seconds": getattr(browser_args, "task_list_visible_poll_min_seconds", None),
        "task_list_visible_poll_max_seconds": getattr(browser_args, "task_list_visible_poll_max_seconds", None),
        "task_list_visible_max_attempts": getattr(browser_args, "task_list_visible_max_attempts", None),
    }
    if profile == "browser":
        browser_summary.setdefault("profile", "browser")
        browser_summary.setdefault("version", _read_version(Path(repo_path).expanduser().resolve()))
        return browser_summary

    agent_summary = _run_agent_profile_sync(repo_path=repo_path, profile_dir=kwargs.get("profile_dir"), package_zip=package_zip)
    return {
        "ok": bool(browser_summary.get("ok")) and bool(agent_summary.get("ok")),
        "action": "test_suite",
        "profile": "full",
        "version": _read_version(Path(repo_path).expanduser().resolve()),
        "browser": browser_summary,
        "agent": agent_summary,
        "rate_limit_strategy": browser_summary.get("rate_limit_strategy"),
        "rate_limit_telemetry": browser_summary.get("rate_limit_telemetry", _empty_rate_limit_telemetry()),
        "safety": {
            "write_tools_blocked": bool(agent_summary.get("safety", {}).get("write_tools_blocked")),
            "model_has_execution_authority": False,
            "source_or_artifact_mutation_allowed": False,
        },
    }


def run_test_suite_sync(**kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_test_suite_async(**kwargs))
