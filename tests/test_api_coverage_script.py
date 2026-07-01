from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_api_coverage_script_help_and_safe_defaults() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "pb-api-coverage-test.py"
    result = subprocess.run(["python3", str(script), "--help"], text=True, capture_output=True, check=True)
    assert "--allow-source-add" in result.stdout
    assert "--include-source-gate-test" in result.stdout
    text = script.read_text(encoding="utf-8")
    assert "requires --allow-source-add and --source-file" in text
    assert "skipped by default because non-standard service modes may allow mutation" in text


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
