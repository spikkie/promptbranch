from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

VERSION = "v0.1.103.10.57"

StepStatus = Literal["passed", "failed", "skipped"]


@dataclass
class ReplayStep:
    name: str
    status: StepStatus
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "passed"


@dataclass
class ReplayResult:
    scenario: str
    steps: list[ReplayStep] = field(default_factory=list)
    launched_browser_steps: list[str] = field(default_factory=list)
    final_verdict: Literal["GO", "FIX"] = "GO"

    @property
    def ok(self) -> bool:
        return self.final_verdict == "GO"

    def step(self, name: str) -> ReplayStep:
        for step in self.steps:
            if step.name == name:
                return step
        raise AssertionError(f"step not found: {name}; steps={[step.name for step in self.steps]}")


def replay_run_all(scenario: str) -> ReplayResult:
    """Fast release-control state-machine replay.

    This intentionally does not open Docker/ChatGPT/browser.  It models the
    run-all orchestration decisions that must be proven before spending time on
    one real live release-control run.
    """
    result = ReplayResult(scenario=scenario)

    def passed(name: str) -> None:
        result.steps.append(ReplayStep(name, "passed"))

    def failed(name: str, reason: str) -> None:
        result.steps.append(ReplayStep(name, "failed", reason))
        result.final_verdict = "FIX"

    def skipped(name: str, reason: str) -> None:
        result.steps.append(ReplayStep(name, "skipped", reason))
        result.final_verdict = "FIX"

    passed("full_direct")
    passed("full_localhost")
    passed("live_profile_preflight")

    if scenario == "auth_bootstrap_backend_403":
        # In a full release this stops before Project Source add/test-all.  In
        # replay we model the terminal effect on browser phases.
        failed("pre_source_add", "browser_backend_403_guardrail")
        return result

    if scenario == "live_project_ensure_challenge":
        failed("live_project_ensure", "docker_live_profile_challenged")
        for name in ("live_conversation_bootstrap", "ask_live", "visual_artifact_roundtrip", "release_live"):
            skipped(name, "skipped_live_project_ensure_docker_live_profile_challenged")
        passed("import_smoke")
        passed("artifact_guard")
        return result

    passed("live_project_ensure")

    if scenario == "live_bootstrap_429_guardrail_with_persisted_cooldown":
        failed("live_conversation_bootstrap", "live_bootstrap_guardrail")
        for name in ("ask_live", "visual_artifact_roundtrip", "release_live"):
            skipped(name, "skipped_blocked_by_live_bootstrap_guardrail")
        passed("import_smoke")
        passed("artifact_guard")
        return result

    passed("live_conversation_bootstrap")

    if scenario == "ask_live_challenge":
        result.launched_browser_steps.append("release_live_continuous")
        failed("ask_live", "docker_live_profile_challenged")
        skipped("visual_artifact_roundtrip", "skipped_ask_live_docker_live_profile_challenged")
        skipped("release_live", "skipped_ask_live_docker_live_profile_challenged")
        passed("import_smoke")
        passed("artifact_guard")
        return result

    result.launched_browser_steps.extend(["release_live_continuous", "visual_artifact_roundtrip", "release_live"])
    passed("ask_live")
    passed("visual_artifact_roundtrip")
    passed("release_live")
    passed("import_smoke")
    passed("artifact_guard")
    return result


def test_release_control_replay_success_go_path() -> None:
    result = replay_run_all("success")

    assert result.ok is True
    assert result.final_verdict == "GO"
    for name in (
        "full_direct",
        "full_localhost",
        "live_profile_preflight",
        "live_project_ensure",
        "live_conversation_bootstrap",
        "ask_live",
        "visual_artifact_roundtrip",
        "release_live",
        "import_smoke",
        "artifact_guard",
    ):
        assert result.step(name).ok is True
    assert result.launched_browser_steps == ["release_live_continuous", "visual_artifact_roundtrip", "release_live"]


def test_release_control_replay_live_bootstrap_429_guardrail_blocks_ask_live_without_wait() -> None:
    result = replay_run_all("live_bootstrap_429_guardrail_with_persisted_cooldown")

    assert result.ok is False
    assert result.final_verdict == "FIX"
    assert result.step("live_conversation_bootstrap").reason == "live_bootstrap_guardrail"
    assert result.step("ask_live").reason == "skipped_blocked_by_live_bootstrap_guardrail"
    assert result.step("visual_artifact_roundtrip").reason == "skipped_blocked_by_live_bootstrap_guardrail"
    assert result.step("release_live").reason == "skipped_blocked_by_live_bootstrap_guardrail"
    assert result.step("import_smoke").ok is True
    assert result.step("artifact_guard").ok is True
    assert "ask_live" not in result.launched_browser_steps
    assert "visual_artifact_roundtrip" not in result.launched_browser_steps
    assert "release_live" not in result.launched_browser_steps


def test_release_control_replay_ask_live_challenge_is_terminal() -> None:
    result = replay_run_all("ask_live_challenge")

    assert result.ok is False
    assert result.step("ask_live").reason == "docker_live_profile_challenged"
    assert result.step("visual_artifact_roundtrip").reason == "skipped_ask_live_docker_live_profile_challenged"
    assert result.step("release_live").reason == "skipped_ask_live_docker_live_profile_challenged"
    assert result.launched_browser_steps == ["release_live_continuous"]


def test_release_control_replay_live_project_ensure_challenge_blocks_bootstrap_and_ask() -> None:
    result = replay_run_all("live_project_ensure_challenge")

    assert result.ok is False
    assert result.step("live_project_ensure").reason == "docker_live_profile_challenged"
    assert result.step("live_conversation_bootstrap").reason == "skipped_live_project_ensure_docker_live_profile_challenged"
    assert result.step("ask_live").reason == "skipped_live_project_ensure_docker_live_profile_challenged"
    assert result.launched_browser_steps == []


def test_release_control_replay_continuous_bootstrap_clean_ask_challenge() -> None:
    result = replay_run_all("ask_live_challenge")

    assert result.ok is False
    assert result.step("ask_live").reason == "docker_live_profile_challenged"
    assert result.step("visual_artifact_roundtrip").reason == "skipped_ask_live_docker_live_profile_challenged"
    assert result.step("release_live").reason == "skipped_ask_live_docker_live_profile_challenged"
    assert result.launched_browser_steps == ["release_live_continuous"]
