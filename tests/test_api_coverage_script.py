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
    assert '--reuse-held-session' in text
    assert '--no-auto-reuse-compatible-held-session' in text


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


def test_cli_test_api_maps_service_config_to_runner_transport(monkeypatch, tmp_path, capsys) -> None:
    import promptbranch_cli

    captured: dict[str, list[str]] = {}

    class Completed:
        returncode = 0

    def fake_run(cmd):
        captured["cmd"] = list(cmd)
        return Completed()

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "service_base_url": "http://localhost:8000",
                "service_token": "secret-from-config",
                "service_timeout_seconds": 300,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("CHATGPT_SERVICE_BASE_URL", raising=False)
    monkeypatch.delenv("CHATGPT_API_BASE_URL", raising=False)
    monkeypatch.delenv("CHATGPT_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("CHATGPT_API_TOKEN", raising=False)
    monkeypatch.delenv("PROMPTBRANCH_SERVICE_BASE_URL", raising=False)
    monkeypatch.setattr(promptbranch_cli.subprocess, "run", fake_run)

    exit_code = promptbranch_cli.main(["--config", str(config_path), "test", "api", "--json"])

    assert exit_code == 0
    cmd = captured["cmd"]
    assert cmd[:3] == [promptbranch_cli.sys.executable, "-m", "promptbranch.api_coverage_test"]
    assert cmd[cmd.index("--base-url") + 1] == "http://localhost:8000"
    assert cmd[cmd.index("--token") + 1] == "secret-from-config"
    assert "secret-from-config" not in capsys.readouterr().out


def test_cli_test_api_explicit_transport_overrides_service_config(monkeypatch, tmp_path) -> None:
    import promptbranch_cli

    captured: dict[str, list[str]] = {}

    class Completed:
        returncode = 0

    def fake_run(cmd):
        captured["cmd"] = list(cmd)
        return Completed()

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"service_base_url": "http://configured.invalid", "service_token": "configured-token"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(promptbranch_cli.subprocess, "run", fake_run)

    exit_code = promptbranch_cli.main(
        [
            "--config",
            str(config_path),
            "test",
            "api",
            "--base-url",
            "http://explicit.invalid",
            "--token",
            "explicit-token",
        ]
    )

    assert exit_code == 0
    cmd = captured["cmd"]
    assert cmd[cmd.index("--base-url") + 1] == "http://explicit.invalid"
    assert cmd[cmd.index("--token") + 1] == "explicit-token"
    assert "configured-token" not in cmd



def test_cli_test_api_forwards_reuse_held_session_flags(monkeypatch) -> None:
    import promptbranch_cli

    captured: dict[str, list[str]] = {}

    class Completed:
        returncode = 0

    def fake_run(cmd):
        captured["cmd"] = list(cmd)
        return Completed()

    monkeypatch.setattr(promptbranch_cli.subprocess, "run", fake_run)
    exit_code = promptbranch_cli.main([
        "test",
        "api",
        "--reuse-held-session",
        "--no-auto-reuse-compatible-held-session",
    ])

    assert exit_code == 0
    assert "--reuse-held-session" in captured["cmd"]
    assert "--no-auto-reuse-compatible-held-session" in captured["cmd"]


def test_api_coverage_auto_reuses_compatible_held_session() -> None:
    from promptbranch.api_coverage_test import ApiRunner, build_parser

    selected = "https://chatgpt.com/g/g-p-project/c/current-task?tab=sources"
    args = build_parser().parse_args([
        "--no-browser",
        "--no-ask",
        "--conversation-url",
        selected,
        "--state-file",
        "/tmp/promptbranch-api-coverage-missing-state.json",
    ])
    runner = ApiRunner(args)

    def fake_get(path, query=None):
        project_url = (query or {}).get("project_url")
        if project_url == "https://chatgpt.com/":
            return 200, {"ok": False, "status": "no_held_auth_readiness_session", "held_session": {"active": False}}, None, "url"
        return 200, {"ok": True, "action": "auth_readiness_session_status", "status": "auth_preflight_ready", "current_url": selected}, None, "url"

    runner._raw_json_get = fake_get  # type: ignore[method-assign]
    runner._preflight_check_held_auth_sessions()

    assert runner.preflight["browser_profile_busy"] is True
    assert runner.preflight["compatible_held_auth_readiness_session_active"] is True
    assert runner.preflight["auto_reuse_applied"] is True
    assert runner.preflight["reuse_held_session"] is True


def test_api_coverage_does_not_auto_reuse_incompatible_held_session() -> None:
    from promptbranch.api_coverage_test import ApiRunner, build_parser

    selected = "https://chatgpt.com/g/g-p-project/c/current-task?tab=sources"
    stale = "https://chatgpt.com/g/g-p-project/c/stale-task?tab=sources"
    args = build_parser().parse_args([
        "--no-browser",
        "--no-ask",
        "--conversation-url",
        selected,
        "--state-file",
        "/tmp/promptbranch-api-coverage-missing-state.json",
    ])
    runner = ApiRunner(args)

    def fake_get(path, query=None):
        return 200, {"ok": True, "action": "auth_readiness_session_status", "status": "auth_preflight_ready", "current_url": stale}, None, "url"

    runner._raw_json_get = fake_get  # type: ignore[method-assign]
    runner._preflight_check_held_auth_sessions()

    assert runner.preflight["browser_profile_busy"] is True
    assert runner.preflight["compatible_held_auth_readiness_session_active"] is False
    assert runner.preflight["auto_reuse_applied"] is False
    assert runner.preflight["reuse_held_session"] is False

def test_api_coverage_prefers_current_conversation_url_over_legacy_top_level(tmp_path) -> None:
    from promptbranch.api_coverage_test import ApiRunner, build_parser

    state_file = tmp_path / "state.json"
    current_url = "https://chatgpt.com/g/g-p-project/c/current-task?tab=sources&x=1=2"
    stale_url = "https://chatgpt.com/g/g-p-project/c/stale-task?tab=sources"
    state_file.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "project_home_url": "https://chatgpt.com/g/g-p-project/project",
                "conversation_url": stale_url,
                "current": {
                    "project_home_url": "https://chatgpt.com/g/g-p-project/project",
                    "conversation_url": current_url,
                },
            }
        ),
        encoding="utf-8",
    )
    args = build_parser().parse_args(["--no-browser", "--no-ask", "--state-file", str(state_file)])
    runner = ApiRunner(args)

    assert runner.conversation_url == current_url
    assert runner._ask_conversation_url() == current_url
    assert "x=1=2" in runner._ask_conversation_url()


def test_api_coverage_explicit_conversation_url_overrides_current_state(tmp_path) -> None:
    from promptbranch.api_coverage_test import ApiRunner, build_parser

    state_file = tmp_path / "state.json"
    current_url = "https://chatgpt.com/g/g-p-project/c/current-task?tab=sources"
    explicit_url = "https://chatgpt.com/g/g-p-project/c/explicit-task?tab=sources&keep=1=2"
    state_file.write_text(json.dumps({"current": {"conversation_url": current_url}}), encoding="utf-8")
    args = build_parser().parse_args([
        "--no-browser",
        "--no-ask",
        "--state-file",
        str(state_file),
        "--conversation-url",
        explicit_url,
    ])
    runner = ApiRunner(args)

    assert runner.conversation_url == explicit_url
    assert runner._ask_conversation_url() == explicit_url
    assert "keep=1=2" in runner._ask_conversation_url()


def test_api_coverage_skips_not_reuse_safe_endpoints_when_compatible_held_session_active(tmp_path) -> None:
    from promptbranch.api_coverage_test import ApiRunner, Step, build_parser

    source_file = tmp_path / "candidate.zip"
    source_file.write_bytes(b"zip-bytes")
    selected = "https://chatgpt.com/g/g-p-project/c/current-task?tab=sources"
    args = build_parser().parse_args([
        "--state-file",
        "/tmp/promptbranch-api-coverage-missing-state.json",
        "--conversation-url",
        selected,
        "--project-url",
        "https://chatgpt.com/g/g-p-project/project",
        "--allow-source-add",
        "--source-file",
        str(source_file),
    ])
    runner = ApiRunner(args)
    requested: list[str] = []

    def fake_preflight() -> None:
        runner.preflight = {
            "browser_profile_busy": True,
            "held_auth_readiness_session_active": True,
            "compatible_held_auth_readiness_session_active": True,
            "auto_reuse_compatible_held_session": True,
            "auto_reuse_applied": True,
            "checked": True,
            "reuse_held_session": True,
            "reuse_held_session_requested": False,
            "selected_conversation_url": selected,
            "probes": [],
        }

    def fake_request(name, method, path, **kwargs):
        requested.append(name)
        step = Step(name=name, method=method, path=path, category=kwargs.get("category", "status"), status="passed", ok=True, http_status=200)
        runner.steps.append(step)
        payload = {"ok": True, "status": "completed"}
        if name == "login_check":
            payload["logged_in"] = True
        elif name == "debug_rate_limit":
            payload["status"] = "clear"
        elif name == "project_sources_add_file":
            payload = {"ok": True, "action": "add", "persistence_verified": True}
        elif name == "ask":
            payload = {"ok": True, "status": "completed", "answer_text": "API_ASK_OK"}
        elif name == "auth_readiness":
            payload = {"ok": True, "logged_in": True, "challenge_detected": False, "release_blocking": False}
        return step, payload

    runner._preflight_check_held_auth_sessions = fake_preflight  # type: ignore[method-assign]
    runner.request = fake_request  # type: ignore[method-assign]

    payload = runner.run()
    names = {step["name"]: step for step in payload["steps"]}

    assert payload["ok"] is True
    assert names["login_check"]["status"] == "skipped"
    assert names["login_check"]["skip_reason"] == "held_session_active_endpoint_not_reuse_safe"
    assert names["projects_list"]["status"] == "skipped"
    assert names["chats_get"]["status"] == "skipped"
    assert names["debug_rate_limit"]["status"] == "skipped"
    assert names["project_source_capabilities"]["status"] == "skipped"
    assert names["project_sources_list"]["status"] == "skipped"
    assert names["ask"]["status"] == "passed"
    assert names["project_sources_add_file"]["status"] == "passed"
    assert names["auth_readiness"]["status"] == "passed"
    assert "login_check" not in requested
    assert "projects_list" not in requested
    assert "chats_get" not in requested
    assert "debug_rate_limit" not in requested
    assert "ask" in requested
    assert "project_sources_add_file" in requested
