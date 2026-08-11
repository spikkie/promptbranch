from __future__ import annotations

import argparse
import ast
import asyncio
import json
from datetime import datetime, timezone
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Optional, Sequence

from promptbranch_python_authority import launcher_python

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None  # type: ignore[assignment]

from promptbranch_full_integration_test import make_parser as make_integration_parser, resolve_step_selection, run_integration
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
from promptbranch_artifacts import ArtifactRegistry, ArtifactRegistryStateError, build_source_sync_preflight, plan_repo_snapshot, release_entry_hygiene_violations, sha256_file, verify_zip_artifact
from promptbranch_version import PACKAGE_VERSION, normalize_version, version_tag
from promptbranch_ask_protocol import BEGIN_REPLY_MARKER, END_REPLY_MARKER, classify_artifact_candidates, parse_promptbranch_reply
from promptbranch_eta import append_eta_observation, estimate_named_step_eta, load_eta_history


DEFAULT_ONLY: tuple[str, ...] = ()
DEFAULT_SKIP: tuple[str, ...] = ()
TEST_SUITE_PROFILES = ("browser", "agent", "full")
TEST_SUITE_REPORT_SCHEMA = "promptbranch.test_suite.report"
TEST_SUITE_REPORT_SCHEMA_VERSION = "1.0"


EXPECTED_NON_FAILURE_STATUSES = {
    "expected_missing",
    "expected_unsupported",
    "expected_skip",
}


AGENT_PROGRESS_STEP_NAMES: tuple[str, ...] = (
    "agent_host_smoke",
    "agent_mcp_read_version",
    "agent_run_readonly",
    "skill_list",
    "skill_show_repo_inspection",
    "skill_validate_repo_inspection",
    "agent_run_skill_repo_inspection",
    "agent_tool_call_test_smoke",
    "agent_run_smoke_tests",
    "agent_summarize_log",
    "agent_summarize_log_path_escape",
    "agent_reject_sync_sources",
    "agent_reject_artifact_release",
    "agent_reject_arbitrary_pytest",
    "version_consistency",
    "package_import_metadata",
    "package_import_smoke",
    "artifact_roundtrip",
    "src_sync_dry_run_plan",
    "src_sync_upload_preflight_plan",
    "package_hygiene",
)


def _human_duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    total = max(0, int(round(float(seconds))))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class TestProgressLedger:
    """Observational named-step progress and ETA ledger.

    Validation authority remains entirely in the step outcomes. ETA is derived
    only from successful timing observations, prefers same-step/same-transport
    medians, and falls back to phase medians. Direct timings may be used as an
    ETA-only localhost prior; they never satisfy localhost validation.
    """

    def __init__(
        self,
        units: Sequence[str],
        *,
        enabled: bool = True,
        transport: str | None = None,
        history_path: str | Path | None = None,
        known_skipped_units: Sequence[str] = (),
        clock: Any = time.monotonic,
    ) -> None:
        self.units = tuple(dict.fromkeys(str(unit) for unit in units))
        self.enabled = bool(enabled)
        self.transport = str(transport or os.environ.get("PROMPTBRANCH_ETA_TRANSPORT") or "direct")
        explicit_history = history_path or os.environ.get("PROMPTBRANCH_ETA_HISTORY_PATH")
        if explicit_history:
            self.history_path: Path | None = Path(explicit_history).expanduser()
        else:
            profile_dir = os.environ.get("PROMPTBRANCH_PROFILE_DIR")
            self.history_path = Path(profile_dir).expanduser() / "eta-history.json" if profile_dir else None
        self.known_skipped_units = {str(unit) for unit in known_skipped_units}
        self._clock = clock
        self.started_monotonic = float(self._clock())
        self.states: dict[str, str] = {unit: "pending" for unit in self.units}
        self.current: str | None = None
        self._unit_started: dict[str, float] = {}
        self._history_records = load_eta_history(self.history_path)
        self._last_eta: dict[str, Any] = {
            "active_remaining": len([unit for unit in self.units if unit not in self.known_skipped_units]),
            "eta_seconds_approx": None,
            "eta_seconds_range": {"low": None, "high": None},
            "eta_approx": "unknown",
            "eta_range": "unknown",
            "eta_confidence": "unknown",
            "eta_basis": "insufficient_named_step_history",
            "active_steps": [unit for unit in self.units if unit not in self.known_skipped_units],
            "unresolved_steps": [unit for unit in self.units if unit not in self.known_skipped_units],
        }

    def _counts(self) -> tuple[int, int, int, int]:
        passed = sum(1 for value in self.states.values() if value == "passed")
        failed = sum(1 for value in self.states.values() if value == "failed")
        skipped = sum(1 for value in self.states.values() if value.startswith("skipped"))
        completed = passed + failed + skipped
        return completed, passed, failed, skipped

    def _estimate(self) -> dict[str, Any]:
        now = float(self._clock())
        current_elapsed = 0.0
        if self.current and self.current in self._unit_started:
            current_elapsed = max(0.0, now - self._unit_started[self.current])
        estimate = estimate_named_step_eta(
            units=self.units,
            states=self.states,
            current=self.current,
            current_elapsed_seconds=current_elapsed,
            history_records=self._history_records,
            transport=self.transport,
            known_skipped_units=tuple(self.known_skipped_units),
            previous_eta_seconds=self._last_eta.get("eta_seconds_approx"),
            previous_eta_high_seconds=(self._last_eta.get("eta_seconds_range") or {}).get("high"),
            previous_active_steps=self._last_eta.get("active_steps") or (),
        )
        self._last_eta = estimate
        return estimate

    def _emit(self, *, status: str, current: str | None = None) -> None:
        if not self.enabled:
            return
        completed, passed, failed, skipped = self._counts()
        total = len(self.units)
        elapsed = max(0.0, float(self._clock()) - self.started_monotonic)
        percent = 100.0 if total == 0 else round((completed / total) * 100.0, 1)
        estimate = self._estimate()
        active = current or self.current or "none"
        print(
            "pb_test_progress: "
            f"status={status} current={active} completed={completed}/{total} "
            f"passed={passed} failed={failed} skipped={skipped} percent={percent:.1f} "
            f"elapsed={_human_duration(elapsed)} active_remaining={estimate['active_remaining']} "
            f"eta_approx={estimate['eta_approx']} eta_range={estimate['eta_range']} "
            f"eta_confidence={estimate['eta_confidence']} eta_basis={estimate['eta_basis']}",
            flush=True,
        )

    def announce(self, current: str) -> None:
        self.current = current
        self._emit(status="running", current=current)

    def start(self, unit: str) -> None:
        if unit not in self.states or self.states[unit] != "pending":
            return
        self.current = unit
        self.states[unit] = "running"
        self._unit_started[unit] = float(self._clock())
        self._emit(status="running", current=unit)

    def finish(
        self,
        unit: str,
        *,
        ok: bool,
        skipped: bool = False,
        skip_reason: str | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        if unit not in self.states:
            return
        if self.states[unit] in {"passed", "failed"} or self.states[unit].startswith("skipped"):
            return
        now = float(self._clock())
        started = self._unit_started.pop(unit, None)
        observed_duration = duration_seconds
        if observed_duration is None and started is not None:
            observed_duration = max(0.0, now - started)
        if skipped:
            self.states[unit] = f"skipped:{skip_reason or 'requested'}"
            status = "skipped"
        else:
            self.states[unit] = "passed" if ok else "failed"
            status = self.states[unit]
            if observed_duration is not None and float(observed_duration) >= 0.0:
                record = append_eta_observation(
                    self.history_path,
                    step=unit,
                    transport=self.transport,
                    duration_seconds=float(observed_duration),
                    outcome=status,
                )
                if record is None:
                    record = {
                        "step": unit,
                        "transport": self.transport,
                        "duration_seconds": float(observed_duration),
                        "outcome": status,
                    }
                self._history_records.append(record)
        self.current = None
        self._emit(status=status, current=unit)

    def skip_pending(self, *, reason: str) -> None:
        for unit, state in list(self.states.items()):
            if state in {"pending", "running"}:
                self.states[unit] = f"skipped:{reason}"
        self._unit_started.clear()
        self.current = None
        self._emit(status="fail_fast_stopped")

    def snapshot(self) -> dict[str, Any]:
        completed, passed, failed, skipped = self._counts()
        total = len(self.units)
        percent = 100.0 if total == 0 else round((completed / total) * 100.0, 1)
        estimate = self._estimate()
        return {
            "total_units": total,
            "completed_units": completed,
            "passed_units": passed,
            "failed_units": failed,
            "skipped_units": skipped,
            "percent_complete": percent,
            "states": dict(self.states),
            "transport": self.transport,
            **estimate,
        }

    def finish_summary(self) -> None:
        completed, _passed, failed, _skipped = self._counts()
        status = "completed" if completed == len(self.units) and failed == 0 else "failed" if failed else "incomplete"
        self._emit(status=status)


class ProgressStepList(list[dict[str, Any]]):
    def __init__(self, *, progress: TestProgressLedger | None, prefix: str) -> None:
        super().__init__()
        self.progress = progress
        self.prefix = prefix
        self._last_append_monotonic = float(progress._clock()) if progress is not None else 0.0

    def append(self, item: dict[str, Any]) -> None:
        now = float(self.progress._clock()) if self.progress is not None else 0.0
        duration = max(0.0, now - self._last_append_monotonic) if self.progress is not None else None
        self._last_append_monotonic = now
        super().append(item)
        if self.progress is None or not isinstance(item, dict):
            return
        name = str(item.get("name") or "")
        unit = f"{self.prefix}.{name}"
        self.progress.finish(unit, ok=bool(item.get("ok")), duration_seconds=duration)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


RELEASE_VALIDATION_PYTHON_PLACEHOLDER = "{release_validation_python}"
RELEASE_VALIDATION_PYTEST_VERSION_ENV = "PROMPTBRANCH_RELEASE_VALIDATION_PYTEST_VERSION"
RELEASE_VALIDATION_PYTEST_VERSION = "9.0.2"
RELEASE_VALIDATION_SKIP_DUPLICATE_ENV = "PROMPTBRANCH_RELEASE_VALIDATION_GROUPS_SKIP_DUPLICATE"


def release_validation_python() -> str:
    """Return the exact Promptbranch launcher interpreter.

    No environment or CLI selector may replace release-validation Python.
    """
    return launcher_python()


def release_validation_runner_preflight(*, timeout_seconds: float = 10.0) -> dict[str, Any]:
    try:
        python_executable = release_validation_python()
    except RuntimeError as exc:
        return {
            "ok": False,
            "status": "python_authority_mismatch",
            "python_executable": launcher_python(),
            "expected_pytest_version": os.environ.get(
                RELEASE_VALIDATION_PYTEST_VERSION_ENV, RELEASE_VALIDATION_PYTEST_VERSION
            ),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    expected_pytest_version = os.environ.get(
        RELEASE_VALIDATION_PYTEST_VERSION_ENV,
        RELEASE_VALIDATION_PYTEST_VERSION,
    )
    script = r"""
from importlib import metadata
import json
from pathlib import Path
import sys
payload = {
    "python_executable": str(Path(sys.executable).absolute()),
    "python_prefix": str(Path(sys.prefix).resolve()),
}
try:
    import pytest
    payload["pytest_version"] = metadata.version("pytest")
    payload["pytest_module"] = str(Path(pytest.__file__).resolve())
except Exception as exc:
    payload["error_type"] = type(exc).__name__
    payload["error"] = str(exc)
print(json.dumps(payload, sort_keys=True))
""".strip()
    try:
        completed = subprocess.run(
            [python_executable, "-c", script],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(0.1, min(float(timeout_seconds), 10.0)),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "status": "release_validation_runner_unavailable",
            "python_executable": python_executable,
            "expected_pytest_version": expected_pytest_version,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    try:
        observed = json.loads((completed.stdout or "").strip() or "{}")
    except json.JSONDecodeError:
        observed = {}
    prefix = Path(str(observed.get("python_prefix") or "/")).resolve()
    module_text = str(observed.get("pytest_module") or "")
    module_path = Path(module_text).resolve() if module_text else None
    module_inside_prefix = bool(module_path and _path_is_within(module_path, prefix))
    executable_match = str(observed.get("python_executable") or "") == python_executable
    version_match = str(observed.get("pytest_version") or "") == expected_pytest_version
    ok = completed.returncode == 0 and executable_match and version_match and module_inside_prefix
    return {
        "ok": ok,
        "status": "release_validation_runner_verified" if ok else "release_validation_runner_invalid",
        "python_executable": python_executable,
        "expected_pytest_version": expected_pytest_version,
        "observed": observed,
        "checks": {
            "process_exit_zero": completed.returncode == 0,
            "python_executable_match": executable_match,
            "pytest_version_match": version_match,
            "pytest_module_inside_python_prefix": module_inside_prefix,
        },
        "returncode": completed.returncode,
        "stderr_tail": _tail_text(completed.stderr or ""),
    }


def _release_validation_command(*args: str) -> list[str]:
    return [RELEASE_VALIDATION_PYTHON_PLACEHOLDER, *args]


def _resolve_release_validation_command(command: Sequence[object]) -> list[str]:
    return [
        release_validation_python() if str(item) == RELEASE_VALIDATION_PYTHON_PLACEHOLDER else str(item)
        for item in command
    ]


RELEASE_VALIDATION_GROUPS: dict[str, dict[str, Any]] = {
    "project_control_surface": {
        "required": True,
        "description": "Project MVP/DoD/Plan control-surface validator.",
        "command": _release_validation_command("-m", "pytest", "-q", "tests/test_project_control_surface.py"),
    },
    "project_authority_behavioral_surface": {
        "required": True,
        "description": "Project authority graph, runtime registry resolver, and behavioral surface inventory contracts.",
        "command": _release_validation_command(
            "-m",
            "pytest",
            "-q",
            "tests/test_project_authority_graph.py",
            "tests/test_behavioral_surface.py",
        ),
    },
    "application_architecture_structural": {
        "required": True,
        "description": "PBAI-001 tracked declaration and fail-closed structural architecture validation.",
        "command": _release_validation_command(
            "-m",
            "pytest",
            "-q",
            "tests/test_promptbranch_application_architecture.py",
            "tests/test_promptbranch_application_migration.py",
            "tests/test_promptbranch_tool_authoring.py",
        ),
    },
    "application_architecture_registry": {
        "required": True,
        "description": "PBAI-001 exact AI object registry and bounded authority reference resolution.",
        "command": _release_validation_command(
            "promptbranch_cli.py",
            "application",
            "architecture",
            "validate",
            "--repo-path",
            ".",
            "--level",
            "registry",
            "--json",
        ),
    },
    "application_architecture_executable": {
        "required": True,
        "description": "PBAI-001 bounded skill execution through MCP stdio with validated SkillRun evidence.",
        "command": _release_validation_command(
            "promptbranch_cli.py",
            "application",
            "architecture",
            "validate",
            "--repo-path",
            ".",
            "--level",
            "executable",
            "--json",
        ),
    },
    "version_surface": {
        "required": True,
        "description": "VERSION, pyproject, and promptbranch_version consistency.",
        "command": _release_validation_command("-m", "pytest", "-q", "tests/test_promptbranch_version.py"),
    },
    "artifact_json_contracts": {
        "required": True,
        "description": "Artifact/adoption/current JSON contract regression coverage.",
        "command": _release_validation_command(
            "-m",
            "pytest",
            "-q",
            "tests/test_promptbranch_artifacts.py",
            "tests/test_promptbranch_cli.py",
            "-k",
            "adopt or artifact_current or local_only or local_artifact_not_found or promptbranch_repo or baseline_status or mvp_status or test_suite_full_profile_dispatches_to_runner",
        ),
    },
    "repo_project_registry": {
        "required": True,
        "description": "Project-scoped repo registry and repo doctor regression coverage.",
        "command": _release_validation_command(
            "-m",
            "pytest",
            "-q",
            "tests/test_promptbranch_project.py",
            "tests/test_promptbranch_repos.py",
        ),
    },
    "browser_scheduler_source_lifecycle": {
        "required": True,
        "description": "Scheduler/source lifecycle and same-profile queue regression coverage.",
        "timeout_seconds": 300.0,
        "nodeid_progress": True,
        "command": _release_validation_command(
            "-m",
            "pytest",
            "-q",
            "tests/test_promptbranch_automation_service.py::test_profile_queue_default_matches_advertised_scheduler_timeout",
            "tests/test_promptbranch_automation_service.py::test_source_remove_waits_behind_source_list_with_same_profile",
            "tests/test_promptbranch_automation_service.py::test_project_remove_is_frozen_before_profile_scheduler",
            "tests/test_promptbranch_automation_service.py::test_browser_profile_busy_payload_marks_scheduler_path",
            "tests/test_promptbranch_automation_service.py::test_cross_process_profile_lock_waits_until_external_owner_releases",
            "tests/test_promptbranch_automation_service.py::test_cross_process_profile_lock_timeout_honors_queue_deadline_and_reports_owner",
            "tests/test_promptbranch_shell_scripts.py::test_release_control_waits_for_live_profile_handoff_before_continuous_live",
            "tests/test_promptbranch_shell_scripts.py::test_release_control_live_preflight_and_continuous_use_same_service_owner",
            "tests/test_promptbranch_shell_scripts.py::test_release_validation_group_includes_cross_process_profile_handoff_regressions",
            "tests/test_promptbranch_cli.py::test_src_add_promotes_browser_profile_busy_to_top_level_payload",
            "tests/test_promptbranch_cli.py::test_queue_status_command_emits_scheduler_json",
            "tests/test_promptbranch_cli.py::test_release_lifecycle_plan_includes_scheduler_and_source_queue",
            "tests/test_promptbranch_cli.py::test_release_lifecycle_plan_blocks_when_artifact_current_is_stale",
            "tests/test_promptbranch_cli.py::test_src_list_browser_profile_busy_reports_wait_idle_guidance",
        ),
    },
    "release_lifecycle_plan": {
        "required": True,
        "description": "Release lifecycle plan/queue invariants.",
        "command": _release_validation_command(
            "-m",
            "pytest",
            "-q",
            "tests/test_promptbranch_cli.py",
            "-k",
            "release_lifecycle_plan",
        ),
    },
    "release_state_machine": {
        "required": True,
        "description": "Canonical release-attempt state machine, independent state verification, transition guards, resume, idempotency, projection recovery, and final convergence.",
        "command": _release_validation_command(
            "-m",
            "pytest",
            "-q",
            "tests/test_release_state_machine.py",
            "tests/test_promptbranch_python_authority.py",
            "tests/test_release_state_machine_docker_integration.py",
            "tests/test_promptbranch_release_eta.py",
            "tests/test_artifact_conversation_provenance.py",
        ),
    },
    "release_pipeline": {
        "required": True,
        "description": "Evidence-bound generic release-pipeline planning, incremental checkpoints, import/resume recovery, mutation reuse, Project Source publication, adoption, and accepted/current verification.",
        "command": _release_validation_command(
            "-m",
            "pytest",
            "-q",
            "tests/test_promptbranch_release_contract.py",
            "tests/test_promptbranch_release_attempt.py",
            "tests/test_promptbranch_release_pipeline.py",
            "tests/test_promptbranch_mvp_proof.py",
            "tests/test_promptbranch_mvp_ask_lifecycle.py",
            "tests/test_ask_release_artifact_execution_prompt.py",
            "tests/test_promptbranch_shell_scripts.py::test_release_control_auth_bootstrap_403_detector_ignores_http_429",
            "tests/test_promptbranch_shell_scripts.py::test_release_control_auth_bootstrap_403_detector_accepts_explicit_http_403",
            "tests/test_promptbranch_shell_scripts.py::test_release_control_auth_bootstrap_403_detector_requires_explicit_status_static",
            "tests/test_promptbranch_shell_scripts.py::test_release_control_join_postcheck_accepts_bare_requested_and_slugged_tracked_aliases",
            "tests/test_promptbranch_shell_scripts.py::test_release_control_join_postcheck_rejects_true_cross_project_uuid",
        ),
    },
    "release_set_planner": {
        "required": True,
        "description": "Read-only multi-repository release-set manifest, dependency ordering, compatibility matrix, immutable target verification, and fail-closed cycle/constraint coverage.",
        "command": _release_validation_command(
            "-m",
            "pytest",
            "-q",
            "tests/test_promptbranch_release_set.py",
            "-k",
            "not release_set_apply and not rollout_evidence and not guarded_apply and not repository_owned_rollback and not release_set_reconcile and not release_set_resume",
        ),
    },
    "release_set_rollout": {
        "required": True,
        "description": "Exact-plan-bound release-set execution, complete lifecycle authorization, reverse rollback, exact previous identity restoration, and tamper-evident rollout evidence.",
        "command": _release_validation_command(
            "-m",
            "pytest",
            "-q",
            "tests/test_promptbranch_release_set.py",
            "-k",
            "release_set_apply or rollout_evidence or guarded_apply or repository_owned_rollback or release_set_reconcile or release_set_resume",
        ),
    },
    "sandbox_mutation_rollback_gate": {
        "required": True,
        "description": "Mandatory sandbox mutation verification, validation immutability, exact rollback, repository immutability, and workspace cleanup gate.",
        "timeout_seconds": 180.0,
        "command": _release_validation_command(
            "scripts/verify-sandbox-mutation-rollback-release-gate.py",
            "--repo",
            ".",
        ),
    },
    "execution_envelope_validation_gate": {
        "required": True,
        "description": "Mandatory v0.1.108 deterministic execution-envelope validation with zero commands, workspaces, mutations, or correction execution authority.",
        "timeout_seconds": 120.0,
        "command": _release_validation_command(
            "promptbranch_cli.py",
            "loop",
            "execution-envelope-validation",
            "--target",
            "examples/loop-targets/sandboxed-file-mutation-target.json",
            "--repo-root",
            ".",
            "--json",
        ),
    },
    "compileall": {
        "required": True,
        "description": "Repository Python source compiles.",
        "command": _release_validation_command("-m", "compileall", "-q", "."),
    },
}


def release_validation_group_manifest() -> dict[str, dict[str, Any]]:
    return {
        group: {
            "required": bool(spec.get("required")),
            "description": spec.get("description"),
            "timeout_seconds": float(spec.get("timeout_seconds", 600.0)),
            "nodeid_progress": bool(spec.get("nodeid_progress")),
            "command": _resolve_release_validation_command(spec.get("command", [])),
        }
        for group, spec in RELEASE_VALIDATION_GROUPS.items()
    }


def _tail_text(text: str, *, max_chars: int = 4000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _release_validation_isolation_paths(isolation_root: Path) -> dict[str, Path]:
    root = isolation_root.expanduser().resolve()
    paths = {
        "root": root,
        "home": root / "home",
        "tmp": root / "tmp",
        "xdg_cache": root / "xdg-cache",
        "xdg_config": root / "xdg-config",
        "xdg_data": root / "xdg-data",
        "xdg_state": root / "xdg-state",
        "profile": root / "profile",
        "pycache": root / "pycache",
        "project_state": root / "project-state",
        "project_config": root / "project-config",
        "project_cache": root / "xdg-config" / "promptbranch" / "project-list-cache.json",
    }
    for key, path in paths.items():
        if key not in {"root", "project_cache"}:
            path.mkdir(parents=True, exist_ok=True)
    paths["project_cache"].parent.mkdir(parents=True, exist_ok=True)
    return paths


def _release_validation_group_env(
    *,
    isolation_root: Path,
    nodeid: str | None = None,
) -> dict[str, str]:
    env = os.environ.copy()
    # Release validation groups are deterministic repo-local checks. Disable
    # ambient pytest plugin autoload so locally installed plugins cannot hang
    # or change release-gate behavior after live browser tests have run.
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    # These groups are offline repo validations. Do not let the surrounding
    # live/browser transport leak service routing into the pytest process.
    for key in list(env):
        if key.startswith("CHATGPT_"):
            env.pop(key, None)
    for key in (
        "PROMPTBRANCH_SERVICE_BASE_URL",
        "PROMPTBRANCH_SERVICE_PORT",
        "PROMPTBRANCH_SERVICE_IMAGE",
        "PROMPTBRANCH_SERVICE_IMAGE_TAG",
        "PROMPTBRANCH_ARTIFACT_SHA256",
        "PROMPTBRANCH_VERSION",
        "PROMPTBRANCH_LOCALHOST_BASE_URL",
        "PROMPTBRANCH_CONTAINER_ID",
        "PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_SEED_DIR",
        "PROMPTBRANCH_BROWSER_PROFILE_LOCK_WAIT_SECONDS",
        "PROMPTBRANCH_BROWSER_PROFILE_STALE_LOCK_SECONDS",
        "PROMPTBRANCH_SOURCE_MUTATION_PROFILE_WAIT_SECONDS",
        "PROMPTBRANCH_CANDIDATE_PYTHON",
        "PROMPTBRANCH_RELEASE_VALIDATION_PYTHON",
    ):
        env.pop(key, None)
    # Avoid operator-level pytest customizations in the release-validation
    # subprocess. The release gate owns its selected nodeids and options.
    env.pop("PYTEST_ADDOPTS", None)

    paths = _release_validation_isolation_paths(isolation_root)
    env.update({
        "HOME": str(paths["home"]),
        "TMPDIR": str(paths["tmp"]),
        "XDG_CACHE_HOME": str(paths["xdg_cache"]),
        "XDG_CONFIG_HOME": str(paths["xdg_config"]),
        "XDG_DATA_HOME": str(paths["xdg_data"]),
        "XDG_STATE_HOME": str(paths["xdg_state"]),
        "PROMPTBRANCH_PROFILE_DIR": str(paths["profile"]),
        "PYTHONPYCACHEPREFIX": str(paths["pycache"]),
        "PROMPTBRANCH_PROJECT_STATE_HOME": str(paths["project_state"]),
        "PROMPTBRANCH_PROJECT_CONFIG_HOME": str(paths["project_config"]),
        "PROMPTBRANCH_PROJECT_CACHE_PATH": str(paths["project_cache"]),
        "PROMPTBRANCH_RELEASE_VALIDATION_ISOLATED": "1",
        "PROMPTBRANCH_RELEASE_VALIDATION_ROOT": str(paths["root"]),
        # Retain the older diagnostic variable, but the real runtime authority
        # is PROMPTBRANCH_PROFILE_DIR above.
        "PROMPTBRANCH_RELEASE_VALIDATION_PROFILE_DIR": str(paths["profile"]),
    })
    if nodeid:
        env["PROMPTBRANCH_RELEASE_VALIDATION_NODEID"] = nodeid
    return env


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.expanduser().resolve().relative_to(root.expanduser().resolve())
    except ValueError:
        return False
    return True


def _release_validation_isolation_preflight(
    *,
    repo_path: Path,
    isolation_root: Path,
    env: dict[str, str],
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    root = isolation_root.expanduser().resolve()
    ambient_profile = (repo_path / ".pb_profile").resolve()
    ambient_lock = ambient_profile / ".promptbranch-browser-profile.lock"
    script = """
import json
import os
from promptbranch_project import project_config_home, project_state_home
from promptbranch_state import global_project_cache_path, resolve_profile_dir
payload = {
    "profile_dir": str(resolve_profile_dir(cwd=os.getcwd())),
    "project_state_home": str(project_state_home()),
    "project_config_home": str(project_config_home()),
    "project_cache_path": str(global_project_cache_path()),
    "python_pycache_prefix": os.environ.get("PYTHONPYCACHEPREFIX"),
    "home": os.environ.get("HOME"),
    "tmpdir": os.environ.get("TMPDIR"),
    "xdg_config_home": os.environ.get("XDG_CONFIG_HOME"),
    "xdg_state_home": os.environ.get("XDG_STATE_HOME"),
}
print(json.dumps(payload, sort_keys=True))
""".strip()
    command = [release_validation_python(), "-c", script]
    try:
        completed = subprocess.run(
            command,
            cwd=str(repo_path),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(0.1, min(float(timeout_seconds), 10.0)),
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "status": "isolation_preflight_timeout",
            "command": command,
            "timeout_seconds": max(0.1, min(float(timeout_seconds), 10.0)),
            "stdout_tail": _tail_text((exc.stdout or "") if isinstance(exc.stdout, str) else ""),
            "stderr_tail": _tail_text((exc.stderr or "") if isinstance(exc.stderr, str) else ""),
            "ambient_repo_profile_lock": {
                "profile_dir": str(ambient_profile),
                "lock_path": str(ambient_lock),
                "lock_file_exists": ambient_lock.exists(),
                "contents_read": False,
                "wait_attempted": False,
            },
        }
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if completed.returncode != 0:
        return {
            "ok": False,
            "status": "isolation_preflight_process_failed",
            "command": command,
            "returncode": completed.returncode,
            "stdout_tail": _tail_text(stdout),
            "stderr_tail": _tail_text(stderr),
            "ambient_repo_profile_lock": {
                "profile_dir": str(ambient_profile),
                "lock_path": str(ambient_lock),
                "lock_file_exists": ambient_lock.exists(),
                "contents_read": False,
                "wait_attempted": False,
            },
        }
    try:
        payload = json.loads(stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "status": "isolation_preflight_invalid_json",
            "command": command,
            "error": str(exc),
            "stdout_tail": _tail_text(stdout),
            "stderr_tail": _tail_text(stderr),
            "ambient_repo_profile_lock": {
                "profile_dir": str(ambient_profile),
                "lock_path": str(ambient_lock),
                "lock_file_exists": ambient_lock.exists(),
                "contents_read": False,
                "wait_attempted": False,
            },
        }

    resolved = {
        key: Path(str(value)).expanduser().resolve()
        for key, value in payload.items()
        if key in {
            "profile_dir",
            "project_state_home",
            "project_config_home",
            "project_cache_path",
            "python_pycache_prefix",
            "home",
            "tmpdir",
            "xdg_config_home",
            "xdg_state_home",
        } and value
    }
    outside_root = {
        key: str(path)
        for key, path in resolved.items()
        if not _path_is_within(path, root)
    }
    resolved_profile = resolved.get("profile_dir")
    ambient_lock_reachable = bool(
        resolved_profile is not None
        and (resolved_profile == ambient_profile or _path_is_within(ambient_lock, resolved_profile))
    )
    ok = not outside_root and not ambient_lock_reachable
    return {
        "ok": ok,
        "status": "isolation_preflight_passed" if ok else "isolation_preflight_failed",
        "command": command,
        "returncode": completed.returncode,
        "isolation_root": str(root),
        "resolved_paths": {key: str(path) for key, path in resolved.items()},
        "outside_isolation_root": outside_root,
        "profile_inside_isolation_root": bool(resolved_profile and _path_is_within(resolved_profile, root)),
        "ambient_repo_profile_lock": {
            "profile_dir": str(ambient_profile),
            "lock_path": str(ambient_lock),
            "lock_file_exists": ambient_lock.exists(),
            "reachable_from_resolved_profile": ambient_lock_reachable,
            "contents_read": False,
            "wait_attempted": False,
        },
        "stdout_tail": _tail_text(stdout),
        "stderr_tail": _tail_text(stderr),
    }


def _split_pytest_nodeid_command(command: Sequence[str]) -> tuple[list[str], list[str]]:
    nodeids = [str(item) for item in command if str(item).startswith("tests/") and "::" in str(item)]
    if not nodeids:
        return list(command), []
    first_nodeid = next(i for i, item in enumerate(command) if str(item) in nodeids)
    # The release gate intentionally uses explicit nodeids only; if any option
    # appears after the first nodeid, fall back to the original group execution
    # rather than accidentally changing pytest semantics.
    trailing = [str(item) for item in command[first_nodeid:] if str(item) not in nodeids]
    if trailing:
        return list(command), []
    return [str(item) for item in command[:first_nodeid]], nodeids


def _run_release_validation_group_with_nodeid_progress(
    group_name: str,
    spec: dict[str, Any],
    *,
    repo_path: Path,
    command: list[str],
    timeout_seconds: float,
    started_at: str,
) -> dict[str, Any] | None:
    command_prefix, nodeids = _split_pytest_nodeid_command(command)
    if not nodeids:
        return None

    started_monotonic = time.monotonic()
    isolation_parent = Path(tempfile.mkdtemp(prefix=f"pb-release-validation-{group_name}-"))
    isolation_diagnostics = {
        "enabled": True,
        "root": str(isolation_parent),
        "mode": "explicit_runtime_path_authority_per_nodeid",
        "path_authority_env_keys": [
            "HOME",
            "TMPDIR",
            "XDG_CACHE_HOME",
            "XDG_CONFIG_HOME",
            "XDG_DATA_HOME",
            "XDG_STATE_HOME",
            "PROMPTBRANCH_PROFILE_DIR",
            "PROMPTBRANCH_PROJECT_STATE_HOME",
            "PROMPTBRANCH_PROJECT_CONFIG_HOME",
            "PROMPTBRANCH_PROJECT_CACHE_PATH",
        ],
        "stripped_env_prefixes": ["CHATGPT_"],
        "stripped_env_keys": [
            "PROMPTBRANCH_SERVICE_BASE_URL",
            "PROMPTBRANCH_SERVICE_PORT",
            "PROMPTBRANCH_SERVICE_IMAGE",
            "PROMPTBRANCH_SERVICE_IMAGE_TAG",
            "PROMPTBRANCH_ARTIFACT_SHA256",
            "PROMPTBRANCH_VERSION",
            "PROMPTBRANCH_LOCALHOST_BASE_URL",
            "PROMPTBRANCH_CONTAINER_ID",
            "PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_SEED_DIR",
            "PROMPTBRANCH_BROWSER_PROFILE_LOCK_WAIT_SECONDS",
            "PROMPTBRANCH_BROWSER_PROFILE_STALE_LOCK_SECONDS",
            "PROMPTBRANCH_SOURCE_MUTATION_PROFILE_WAIT_SECONDS",
            "PYTEST_ADDOPTS",
        ],
        "node_preflights": [],
    }
    completed_nodeids: list[str] = []
    failed_nodeids: list[str] = []
    timed_out_nodeids: list[str] = []
    nodeid_results: list[dict[str, Any]] = []
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []

    for index, nodeid in enumerate(nodeids, start=1):
        elapsed = time.monotonic() - started_monotonic
        remaining = timeout_seconds - elapsed
        if remaining <= 0:
            timed_out_nodeids.append(nodeid)
            return {
                "ok": False,
                "action": "release_validation_group",
                "status": "timeout",
                "group": group_name,
                "required": bool(spec.get("required")),
                "description": spec.get("description"),
                "command": command,
                "command_mode": "per_nodeid_progress",
                "environment_isolation": isolation_diagnostics,
                "started_at": started_at,
                "finished_at": utc_now(),
                "timeout_seconds": timeout_seconds,
                "active_nodeid": nodeid,
                "completed_nodeids": completed_nodeids,
                "failed_nodeids": failed_nodeids,
                "timed_out_nodeids": timed_out_nodeids,
                "nodeid_results": nodeid_results,
                "stdout_tail": _tail_text("\n".join(stdout_parts)),
                "stderr_tail": _tail_text("\n".join(stderr_parts)),
            }

        progress_line = (
            "release_validation_group_progress: "
            f"group={group_name} index={index}/{len(nodeids)} nodeid={nodeid}"
        )
        print(progress_line, flush=True)
        stdout_parts.append(progress_line)
        node_command = [*command_prefix, nodeid]
        node_started_at = utc_now()
        node_isolation_root = isolation_parent / f"node-{index:02d}"
        node_env = _release_validation_group_env(isolation_root=node_isolation_root, nodeid=nodeid)
        preflight = _release_validation_isolation_preflight(
            repo_path=repo_path,
            isolation_root=node_isolation_root,
            env=node_env,
            timeout_seconds=min(remaining, 10.0),
        )
        isolation_diagnostics["node_preflights"].append({"nodeid": nodeid, **preflight})
        if not preflight.get("ok"):
            return {
                "ok": False,
                "action": "release_validation_group",
                "status": "isolation_preflight_failed",
                "group": group_name,
                "required": bool(spec.get("required")),
                "description": spec.get("description"),
                "command": command,
                "command_mode": "per_nodeid_progress",
                "environment_isolation": isolation_diagnostics,
                "started_at": started_at,
                "finished_at": utc_now(),
                "timeout_seconds": timeout_seconds,
                "active_nodeid": nodeid,
                "completed_nodeids": completed_nodeids,
                "failed_nodeids": failed_nodeids,
                "timed_out_nodeids": timed_out_nodeids,
                "nodeid_results": nodeid_results,
                "stdout_tail": _tail_text("\n".join(stdout_parts)),
                "stderr_tail": _tail_text("\n".join(stderr_parts)),
            }
        remaining = timeout_seconds - (time.monotonic() - started_monotonic)
        if remaining <= 0:
            timed_out_nodeids.append(nodeid)
            return {
                "ok": False,
                "action": "release_validation_group",
                "status": "timeout",
                "group": group_name,
                "required": bool(spec.get("required")),
                "description": spec.get("description"),
                "command": command,
                "command_mode": "per_nodeid_progress",
                "environment_isolation": isolation_diagnostics,
                "started_at": started_at,
                "finished_at": utc_now(),
                "timeout_seconds": timeout_seconds,
                "active_nodeid": nodeid,
                "completed_nodeids": completed_nodeids,
                "failed_nodeids": failed_nodeids,
                "timed_out_nodeids": timed_out_nodeids,
                "nodeid_results": nodeid_results,
                "stdout_tail": _tail_text("\n".join(stdout_parts)),
                "stderr_tail": _tail_text("\n".join(stderr_parts)),
            }
        try:
            completed = subprocess.run(
                node_command,
                cwd=str(repo_path),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=max(0.1, remaining),
                check=False,
                env=node_env,
            )
        except subprocess.TimeoutExpired as exc:
            timed_out_nodeids.append(nodeid)
            stdout_text = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr_text = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
            stdout_parts.append(stdout_text)
            stderr_parts.append(stderr_text)
            nodeid_results.append({
                "nodeid": nodeid,
                "status": "timeout",
                "ok": False,
                "command": node_command,
                "started_at": node_started_at,
                "finished_at": utc_now(),
                "timeout_seconds": max(0.1, remaining),
                "stdout_tail": _tail_text(stdout_text),
                "stderr_tail": _tail_text(stderr_text),
                "environment_isolation_preflight": preflight,
            })
            return {
                "ok": False,
                "action": "release_validation_group",
                "status": "timeout",
                "group": group_name,
                "required": bool(spec.get("required")),
                "description": spec.get("description"),
                "command": command,
                "command_mode": "per_nodeid_progress",
                "environment_isolation": isolation_diagnostics,
                "started_at": started_at,
                "finished_at": utc_now(),
                "timeout_seconds": timeout_seconds,
                "active_nodeid": nodeid,
                "completed_nodeids": completed_nodeids,
                "failed_nodeids": failed_nodeids,
                "timed_out_nodeids": timed_out_nodeids,
                "nodeid_results": nodeid_results,
                "stdout_tail": _tail_text("\n".join(stdout_parts)),
                "stderr_tail": _tail_text("\n".join(stderr_parts)),
            }

        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
        stdout_parts.append(stdout_text)
        stderr_parts.append(stderr_text)
        node_ok = completed.returncode == 0
        if node_ok:
            completed_nodeids.append(nodeid)
        else:
            failed_nodeids.append(nodeid)
        nodeid_results.append({
            "nodeid": nodeid,
            "status": "passed" if node_ok else "failed",
            "ok": node_ok,
            "command": node_command,
            "returncode": completed.returncode,
            "started_at": node_started_at,
            "finished_at": utc_now(),
            "stdout_tail": _tail_text(stdout_text),
            "stderr_tail": _tail_text(stderr_text),
            "environment_isolation_preflight": preflight,
        })
        if not node_ok:
            return {
                "ok": False,
                "action": "release_validation_group",
                "status": "failed",
                "group": group_name,
                "required": bool(spec.get("required")),
                "description": spec.get("description"),
                "command": command,
                "command_mode": "per_nodeid_progress",
                "environment_isolation": isolation_diagnostics,
                "returncode": completed.returncode,
                "started_at": started_at,
                "finished_at": utc_now(),
                "timeout_seconds": timeout_seconds,
                "active_nodeid": nodeid,
                "completed_nodeids": completed_nodeids,
                "failed_nodeids": failed_nodeids,
                "timed_out_nodeids": timed_out_nodeids,
                "nodeid_results": nodeid_results,
                "stdout_tail": _tail_text("\n".join(stdout_parts)),
                "stderr_tail": _tail_text("\n".join(stderr_parts)),
            }

    return {
        "ok": True,
        "action": "release_validation_group",
        "status": "passed",
        "group": group_name,
        "required": bool(spec.get("required")),
        "description": spec.get("description"),
        "command": command,
        "command_mode": "per_nodeid_progress",
        "environment_isolation": isolation_diagnostics,
        "returncode": 0,
        "started_at": started_at,
        "finished_at": utc_now(),
        "timeout_seconds": timeout_seconds,
        "completed_nodeids": completed_nodeids,
        "failed_nodeids": failed_nodeids,
        "timed_out_nodeids": timed_out_nodeids,
        "nodeid_results": nodeid_results,
        "stdout_tail": _tail_text("\n".join(stdout_parts)),
        "stderr_tail": _tail_text("\n".join(stderr_parts)),
    }


def _run_release_validation_group(group_name: str, spec: dict[str, Any], *, repo_path: Path, timeout_seconds: float = 600.0) -> dict[str, Any]:
    try:
        timeout_seconds = float(spec.get("timeout_seconds", timeout_seconds))
    except (TypeError, ValueError):
        timeout_seconds = 600.0
    command = _resolve_release_validation_command(spec.get("command") or [])
    if not command:
        return {
            "ok": False,
            "action": "release_validation_group",
            "status": "missing_command",
            "group": group_name,
            "required": bool(spec.get("required")),
            "description": spec.get("description"),
        }
    started_at = utc_now()
    if bool(spec.get("nodeid_progress")):
        progress_result = _run_release_validation_group_with_nodeid_progress(
            group_name,
            spec,
            repo_path=repo_path,
            command=command,
            timeout_seconds=timeout_seconds,
            started_at=started_at,
        )
        if progress_result is not None:
            return progress_result

    isolation_root = Path(tempfile.mkdtemp(prefix=f"pb-release-validation-{group_name}-"))
    env = _release_validation_group_env(isolation_root=isolation_root)
    preflight = _release_validation_isolation_preflight(
        repo_path=repo_path,
        isolation_root=isolation_root,
        env=env,
        timeout_seconds=min(timeout_seconds, 10.0),
    )
    isolation_diagnostics = {
        "enabled": True,
        "root": str(isolation_root),
        "mode": "explicit_runtime_path_authority",
        "preflight": preflight,
    }
    if not preflight.get("ok"):
        return {
            "ok": False,
            "action": "release_validation_group",
            "status": "isolation_preflight_failed",
            "group": group_name,
            "required": bool(spec.get("required")),
            "description": spec.get("description"),
            "command": command,
            "environment_isolation": isolation_diagnostics,
            "started_at": started_at,
            "finished_at": utc_now(),
            "timeout_seconds": timeout_seconds,
            "stdout_tail": "",
            "stderr_tail": _tail_text(str(preflight.get("stderr_tail") or "")),
        }
    try:
        completed = subprocess.run(
            command,
            cwd=str(repo_path),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
        ok = completed.returncode == 0
        return {
            "ok": ok,
            "action": "release_validation_group",
            "status": "passed" if ok else "failed",
            "group": group_name,
            "required": bool(spec.get("required")),
            "description": spec.get("description"),
            "command": command,
            "environment_isolation": isolation_diagnostics,
            "returncode": completed.returncode,
            "started_at": started_at,
            "finished_at": utc_now(),
            "timeout_seconds": timeout_seconds,
            "stdout_tail": _tail_text(completed.stdout or ""),
            "stderr_tail": _tail_text(completed.stderr or ""),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "action": "release_validation_group",
            "status": "timeout",
            "group": group_name,
            "required": bool(spec.get("required")),
            "description": spec.get("description"),
            "command": command,
            "environment_isolation": isolation_diagnostics,
            "started_at": started_at,
            "finished_at": utc_now(),
            "timeout_seconds": timeout_seconds,
            "stdout_tail": _tail_text((exc.stdout or "") if isinstance(exc.stdout, str) else ""),
            "stderr_tail": _tail_text((exc.stderr or "") if isinstance(exc.stderr, str) else ""),
        }


def run_release_validation_groups(
    *,
    repo_path: Path | str = ".",
    progress: TestProgressLedger | None = None,
    fail_fast: bool = False,
) -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    if os.environ.get(RELEASE_VALIDATION_SKIP_DUPLICATE_ENV) == "1":
        if progress is not None:
            for group_name in RELEASE_VALIDATION_GROUPS:
                progress.finish(
                    f"validation.{group_name}",
                    ok=True,
                    skipped=True,
                    skip_reason="duplicate_already_passed",
                )
        groups = {
            group_name: {
                "ok": True,
                "action": "release_validation_group",
                "status": "skipped_duplicate_already_passed",
                "group": group_name,
                "required": bool(spec.get("required")),
                "description": spec.get("description"),
                "command": _resolve_release_validation_command(spec.get("command") or []),
                "skip_reason": "release_validation_groups_already_passed_in_primary_run_all_transport",
            }
            for group_name, spec in RELEASE_VALIDATION_GROUPS.items()
        }
        return {
            "ok": True,
            "action": "release_validation_groups",
            "status": "skipped_duplicate_already_passed",
            "required_group_count": len(RELEASE_VALIDATION_GROUPS),
            "missing_required_groups": [],
            "duplicate_skip": True,
            "groups": groups,
        }
    runner_preflight = release_validation_runner_preflight()
    if not runner_preflight.get("ok"):
        groups = {}
        for group_name, spec in RELEASE_VALIDATION_GROUPS.items():
            groups[group_name] = {
                "ok": False,
                "action": "release_validation_group",
                "status": "skipped_runner_preflight_failed",
                "group": group_name,
                "required": bool(spec.get("required")),
                "description": spec.get("description"),
                "skip_reason": "release validation runner preflight failed",
            }
            if progress is not None:
                progress.finish(
                    f"validation.{group_name}",
                    ok=False,
                    skipped=True,
                    skip_reason="runner_preflight_failed",
                )
        missing_required = [
            name for name, spec in RELEASE_VALIDATION_GROUPS.items() if bool(spec.get("required"))
        ]
        return {
            "ok": False,
            "action": "release_validation_groups",
            "status": "runner_preflight_failed",
            "required_group_count": len(RELEASE_VALIDATION_GROUPS),
            "missing_required_groups": missing_required,
            "runner_preflight": runner_preflight,
            "groups": groups,
        }

    groups: dict[str, dict[str, Any]] = {}
    group_items = list(RELEASE_VALIDATION_GROUPS.items())
    for index, (group_name, spec) in enumerate(group_items):
        unit = f"validation.{group_name}"
        if progress is not None:
            progress.start(unit)
        result = _run_release_validation_group(group_name, spec, repo_path=root)
        groups[group_name] = result
        if progress is not None:
            progress.finish(unit, ok=bool(result.get("ok")))
        if fail_fast and bool(spec.get("required")) and not bool(result.get("ok")):
            for remaining_name, remaining_spec in group_items[index + 1:]:
                groups[remaining_name] = {
                    "ok": False,
                    "action": "release_validation_group",
                    "status": "skipped_fail_fast",
                    "group": remaining_name,
                    "required": bool(remaining_spec.get("required")),
                    "description": remaining_spec.get("description"),
                    "skip_reason": f"required group {group_name} failed",
                }
                if progress is not None:
                    progress.finish(
                        f"validation.{remaining_name}",
                        ok=False,
                        skipped=True,
                        skip_reason="fail_fast",
                    )
            break
    missing_required = [name for name, payload in groups.items() if bool(payload.get("required")) and not bool(payload.get("ok"))]
    return {
        "ok": not missing_required,
        "action": "release_validation_groups",
        "status": "passed" if not missing_required else "failed",
        "required_group_count": len(RELEASE_VALIDATION_GROUPS),
        "missing_required_groups": missing_required,
        "runner_preflight": runner_preflight,
        "groups": groups,
    }


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
    ask_conversation_url: Optional[str] = None,
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
    fail_fast: bool = False,
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
        'ask_conversation_url': ask_conversation_url,
        'json_out': json_out,
        'project_list_debug_scroll_rounds': project_list_debug_scroll_rounds,
        'project_list_debug_wait_ms': project_list_debug_wait_ms,
        'project_list_debug_manual_pause': project_list_debug_manual_pause,
        'service_base_url': service_base_url,
        'service_token': service_token,
        'service_timeout_seconds': service_timeout_seconds,
        'clear_singleton_locks': clear_singleton_locks,
        'rate_limit_safe': rate_limit_safe,
        'fail_fast': fail_fast,
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


def _read_promptbranch_version_file(repo_path: Path) -> str | None:
    try:
        return _extract_package_version_constant((repo_path / "promptbranch_version.py").read_text(encoding="utf-8"))
    except OSError:
        return None


def _extract_compose_service_image_version(source: str) -> str | None:
    """Return the declared/default promptbranch-service image tag from Compose YAML.

    Supports both the single-default runtime form::

        image: promptbranch-service:0.1.1.1

    and the historical parameterized v0.1.1 form::

        image: ${PROMPTBRANCH_SERVICE_IMAGE:-promptbranch-service:${PROMPTBRANCH_SERVICE_IMAGE_TAG:-0.1.1}}

    The validator only needs the default declared version. Runtime overrides are
    intentionally not treated as source version declarations.
    """
    match = re.search(r"^\s*image:\s*promptbranch-service:([^\s#]+)", source, flags=re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"\'') or None
    match = re.search(r"promptbranch-service:\$\{PROMPTBRANCH_SERVICE_IMAGE_TAG:-([^}]+)\}", source)
    if match:
        return match.group(1).strip().strip('"\'') or None
    return None


def _read_compose_service_image_version(repo_path: Path) -> str | None:
    try:
        return _extract_compose_service_image_version((repo_path / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8"))
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
        "conversation_history_fetch_attempt_count": 0,
        "conversation_history_fetch_skipped_count": 0,
        "conversation_history_cooldown_skip_count": 0,
        "navigation_noop_skip_count": 0,
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
    for key in (
        "conversation_history_fetch_attempt_count",
        "conversation_history_fetch_skipped_count",
        "conversation_history_cooldown_skip_count",
        "navigation_noop_skip_count",
    ):
        try:
            target[key] = int(target.get(key) or 0) + int(telemetry.get(key) or 0)
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


def classify_rate_limit_summary(telemetry: Any, *, suite_ok: bool | None = None) -> dict[str, Any]:
    """Return a compact operator-facing rate-limit classification.

    The full telemetry can be large and noisy. This summary preserves the
    operational decision: whether rate limiting was absent, recovered from, or
    excessive enough to make the live validation result fragile.
    """

    data = telemetry if isinstance(telemetry, dict) else {}
    try:
        event_count = int(data.get("event_count") or len(data.get("service_rate_limit_events") or []))
    except (TypeError, ValueError):
        event_count = 0
    try:
        cooldown_total = float(data.get("cooldown_wait_seconds_total") or 0.0)
    except (TypeError, ValueError):
        cooldown_total = 0.0
    try:
        cooldown_count = int(data.get("cooldown_wait_count") or 0)
    except (TypeError, ValueError):
        cooldown_count = 0
    try:
        planned_total = float(data.get("planned_cooldown_wait_seconds_total") or 0.0)
    except (TypeError, ValueError):
        planned_total = 0.0
    try:
        planned_count = int(data.get("planned_cooldown_wait_count") or 0)
    except (TypeError, ValueError):
        planned_count = 0
    modal = bool(data.get("rate_limit_modal_detected"))
    history_429 = bool(data.get("conversation_history_429_seen"))

    observed = modal or history_429 or event_count > 0 or cooldown_count > 0
    excessive = cooldown_total >= 900.0 or cooldown_count >= 8 or event_count >= 30
    if not observed:
        status = "none"
        blocking = False
        recommendation = "No ChatGPT rate-limit evidence observed."
    elif suite_ok is False:
        status = "rate_limited_failed"
        blocking = True
        recommendation = "Live validation failed with rate-limit evidence; rerun later or reduce conversation-history enumeration."
    elif excessive:
        status = "rate_limited_excessive"
        blocking = False
        recommendation = "Suite recovered, but rate-limit pressure was excessive; reduce history enumeration or increase live-test pacing before relying on repeated runs."
    elif cooldown_count > 0:
        status = "rate_limited_recovered"
        blocking = False
        recommendation = "Suite recovered after persisted cooldown waits."
    else:
        status = "observed_no_cooldown"
        blocking = False
        recommendation = "Rate-limit evidence was observed without a recorded cooldown wait."

    return {
        "status": status,
        "blocking": blocking,
        "event_count": event_count,
        "rate_limit_modal_detected": modal,
        "conversation_history_429_seen": history_429,
        "cooldown_wait_seconds_total": round(cooldown_total, 3),
        "cooldown_wait_count": cooldown_count,
        "planned_cooldown_wait_seconds_total": round(planned_total, 3),
        "planned_cooldown_wait_count": planned_count,
        "recommendation": recommendation,
    }



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


def _declared_exact_dependency_versions(repo_path: Path, names: Sequence[str]) -> dict[str, str]:
    try:
        data = _load_pyproject_from_text((repo_path / "pyproject.toml").read_text(encoding="utf-8"))
    except OSError:
        return {}
    dependencies = ((data.get("project") or {}).get("dependencies") or []) if isinstance(data, dict) else []
    wanted = {str(name).strip().lower() for name in names if str(name).strip()}
    resolved: dict[str, str] = {}
    for raw in dependencies:
        text = str(raw).strip()
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)", text)
        if not match:
            continue
        name = match.group(1).lower()
        if name in wanted:
            resolved[name] = match.group(2)
    return resolved


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
        _version_observation("promptbranch_version.py.PACKAGE_VERSION", _read_promptbranch_version_file(root)),
        _version_observation("runtime.promptbranch_version.PACKAGE_VERSION", PACKAGE_VERSION),
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
    expected_dependencies = _declared_exact_dependency_versions(root, ("fastapi", "starlette", "pytest"))
    if not declared:
        return {"ok": False, "action": "package_import_smoke", "status": "pyproject_missing_or_unreadable", "repo_path": str(root), "modules": modules}
    executable = python_executable or sys.executable
    code = "\n".join([
        "import contextlib",
        "import importlib",
        "import io",
        "import json",
        "import os",
        "import sys",
        "modules = json.loads(sys.argv[1])",
        "expected_version = sys.argv[2] or None",
        "expected_python = os.path.abspath(sys.argv[3])",
        "expected_dependencies = json.loads(sys.argv[4])",
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
        "actual_python = os.path.abspath(sys.executable)",
        "expected_prefix = os.path.dirname(os.path.dirname(expected_python))",
        "runtime_identity = {'ok': actual_python == expected_python and os.path.realpath(sys.prefix) == os.path.realpath(expected_prefix), 'expected_python': expected_python, 'actual_python': actual_python, 'expected_prefix': expected_prefix, 'actual_prefix': sys.prefix}",
        "dependency_observations = []",
        "dependency_mismatches = []",
        "try:",
        "    from importlib import metadata as dependency_metadata",
        "    for dependency_name, dependency_expected in sorted(expected_dependencies.items()):",
        "        try:",
        "            dependency_actual = dependency_metadata.version(dependency_name)",
        "        except Exception:",
        "            dependency_actual = None",
        "        row = {'name': dependency_name, 'expected': dependency_expected, 'actual': dependency_actual}",
        "        dependency_observations.append(row)",
        "        if dependency_actual != dependency_expected:",
        "            dependency_mismatches.append(row)",
        "except Exception as exc:",
        "    dependency_mismatches.append({'name': 'metadata', 'expected': expected_dependencies, 'actual': None, 'error': str(exc)})",
        "dependency_consistency = {'ok': not dependency_mismatches, 'expected': expected_dependencies, 'observations': dependency_observations, 'mismatches': dependency_mismatches}",
        "payload = {'imports': results, 'version_consistency': version_consistency, 'runtime_identity': runtime_identity, 'dependency_consistency': dependency_consistency}",
        "print(json.dumps(payload, ensure_ascii=False))",
        "sys.exit(0 if all(item.get('ok') for item in results) and version_consistency.get('ok') and runtime_identity.get('ok') and dependency_consistency.get('ok') else 1)",
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
        completed = subprocess.run([executable, "-c", code, json.dumps(modules), expected_version or "", str(Path(executable).expanduser().absolute()), json.dumps(expected_dependencies, sort_keys=True)], cwd=tmp, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
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
    runtime_identity = subprocess_payload.get("runtime_identity") if isinstance(subprocess_payload, dict) else None
    if not isinstance(runtime_identity, dict):
        runtime_identity = {"ok": False, "expected_python": str(Path(executable).expanduser().absolute()), "actual_python": None, "expected_prefix": None, "actual_prefix": None}
    dependency_consistency = subprocess_payload.get("dependency_consistency") if isinstance(subprocess_payload, dict) else None
    if not isinstance(dependency_consistency, dict):
        dependency_consistency = {"ok": False, "expected": expected_dependencies, "observations": [], "mismatches": [{"name": "dependency_runtime_payload", "expected": expected_dependencies, "actual": None}]}
    ok = completed.returncode == 0 and not failures and bool(version_consistency.get("ok")) and bool(runtime_identity.get("ok")) and bool(dependency_consistency.get("ok"))
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
        "runtime_identity": runtime_identity,
        "dependency_consistency": dependency_consistency,
        "expected_dependency_versions": expected_dependencies,
        "returncode": completed.returncode,
        "stdout_bytes": len(completed.stdout or ""),
        "stderr": completed.stderr[-4000:] if completed.stderr else "",
        "source_tree_masking_prevented": True,
    }



def _src_sync_dry_run_plan(*, repo_path: str | Path = ".", profile_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    profile_base = Path(profile_dir).expanduser() if profile_dir else root / ".pb_profile"
    registry = ArtifactRegistry(profile_base)
    try:
        plan, included = build_source_sync_preflight(
            root,
            output_dir=registry.artifact_dir,
            profile_dir=registry.profile_dir,
            project_url=None,
            upload_requested=False,
        )
    except ArtifactRegistryStateError as exc:
        return {
            "ok": False,
            "action": "src_sync_dry_run",
            "status": "preflight_failed",
            "registry_status": exc.status,
            "artifact_registry": exc.to_payload(action="artifact_registry"),
            "error": str(exc),
            "repo_path": str(root),
            "mutating_actions_executed": False,
        }
    except ValueError as exc:
        return {"ok": False, "action": "src_sync_dry_run", "status": "plan_failed", "error": str(exc), "repo_path": str(root), "mutating_actions_executed": False}
    preflight = plan["preflight"]
    return {
        "ok": True,
        "action": "src_sync_dry_run",
        "status": "planned",
        "repo_path": str(root),
        "mutating_actions_executed": False,
        "artifact": {**plan, "would_upload_source": False},
        "included_count": len(included),
        "registry_status": preflight["before_snapshot"]["artifact_registry"].get("registry_status"),
        "before_snapshot": preflight["before_snapshot"],
        "collateral_checks": preflight["collateral_checks"],
        "transaction_id": preflight["transaction_id"],
        "transaction_plan": {
            "transaction_id": preflight["transaction_id"],
            "would_package_repo_snapshot": True,
            "would_update_artifact_registry": True,
            "would_upload_project_source": False,
            "required_settle_conditions": [],
            "verification_plan": preflight["verification_plan"],
            "collateral_checks": preflight["collateral_checks"],
        },
    }



def _src_sync_upload_preflight_plan(*, repo_path: str | Path = ".", profile_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    profile_base = Path(profile_dir).expanduser() if profile_dir else root / ".pb_profile"
    registry = ArtifactRegistry(profile_base)
    project_url = "test://promptbranch-preflight-workspace"
    try:
        plan, included = build_source_sync_preflight(
            root,
            output_dir=registry.artifact_dir,
            profile_dir=registry.profile_dir,
            project_url=project_url,
            upload_requested=True,
        )
    except ArtifactRegistryStateError as exc:
        return {
            "ok": False,
            "action": "src_sync_upload_preflight",
            "status": "preflight_failed",
            "registry_status": exc.status,
            "artifact_registry": exc.to_payload(action="artifact_registry"),
            "error": str(exc),
            "repo_path": str(root),
            "mutating_actions_executed": False,
            "project_source_mutated": False,
        }
    except ValueError as exc:
        return {"ok": False, "action": "src_sync_upload_preflight", "status": "plan_failed", "error": str(exc), "repo_path": str(root), "mutating_actions_executed": False, "project_source_mutated": False}
    preflight = plan["preflight"]
    transaction_id = preflight["transaction_id"]
    return {
        "ok": True,
        "action": "src_sync_upload_preflight",
        "status": "upload_confirmation_required",
        "repo_path": str(root),
        "mutating_actions_executed": False,
        "project_source_mutated": False,
        "artifact": {**plan, "would_upload_source": True},
        "included_count": len(included),
        "registry_status": preflight["before_snapshot"]["artifact_registry"].get("registry_status"),
        "transaction_id": transaction_id,
        "confirmation": {
            "required": True,
            "confirm_flag": "--confirm-upload",
            "confirm_transaction_id_flag": "--confirm-transaction-id",
            "confirm_command": f"pb src sync {root} --upload --confirm-upload --confirm-transaction-id {transaction_id} --json",
        },
        "collateral_checks": preflight["collateral_checks"],
        "verification_plan": preflight["verification_plan"],
    }



def _artifact_roundtrip_reply_text(reply: dict[str, Any]) -> str:
    return f"{BEGIN_REPLY_MARKER}\n" + json.dumps(reply, indent=2, ensure_ascii=False) + f"\n{END_REPLY_MARKER}"


def _artifact_roundtrip_base_reply(*, run_id: str, output_filename: str, output_url: str) -> dict[str, Any]:
    return {
        "schema": "promptbranch.ask.reply",
        "schema_version": "1.0",
        "request_id": f"artifact-roundtrip-{run_id}",
        "correlation_id": f"artifact-roundtrip-{run_id}",
        "status": "completed",
        "result_type": "diagnostic",
        "summary": "Synthetic non-visual artifact roundtrip reply for deterministic Promptbranch testing.",
        "baseline": {
            "input_artifact": "synthetic-input.zip",
            "input_version": "v0.0.0",
            "output_artifact": output_filename,
            "output_version": "v0.0.0",
            "release_type": "artifact_roundtrip_smoke",
        },
        "changes": [
            {"path": "output.txt", "kind": "generated", "summary": "Synthetic smoke output file."}
        ],
        "artifacts": [
            {
                "kind": "zip",
                "filename": output_filename,
                "version": None,
                "role": "smoke_test_artifact",
                "download": {
                    "available": True,
                    "link_text": output_filename,
                    "url": output_url,
                    "url_temporary": False,
                    "requires_browser_context": False,
                },
            }
        ],
        "validation": {"claimed": ["synthetic local ZIP created"], "not_claimed": ["ChatGPT browser/UI path"]},
        "next_step": {"operator_action": "none", "recommended_command": "pb test artifact-roundtrip --json"},
        "confidence": "high",
    }


def _write_artifact_roundtrip_zip(path: Path, *, entry: str, content: str, wrapper: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    arcname = f"wrapper/{entry}" if wrapper else entry
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(arcname, content)


def _verify_artifact_roundtrip_content(zip_path: Path, *, expected_entry: str, expected_content: str) -> dict[str, Any]:
    zip_check = verify_zip_artifact(zip_path)
    content_check: dict[str, Any] = {
        "expected_entry": expected_entry,
        "expected_content_sha256": None,
        "actual_content_sha256": None,
        "expected_size": len(expected_content.encode("utf-8")),
        "actual_size": None,
        "content_matches": False,
    }
    if not zip_check.get("ok"):
        return {**zip_check, "content_check": content_check, "status": "zip_verification_failed"}
    try:
        with zipfile.ZipFile(zip_path) as archive:
            actual = archive.read(expected_entry).decode("utf-8")
    except KeyError:
        return {**zip_check, "ok": False, "status": "expected_entry_missing", "content_check": content_check}
    except (UnicodeDecodeError, zipfile.BadZipFile) as exc:
        return {**zip_check, "ok": False, "status": "expected_entry_unreadable", "error": str(exc), "content_check": content_check}
    content_check.update(
        {
            "expected_content_sha256": __import__("hashlib").sha256(expected_content.encode("utf-8")).hexdigest(),
            "actual_content_sha256": __import__("hashlib").sha256(actual.encode("utf-8")).hexdigest(),
            "actual_size": len(actual.encode("utf-8")),
            "content_matches": actual == expected_content,
        }
    )
    if actual != expected_content:
        return {**zip_check, "ok": False, "status": "expected_content_mismatch", "content_check": content_check}
    return {**zip_check, "ok": True, "status": "smoke_zip_verified", "content_check": content_check}


def artifact_roundtrip_smoke(*, repo_path: str | Path = ".", profile_dir: str | Path | None = None, run_id: str | None = None) -> dict[str, Any]:
    """Run a deterministic, non-browser artifact protocol/intake smoke test.

    This intentionally does not call ChatGPT, launch a browser, require auth, or
    mutate Project Sources.  It proves the host-side protocol path that must be
    safe enough for the default full suite: reply parsing, candidate selection,
    local artifact materialization, ZIP hygiene/smoke verification, and fail-closed
    negative cases.
    """

    root = Path(repo_path).expanduser().resolve()
    version = _read_version(root)
    safe_run_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(run_id or "").strip()).strip("._-")
    if not safe_run_id:
        safe_run_id = "deterministic"
    profile_root = Path(profile_dir).expanduser().resolve() if profile_dir else root / ".pb_profile"
    work_dir = profile_root / "test_artifact_roundtrip" / safe_run_id
    work_dir.mkdir(parents=True, exist_ok=True)
    expected_entry = "output.txt"
    expected_content = f"PB_ARTIFACT_ROUNDTRIP_OK_{safe_run_id}"
    output_filename = f"pb_artifact_roundtrip_{safe_run_id}.zip"
    source_zip = work_dir / output_filename
    inbox_zip = work_dir / "artifact_inbox" / output_filename
    steps: list[dict[str, Any]] = []

    _write_artifact_roundtrip_zip(source_zip, entry=expected_entry, content=expected_content)
    create_payload = {
        "ok": source_zip.is_file(),
        "action": "artifact_roundtrip_create_zip",
        "status": "created" if source_zip.is_file() else "create_failed",
        "path": str(source_zip),
        "filename": output_filename,
        "sha256": sha256_file(source_zip) if source_zip.is_file() else None,
        "size_bytes": source_zip.stat().st_size if source_zip.is_file() else None,
    }
    steps.append(_step("create_synthetic_zip", create_payload))

    reply = _artifact_roundtrip_base_reply(run_id=safe_run_id, output_filename=output_filename, output_url=source_zip.as_uri())
    parsed = parse_promptbranch_reply(_artifact_roundtrip_reply_text(reply))
    steps.append(_step("parse_valid_reply", parsed))

    classification = classify_artifact_candidates(
        parsed.get("artifact_candidates") if isinstance(parsed.get("artifact_candidates"), list) else [],
        expected_filename=output_filename,
    )
    steps.append(_step("classify_expected_candidate", classification))

    selected = classification.get("selected_candidate") if isinstance(classification.get("selected_candidate"), dict) else {}
    download_url = (selected.get("download") or {}).get("url") if isinstance(selected.get("download"), dict) else None
    download_payload: dict[str, Any]
    try:
        if not isinstance(download_url, str) or not download_url.startswith("file://"):
            raise ValueError("selected candidate does not expose a deterministic file:// URL")
        src = Path(__import__("urllib.parse").parse.urlparse(download_url).path)
        inbox_zip.parent.mkdir(parents=True, exist_ok=True)
        inbox_zip.write_bytes(src.read_bytes())
        download_payload = {
            "ok": True,
            "action": "artifact_roundtrip_local_download",
            "status": "downloaded",
            "download_url": download_url,
            "path": str(inbox_zip),
            "sha256": sha256_file(inbox_zip),
            "size_bytes": inbox_zip.stat().st_size,
        }
    except Exception as exc:
        download_payload = {"ok": False, "action": "artifact_roundtrip_local_download", "status": "download_failed", "download_url": download_url, "error": str(exc)}
    steps.append(_step("local_artifact_download", download_payload))

    verification = _verify_artifact_roundtrip_content(inbox_zip, expected_entry=expected_entry, expected_content=expected_content)
    steps.append(_step("smoke_zip_verify", verification))

    malformed = parse_promptbranch_reply(f"{BEGIN_REPLY_MARKER}\n{{bad json\n{END_REPLY_MARKER}")
    steps.append(_step("malformed_reply_fails_closed", malformed, expected_failure=True, expected_status="reply_schema_invalid"))

    wrong_name_reply = _artifact_roundtrip_base_reply(run_id=safe_run_id, output_filename="wrong_artifact.zip", output_url=source_zip.as_uri())
    wrong_name_parsed = parse_promptbranch_reply(_artifact_roundtrip_reply_text(wrong_name_reply))
    wrong_name = classify_artifact_candidates(
        wrong_name_parsed.get("artifact_candidates") if isinstance(wrong_name_parsed.get("artifact_candidates"), list) else [],
        expected_filename=output_filename,
    )
    steps.append(_step("wrong_filename_fails_closed", wrong_name, expected_failure=True, expected_status="artifact_wrong_filename"))

    wrong_content_zip = work_dir / "wrong_content.zip"
    _write_artifact_roundtrip_zip(wrong_content_zip, entry=expected_entry, content=expected_content + "_WRONG")
    wrong_content = _verify_artifact_roundtrip_content(wrong_content_zip, expected_entry=expected_entry, expected_content=expected_content)
    steps.append(_step("wrong_content_fails_closed", wrong_content, expected_failure=True, expected_status="expected_content_mismatch"))

    wrapper_zip = work_dir / "wrapper_folder.zip"
    _write_artifact_roundtrip_zip(wrapper_zip, entry=expected_entry, content=expected_content, wrapper=True)
    wrapper_check = _verify_artifact_roundtrip_content(wrapper_zip, expected_entry=expected_entry, expected_content=expected_content)
    steps.append(_step("wrapper_folder_fails_closed", wrapper_check, expected_failure=True, expected_status="zip_verification_failed"))

    ok = all(bool(step.get("ok")) for step in steps)
    failed_step = next((step for step in steps if not bool(step.get("ok"))), None)
    return {
        "ok": ok,
        "action": "test_artifact_roundtrip",
        "profile": "artifact-roundtrip",
        "status": "verified" if ok else (failed_step.get("status") if failed_step else "failed"),
        "repo_path": str(root),
        "version": version,
        "run_id": safe_run_id,
        "work_dir": str(work_dir),
        "browser_required": False,
        "chatgpt_required": False,
        "network_required": False,
        "docker_safe": True,
        "mutating_actions_executed": False,
        "project_source_mutated": False,
        "artifact_registry_updated": False,
        "expected_output_filename": output_filename,
        "expected_entry": expected_entry,
        "step_count": len(steps),
        "failure_count": len([step for step in steps if not bool(step.get("ok"))]),
        "steps": steps,
        "failed_step": failed_step,
        "safety": {
            "browser_required": False,
            "write_tools_blocked": True,
            "source_or_artifact_mutation_allowed": False,
            "uses_synthetic_reply": True,
        },
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
            names = archive.namelist()
            bad_entries = release_entry_hygiene_violations(names)
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



def _suite_failed_steps(section_name: str, section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict):
        return []
    failures: list[dict[str, Any]] = []
    for step_key, scope in (("steps", "main"), ("cleanup_steps", "cleanup")):
        steps = section.get(step_key)
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict) or bool(step.get("ok")):
                continue
            details = step.get("details") if isinstance(step.get("details"), dict) else {}
            payload = step.get("payload") if isinstance(step.get("payload"), dict) else {}
            status = step.get("status") or details.get("status") or payload.get("status") or details.get("error_type")
            if status in EXPECTED_NON_FAILURE_STATUSES:
                continue
            failures.append({
                "section": section_name,
                "scope": scope,
                "name": step.get("name"),
                "status": status,
                "diagnostic": details.get("error") or payload.get("error") or details.get("diagnostic") or payload.get("diagnostic"),
            })
    return failures


def _attach_suite_failure_summary(summary: dict[str, Any], section_name: str) -> dict[str, Any]:
    failures = _suite_failed_steps(section_name, summary)
    summary["failure_count"] = len(failures)
    summary["failed_steps"] = failures
    return summary

def _run_agent_profile_sync(*, repo_path: str | Path = ".", profile_dir: str | Path | None = None, package_zip: str | None = None, progress: TestProgressLedger | None = None, fail_fast: bool = False) -> dict[str, Any]:
    root = Path(repo_path).expanduser().resolve()
    steps: list[dict[str, Any]] = ProgressStepList(progress=progress, prefix="agent")
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
    steps.append(_step("artifact_roundtrip", artifact_roundtrip_smoke(repo_path=root, profile_dir=profile_dir)))
    steps.append(_step("src_sync_dry_run_plan", _src_sync_dry_run_plan(repo_path=root, profile_dir=profile_dir)))
    steps.append(_step("src_sync_upload_preflight_plan", _src_sync_upload_preflight_plan(repo_path=root, profile_dir=profile_dir)))
    release_validation = run_release_validation_groups(repo_path=root, progress=progress, fail_fast=fail_fast)
    steps.append(_step("release_validation_groups", release_validation))
    steps.append(_step("compileall", release_validation.get("groups", {}).get("compileall", {})))
    if fail_fast and not bool(release_validation.get("ok")):
        if progress is not None:
            progress.finish(
                "agent.package_hygiene",
                ok=False,
                skipped=True,
                skip_reason="fail_fast",
            )
        steps.append(_step("package_hygiene", {
            "ok": False,
            "action": "package_hygiene",
            "status": "skipped_fail_fast",
            "skip_reason": "required release-validation group failed",
        }))
    else:
        steps.append(_step("package_hygiene", _package_hygiene(package_zip, repo_path=root)))

    ok = all(bool(step.get("ok")) for step in steps)
    return {
        "ok": ok,
        "schema": TEST_SUITE_REPORT_SCHEMA,
        "schema_version": TEST_SUITE_REPORT_SCHEMA_VERSION,
        "action": "test_suite",
        "profile": "agent",
        "repo_path": str(root),
        "version": _read_version(root),
        "steps": steps,
        "artifacts": artifacts,
        "release_validation_groups": release_validation,
        "safety": {
            "browser_required": False,
            "write_tools_blocked": True,
            "model_has_execution_authority": False,
            "source_or_artifact_mutation_allowed": False,
        },
        "rate_limit_telemetry": _empty_rate_limit_telemetry(),
        "rate_limit_summary": classify_rate_limit_summary(_empty_rate_limit_telemetry(), suite_ok=ok),
    }


async def run_test_suite_async(**kwargs: Any) -> dict[str, Any]:
    profile = str(kwargs.pop("profile", "browser") or "browser").strip().lower()
    repo_path = kwargs.pop("path", ".")
    package_zip = kwargs.pop("package_zip", None)
    fail_fast = bool(kwargs.pop("fail_fast", False))
    progress_enabled = bool(kwargs.pop("progress", True))
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
            "conversation_history_fetch_attempt_count",
            "conversation_history_fetch_skipped_count",
            "conversation_history_cooldown_skip_count",
            "navigation_noop_skip_count",
            "service_rate_limit_events",
        ],
        "operator_message": "If ChatGPT shows 'You're making requests too quickly', the live browser profile will honor persisted cooldowns and report rate-limit telemetry in the suite JSON.",
    }

    validation_units = tuple(f"validation.{name}" for name in RELEASE_VALIDATION_GROUPS)
    agent_units = tuple(f"agent.{name}" for name in AGENT_PROGRESS_STEP_NAMES)
    known_validation_skips = (
        validation_units if os.environ.get(RELEASE_VALIDATION_SKIP_DUPLICATE_ENV) == "1" else ()
    )

    if profile == "agent":
        progress = TestProgressLedger(
            (*agent_units, *validation_units),
            enabled=progress_enabled,
            known_skipped_units=known_validation_skips,
        )
        progress.announce("agent")
        summary = _run_agent_profile_sync(
            repo_path=repo_path,
            profile_dir=kwargs.get("profile_dir"),
            package_zip=package_zip,
            progress=progress,
            fail_fast=fail_fast,
        )
        _attach_suite_failure_summary(summary, "agent")
        summary["rate_limit_strategy"] = {**rate_limit_strategy, "browser_required": False}
        progress.finish_summary()
        summary["progress"] = {"enabled": progress_enabled, "fail_fast": fail_fast, **progress.snapshot()}
        return summary

    browser_args = build_test_suite_namespace(**kwargs, rate_limit_safe=rate_limit_safe, fail_fast=fail_fast)
    selection = resolve_step_selection(
        only_values=browser_args.only,
        skip_values=browser_args.skip,
        keep_project=browser_args.keep_project,
    )
    browser_units = tuple(f"browser.{name}" for name in selection.enabled_steps)
    all_units = browser_units if profile == "browser" else (*browser_units, *agent_units, *validation_units)
    progress = TestProgressLedger(
        all_units,
        enabled=progress_enabled,
        known_skipped_units=known_validation_skips,
    )

    def browser_progress_callback(*, event: str, step_name: str, ok: bool | None = None, duration_seconds: float = 0.0) -> None:
        canonical = "task_message_flow" if step_name.startswith("task_message_flow.") else step_name
        unit = f"browser.{canonical}"
        if unit not in progress.states:
            return
        if event == "started":
            progress.start(unit)
            return
        if event != "finished":
            return
        if ok is False:
            progress.finish(unit, ok=False, duration_seconds=duration_seconds)
            return
        if step_name == canonical:
            progress.finish(unit, ok=True, duration_seconds=duration_seconds)

    setattr(browser_args, "_progress_callback", browser_progress_callback)
    progress.announce("browser")
    browser_summary = await run_integration(browser_args)
    _attach_suite_failure_summary(browser_summary, "browser")
    browser_summary["rate_limit_telemetry"] = extract_rate_limit_telemetry(browser_summary)
    browser_summary["rate_limit_summary"] = classify_rate_limit_summary(browser_summary["rate_limit_telemetry"], suite_ok=bool(browser_summary.get("ok")))
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
        if fail_fast and not bool(browser_summary.get("ok")):
            progress.skip_pending(reason="browser_failure")
        progress.finish_summary()
        browser_summary["progress"] = {"enabled": progress_enabled, "fail_fast": fail_fast, **progress.snapshot()}
        return browser_summary

    if fail_fast and not bool(browser_summary.get("ok")):
        progress.skip_pending(reason="browser_failure")
        agent_summary = {
            "ok": False,
            "schema": TEST_SUITE_REPORT_SCHEMA,
        "schema_version": TEST_SUITE_REPORT_SCHEMA_VERSION,
        "action": "test_suite",
            "profile": "agent",
            "status": "skipped_fail_fast",
            "failure_count": 0,
            "failed_steps": [],
            "steps": [],
            "release_validation_groups": {
                "ok": False,
                "status": "skipped_fail_fast",
                "groups": {},
                "missing_required_groups": list(RELEASE_VALIDATION_GROUPS),
            },
            "safety": {
                "write_tools_blocked": True,
                "model_has_execution_authority": False,
                "source_or_artifact_mutation_allowed": False,
            },
        }
    else:
        progress.announce("agent")
        agent_summary = _run_agent_profile_sync(
            repo_path=repo_path,
            profile_dir=kwargs.get("profile_dir"),
            package_zip=package_zip,
            progress=progress,
            fail_fast=fail_fast,
        )
    _attach_suite_failure_summary(agent_summary, "agent")
    full_failures = list(browser_summary.get("failed_steps") or []) + list(agent_summary.get("failed_steps") or [])
    full_ok = bool(browser_summary.get("ok")) and bool(agent_summary.get("ok"))
    progress.finish_summary()
    return {
        "ok": full_ok,
        "schema": TEST_SUITE_REPORT_SCHEMA,
        "schema_version": TEST_SUITE_REPORT_SCHEMA_VERSION,
        "action": "test_suite",
        "profile": "full",
        "version": _read_version(Path(repo_path).expanduser().resolve()),
        "browser": browser_summary,
        "agent": agent_summary,
        "failure_count": len(full_failures),
        "failed_steps": full_failures,
        "release_validation_groups": agent_summary.get("release_validation_groups"),
        "rate_limit_strategy": browser_summary.get("rate_limit_strategy"),
        "rate_limit_telemetry": browser_summary.get("rate_limit_telemetry", _empty_rate_limit_telemetry()),
        "rate_limit_summary": classify_rate_limit_summary(
            browser_summary.get("rate_limit_telemetry", _empty_rate_limit_telemetry()),
            suite_ok=full_ok,
        ),
        "progress": {
            "enabled": progress_enabled,
            "fail_fast": fail_fast,
            **progress.snapshot(),
        },
        "safety": {
            "write_tools_blocked": bool(agent_summary.get("safety", {}).get("write_tools_blocked")),
            "model_has_execution_authority": False,
            "source_or_artifact_mutation_allowed": False,
        },
    }


async def run_project_source_file_reliability_async(**kwargs: Any) -> dict[str, Any]:
    """Run only the live file-source staged-overwrite and removal-proof regressions.

    The scenarios use separate delete-frozen projects so a staged-overwrite
    failure cannot suppress removal-proof evidence.  This profile is a focused
    development preflight; it does not replace adoption-grade full_direct and
    full_localhost validation.
    """

    repo_path = Path(str(kwargs.pop("path", ".") or ".")).expanduser().resolve()
    kwargs.pop("package_zip", None)
    kwargs.pop("profile", None)
    kwargs.pop("rate_limit_safe", None)
    requested_project_name = str(kwargs.get("project_name") or "").strip()
    run_id = str(kwargs.get("run_id") or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    prefix = str(kwargs.get("project_name_prefix") or "itest-pb-source-reliability").strip()
    base_name = requested_project_name or f"{prefix}-{run_id}"

    scenario_specs = (
        (
            "staged_overwrite",
            ["project_ensure,source_add_file,source_overwrite_file"],
            False,
        ),
        (
            "removal_proof",
            ["project_ensure,source_add_file,source_remove_file"],
            True,
        ),
    )
    scenarios: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for scenario_name, only, strict_remove_ui in scenario_specs:
        scenario_kwargs = dict(kwargs)
        scenario_kwargs.update({
            "only": only,
            "skip": [],
            "keep_project": True,
            "strict_remove_ui": strict_remove_ui,
            "project_name": f"{base_name}-{scenario_name.replace('_', '-')}",
            "run_id": f"{run_id}-{scenario_name}",
            "json_out": None,
            "rate_limit_safe": False,
        })
        args = build_test_suite_namespace(**scenario_kwargs)
        summary = await run_integration(args)
        _attach_suite_failure_summary(summary, "browser")
        summary["rate_limit_telemetry"] = extract_rate_limit_telemetry(summary)
        summary["rate_limit_summary"] = classify_rate_limit_summary(
            summary["rate_limit_telemetry"],
            suite_ok=bool(summary.get("ok")),
        )
        scenarios[scenario_name] = summary
        if not summary.get("ok"):
            failures.extend(
                [
                    {**item, "scenario": scenario_name}
                    for item in list(summary.get("failed_steps") or [])
                    if isinstance(item, dict)
                ]
                or [{
                    "section": "browser",
                    "scope": scenario_name,
                    "name": scenario_name,
                    "status": "scenario_failed",
                    "diagnostic": str((summary.get("error") or {}).get("error") if isinstance(summary.get("error"), dict) else summary.get("error") or "focused live scenario failed"),
                    "scenario": scenario_name,
                }]
            )

    ok = all(bool(item.get("ok")) for item in scenarios.values())
    return {
        "ok": ok,
        "schema": TEST_SUITE_REPORT_SCHEMA,
        "schema_version": TEST_SUITE_REPORT_SCHEMA_VERSION,
        "action": "test_suite",
        "profile": "project-source-file-reliability",
        "status": "passed" if ok else "failed",
        "version": _read_version(repo_path),
        "project_name_base": base_name,
        "scenarios": scenarios,
        "failure_count": len(failures),
        "failed_steps": failures,
        "adoption_grade": False,
        "full_release_validation_required": True,
        "next_required_gate": "full_direct_and_full_localhost",
    }


def run_project_source_file_reliability_sync(**kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_project_source_file_reliability_async(**kwargs))


def run_test_suite_sync(**kwargs: Any) -> dict[str, Any]:
    return asyncio.run(run_test_suite_async(**kwargs))
