from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_api_coverage_script_help_and_safe_defaults() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "pb-api-coverage-test.py"
    result = subprocess.run(["python3", str(script), "--help"], text=True, capture_output=True, check=True)
    assert "--allow-source-add" in result.stdout
    assert "--include-source-gate-test" in result.stdout
    assert "--hold-auth-session" in result.stdout
    assert "--reuse-held-session" in result.stdout
    text = script.read_text(encoding="utf-8")
    assert "requires --allow-source-add and --source-file" in text
    assert "skipped by default because non-standard service modes may allow mutation" in text
    assert "browser_profile_busy" in text


def test_api_coverage_shell_wrapper_executes_python_script() -> None:
    wrapper = Path(__file__).resolve().parents[1] / "scripts" / "pb-api-coverage-test.sh"
    result = subprocess.run([str(wrapper), "--help"], text=True, capture_output=True, check=True)
    assert "Run Promptbranch container API coverage tests sequentially" in result.stdout


def test_cli_exposes_test_api_command() -> None:
    cli = Path(__file__).resolve().parents[1] / "promptbranch_cli.py"
    text = cli.read_text(encoding="utf-8")
    assert 'test_subparsers.add_parser("api"' in text
    assert 'async def cmd_test_api' in text
    assert 'args.test_command == "api"' in text


def test_api_coverage_module_help_is_install_safe() -> None:
    result = subprocess.run(["python3", "-m", "promptbranch.api_coverage_test", "--help"], text=True, capture_output=True, check=True)
    assert "Run Promptbranch container API coverage tests sequentially" in result.stdout


def test_cli_test_api_uses_installed_module_not_site_packages_scripts() -> None:
    cli = Path(__file__).resolve().parents[1] / "promptbranch_cli.py"
    text = cli.read_text(encoding="utf-8")
    assert '"-m", "promptbranch.api_coverage_test"' in text
    assert 'status": "script_missing"' not in text


def test_api_coverage_serial_mode_runs_auth_readiness_after_ask() -> None:
    script = Path(__file__).resolve().parents[1] / "promptbranch" / "api_coverage_test.py"
    text = script.read_text(encoding="utf-8")
    run_block = text[text.index("    def run(self) -> dict[str, Any]:"):text.index("    def report(self) -> dict[str, Any]:")]
    assert run_block.rindex('"project_source_capabilities",') < run_block.rindex('"ask",')
    assert run_block.rindex('"ask",') < run_block.rindex('"auth_readiness",')


def test_api_coverage_classifies_browser_profile_busy() -> None:
    from promptbranch.api_coverage_test import _classify_response

    assert _classify_response(503, {"detail": "browser_context_unavailable_held_auth_session_active"}, "HTTP Error 503") == "browser_profile_busy"

def test_api_coverage_does_not_classify_successful_clear_responses() -> None:
    from promptbranch.api_coverage_test import _classify_response

    assert _classify_response(200, {"ok": True, "action": "get_chat", "status": "completed", "text": "browser_context_unavailable_held_auth_session_active was mentioned in history"}, None) is None
    assert _classify_response(200, {"ok": True, "action": "debug_rate_limit", "status": "clear", "conversation_history_rate_limit": False}, None) is None
    assert _classify_response(200, {"ok": True, "action": "passive_auth_readiness", "status": "auth_preflight_ready", "challenge_detected": False, "release_blocking": False}, None) is None
    assert _classify_response(200, {"ok": True, "action": "add", "persistence_verified": True, "project_source_mutation_intent": "per_request", "challenge_detected": False, "release_blocking": False}, None) is None


def test_api_coverage_classifies_actual_rate_limit_and_challenge() -> None:
    from promptbranch.api_coverage_test import _classify_response

    assert _classify_response(429, {"detail": "Too many requests"}, "HTTP Error 429") == "rate_limited"
    assert _classify_response(200, {"ok": False, "status": "auth_challenge", "challenge_detected": True, "release_blocking": True}, None) == "auth_challenge_or_cloudflare"



def _api_runner_for_unit_tests():
    from promptbranch.api_coverage_test import ApiRunner, build_parser

    args = build_parser().parse_args([
        "--no-browser",
        "--no-ask",
        "--state-file",
        "/tmp/promptbranch-api-coverage-missing-state.json",
    ])
    return ApiRunner(args)


def test_api_coverage_semantic_failure_for_ask_without_ok_or_token() -> None:
    from promptbranch.api_coverage_test import Step

    runner = _api_runner_for_unit_tests()
    step = Step(name="ask", method="POST", path="/v1/ask", category="ask", status="passed", ok=True, http_status=200)
    runner._require_ask_success(
        step,
        {
            "ok": False,
            "status": "submit_causality_not_confirmed",
            "answer_text": "",
        },
    )
    assert not step.ok
    assert step.status == "failed"
    assert "ok=true" in str(step.error)
    assert "expected token" in str(step.error)
    assert "not observed" in str(step.error)


def test_api_coverage_semantic_pass_for_ask_token_observed() -> None:
    from promptbranch.api_coverage_test import Step

    runner = _api_runner_for_unit_tests()
    step = Step(name="ask", method="POST", path="/v1/ask", category="ask", status="passed", ok=True, http_status=200)
    runner._require_ask_success(step, {"ok": True, "status": "completed", "answer_text": "API_ASK_OK"})
    assert step.ok
    assert step.status == "passed"
    assert step.error is None




def test_api_coverage_ask_uses_button_submit_payload() -> None:
    module = Path(__file__).resolve().parents[1] / "promptbranch" / "api_coverage_test.py"
    script = Path(__file__).resolve().parents[1] / "scripts" / "pb-api-coverage-test.py"
    for path in (module, script):
        text = path.read_text(encoding="utf-8")
        assert '"prefer_button_submit": "true"' in text
        assert 'expected token {self.args.ask_token!r} not observed in answer_text' in text


def test_api_coverage_semantic_source_add_requires_persistence() -> None:
    from promptbranch.api_coverage_test import Step

    runner = _api_runner_for_unit_tests()
    step = Step(name="project_sources_add_file", method="POST", path="/v1/project-sources", category="mutation", status="passed", ok=True, http_status=200)
    runner._require_source_add_success(step, {"ok": True, "action": "add", "persistence_verified": False})
    assert not step.ok
    assert "persistence_verified=true" in str(step.error)


def test_api_coverage_semantic_auth_readiness_requires_no_challenge() -> None:
    from promptbranch.api_coverage_test import Step

    runner = _api_runner_for_unit_tests()
    step = Step(name="auth_readiness", method="POST", path="/v1/auth-readiness", category="browser", status="passed", ok=True, http_status=200)
    runner._require_auth_readiness_ready(
        step,
        {"ok": True, "logged_in": True, "challenge_detected": True, "release_blocking": True},
    )
    assert not step.ok
    assert step.classification == "auth_challenge_or_cloudflare"


def test_api_coverage_semantic_debug_rate_limit_requires_clear() -> None:
    from promptbranch.api_coverage_test import Step

    runner = _api_runner_for_unit_tests()
    step = Step(name="debug_rate_limit", method="GET", path="/v1/debug/rate-limit", category="debug", status="passed", ok=True, http_status=200)
    runner._require_debug_rate_limit_clear(step, {"ok": True, "status": "rate_limited"})
    assert not step.ok
    assert step.classification == "rate_limited"


def test_api_coverage_semantic_read_endpoint_requires_body_ok() -> None:
    from promptbranch.api_coverage_test import Step

    runner = _api_runner_for_unit_tests()
    step = Step(name="project_sources_list", method="GET", path="/v1/project-sources", category="sources", status="passed", ok=True, http_status=200)
    runner._require_body_ok(step, {"ok": False, "status": "not_ready"}, "project_sources_list")
    assert not step.ok
    assert "ok=true" in str(step.error)


def test_api_coverage_preflight_detects_held_session_payload_active() -> None:
    runner = _api_runner_for_unit_tests()
    assert runner._held_session_payload_active({"ok": False, "status": "no_held_auth_readiness_session", "held_session": {"active": False}}) is False
    assert runner._held_session_payload_active({"ok": True, "action": "auth_readiness_session_status", "status": "auth_preflight_ready", "held_session": {"active": True}}) is True
    assert runner._held_session_payload_active({"ok": True, "action": "auth_readiness_session_status", "status": "auth_preflight_ready"}) is True


def test_api_coverage_report_includes_preflight_state() -> None:
    runner = _api_runner_for_unit_tests()
    payload = runner.report()
    assert "preflight" in payload
    assert payload["preflight"]["browser_profile_busy"] is False
    assert payload["preflight"]["checked"] is False


def test_api_coverage_fail_early_when_preflight_busy_without_reuse() -> None:
    from promptbranch.api_coverage_test import Step

    runner = _api_runner_for_unit_tests()
    runner.preflight = {
        "browser_profile_busy": True,
        "held_auth_readiness_session_active": True,
        "checked": True,
        "reuse_held_session": False,
        "probes": [],
    }

    def fake_request(name, method, path, **kwargs):
        step = Step(name=name, method=method, path=path, category=kwargs.get("category", "status"), status="passed", ok=True, http_status=200)
        runner.steps.append(step)
        return step, {"ok": True}

    runner.request = fake_request  # type: ignore[method-assign]
    payload = runner._finish_after_held_session_preflight_failure()
    assert payload["ok"] is False
    assert payload["preflight"]["browser_profile_busy"] is True
    assert payload["counts"]["browser_profile_busy"] == 1
    names = {step["name"]: step for step in payload["steps"]}
    assert names["held_auth_session_preflight"]["status"] == "failed"
    assert names["login_check"]["status"] == "skipped"
    assert names["projects_list"]["skip_reason"].startswith("preflight.browser_profile_busy=true")
