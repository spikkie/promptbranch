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

