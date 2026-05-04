from __future__ import annotations

import argparse
import asyncio
import zipfile
from pathlib import Path
from typing import Any, Optional, Sequence

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


def _package_hygiene(package_zip: str | None, *, repo_path: Path) -> dict[str, Any]:
    version = _read_version(repo_path)
    candidates: list[Path] = []
    if package_zip:
        candidates.append((repo_path / package_zip).expanduser() if not Path(package_zip).is_absolute() else Path(package_zip).expanduser())
    if version:
        candidates.append(repo_path / f"chatgpt_claudecode_workflow_{version}.zip")
    candidates.extend(sorted(repo_path.glob("chatgpt_claudecode_workflow_v*.zip"), reverse=True))

    zip_path = next((candidate.resolve() for candidate in candidates if candidate.exists()), None)
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
    }


async def run_test_suite_async(**kwargs: Any) -> dict[str, Any]:
    profile = str(kwargs.pop("profile", "browser") or "browser").strip().lower()
    repo_path = kwargs.pop("path", ".")
    package_zip = kwargs.pop("package_zip", None)
    if profile not in TEST_SUITE_PROFILES:
        return {"ok": False, "action": "test_suite", "status": "invalid_profile", "profile": profile, "valid_profiles": list(TEST_SUITE_PROFILES)}

    if profile == "agent":
        return _run_agent_profile_sync(repo_path=repo_path, profile_dir=kwargs.get("profile_dir"), package_zip=package_zip)

    browser_args = build_test_suite_namespace(**kwargs)
    browser_summary = await run_integration(browser_args)
    if profile == "browser":
        browser_summary.setdefault("profile", "browser")
        return browser_summary

    agent_summary = _run_agent_profile_sync(repo_path=repo_path, profile_dir=kwargs.get("profile_dir"), package_zip=package_zip)
    return {
        "ok": bool(browser_summary.get("ok")) and bool(agent_summary.get("ok")),
        "action": "test_suite",
        "profile": "full",
        "browser": browser_summary,
        "agent": agent_summary,
        "safety": {
            "write_tools_blocked": bool(agent_summary.get("safety", {}).get("write_tools_blocked")),
            "model_has_execution_authority": False,
            "source_or_artifact_mutation_allowed": False,
        },
    }


def run_test_suite_sync(**kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_test_suite_async(**kwargs))
