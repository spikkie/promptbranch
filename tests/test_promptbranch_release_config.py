from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from promptbranch_cli import cmd_release_config


ROOT_CONFIG = Path(".promptbranch-release.yml")


def test_checked_in_release_config_is_read_only_and_repo_relative(capsys) -> None:
    args = argparse.Namespace(config=str(ROOT_CONFIG), repo_path=".", json=True)

    exit_code = asyncio.run(cmd_release_config(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["status"] == "verified"
    assert payload["action"] == "release_config"
    assert payload["read_only"] is True
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
    assert payload["git_commit_performed"] is False
    assert payload["git_push_performed"] is False
    assert payload["artifact"]["prefix"] == "chatgpt_claudecode_workflow-2_"
    assert payload["artifact"]["version_prefix"] == "v"
    assert payload["artifact"]["suffix"] == ".zip"
    assert payload["artifact"]["filename_pattern"] == "chatgpt_claudecode_workflow-2_v<version>.zip"
    assert payload["artifact"]["version_file"] == "VERSION"
    assert payload["artifact"]["policy_file"] == ".pb_profile/promptbranch_artifacts.json"
    assert ".git/" in payload["install"]["preserve"]
    assert ".pb_profile/" in payload["install"]["preserve"]
    assert "*.zip" in payload["git"]["unsafe_paths"]
    assert payload["read_only_contract"]["hooks_executed"] is False
    assert payload["read_only_contract"]["install_executed"] is False
    assert payload["read_only_contract"]["adoption_performed"] is False
    assert payload["blocker_codes"] == []


def test_release_config_reports_docs_hooks_without_executing_them(capsys) -> None:
    args = argparse.Namespace(config=str(ROOT_CONFIG), repo_path=".", json=True)

    exit_code = asyncio.run(cmd_release_config(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    hooks = payload["hooks"]
    assert hooks["docs_status"]["repo_relative"] is True
    assert hooks["docs_status"]["template_valid"] is True
    assert hooks["docs_status"]["placeholders"] == ["version"]
    assert "release docs-status" in hooks["docs_status"]["command"]
    assert hooks["focused_docs_tests"]["repo_relative"] is True
    assert hooks["focused_docs_tests"]["template_valid"] is True
    assert hooks["focused_docs_tests"]["placeholders"] == []
    assert "tests/test_promptbranch_docs_site_scaffold.py" in hooks["focused_docs_tests"]["command"]
    assert payload["read_only_contract"]["hooks_executed"] is False


def test_release_config_rejects_absolute_hook_command_paths(capsys, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / ".promptbranch-release.yml"
    config.write_text(
        """
schema_version: 1
artifact:
  prefix: chatgpt_claudecode_workflow-2_
  version_prefix: v
  suffix: .zip
  version_file: VERSION
  policy_file: .pb_profile/promptbranch_artifacts.json
install:
  preserve:
    - .git/
    - .pb_profile/
git:
  unsafe_paths:
    - .env
    - '*.zip'
hooks:
  bad_absolute:
    command: /home/spikkie/bin/release --version {version}
""".lstrip(),
        encoding="utf-8",
    )
    args = argparse.Namespace(config=str(config), repo_path=str(repo), json=True)

    exit_code = asyncio.run(cmd_release_config(None, args))
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert "release_config_hook_command_path_invalid" in payload["blocker_codes"]
    assert payload["mutating_actions_executed"] is False
    assert payload["project_source_mutated"] is False
