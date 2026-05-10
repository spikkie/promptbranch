import json
import os
import subprocess
from pathlib import Path


def test_promptbranch_statusline_uses_nearest_pb_profile(tmp_path: Path):
    root = tmp_path / "repo"
    nested = root / "a" / "b"
    profile = root / ".pb_profile"
    nested.mkdir(parents=True)
    profile.mkdir()
    (profile / ".promptbranch_state.json").write_text(
        json.dumps(
            {
                "project_name": "Demo Project",
                "conversation_id": "conv-123",
                "project_url": "https://chatgpt.com/",
                "conversation_url": "https://chatgpt.com/c/abc",
            }
        ),
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "promptbranch-statusline.sh"
    result = subprocess.run(
        [str(script), "--json", "--path", str(nested)],
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["has_profile"] is True
    assert payload["project"] == "Demo Project"
    assert payload["task"] == "conv-123"


def test_promptbranch_aliases_contains_expected_shortcuts():
    alias_file = Path(__file__).resolve().parents[1] / "scripts" / "promptbranch-aliases.sh"
    text = alias_file.read_text(encoding="utf-8")
    assert "alias pbs='promptbranch state'" in text
    assert "alias pbtl='promptbranch task list'" in text
    assert "alias pbsl='promptbranch src list'" in text
    assert "alias pbsf='promptbranch src add --type file --file'" in text
    assert "alias pbsr='promptbranch src rm'" in text
    assert "alias pbss='promptbranch src sync'" in text
    assert "alias pbac='promptbranch artifact current'" in text



def test_release_control_tests_only_skips_release_mutation_steps(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"

    (fake_bin / "promptbranch").write_text("#!/usr/bin/env bash\necho promptbranch \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n", encoding="utf-8")
    (fake_bin / "promptbranch").chmod(0o755)
    (fake_bin / "timeout").write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"--foreground\" ]]; then shift; fi\n"
        "shift\n"
        "exec \"$@\"\n",
        encoding="utf-8",
    )
    (fake_bin / "timeout").chmod(0o755)
    (fake_bin / "pb").write_text(
        "#!/usr/bin/env bash\n"
        "echo pb \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.9\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\"}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-tests-only.log"

    result = subprocess.run(
        [str(script), "--tests-only", "--version", "v9.9.9"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "tests_only:     1" in result.stdout
    assert "Download ZIP not found" not in result.stdout + result.stderr
    assert not (repo / "chatgpt_claudecode_workflow_v9.9.9.zip").exists()
    assert (repo / "pb_test.full.v9.9.9.log").is_file()
    assert (repo / "pb_test.full.v9.9.9.report.json").is_file()
    assert (repo / "release-control-tests-only.log").is_file()
    call_text = calls.read_text(encoding="utf-8")
    assert "pb test full --json" in call_text
    assert "pb test report pb_test.full.v9.9.9.log --json" in call_text
    assert "promptbranch src add" not in call_text


def _write_release_control_fake_commands(fake_bin: Path, calls: Path, *, version: str = "v9.9.9") -> None:
    artifact = f"chatgpt_claudecode_workflow_{version}.zip"
    (fake_bin / "promptbranch").write_text(
        "#!/usr/bin/env bash\n"
        "echo promptbranch \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n",
        encoding="utf-8",
    )
    (fake_bin / "promptbranch").chmod(0o755)
    (fake_bin / "timeout").write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"--foreground\" ]]; then shift; fi\n"
        "shift\n"
        "exec \"$@\"\n",
        encoding="utf-8",
    )
    (fake_bin / "timeout").chmod(0o755)
    (fake_bin / "pb").write_text(
        "#!/usr/bin/env bash\n"
        "echo pb \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n"
        f"artifact='{artifact}'\n"
        f"version='{version}'\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"'\"$version\"'\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact verify\" ]]; then echo '{\"ok\": true, \"action\": \"artifact_verify\", \"status\": \"verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"src list\" ]]; then echo '{\"ok\": true, \"sources\": [{\"filename\": \"'\"$artifact\"'\"}]}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact adopt\" ]]; then echo '{\"ok\": true, \"action\": \"artifact_adopt\", \"status\": \"adopted\", \"source_verified\": true, \"project_source_mutated\": false, \"artifact_registry_updated\": true, \"state_artifact_updated\": true, \"state_source_updated\": true}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact current\" ]]; then echo '{\"ok\": true, \"runtime\": {\"version\": \"'\"$version\"'\"}, \"state\": {\"artifact_ref\": \"'\"$artifact\"'\", \"artifact_version\": \"'\"$version\"'\", \"source_ref\": \"'\"$artifact\"'\", \"source_version\": \"'\"$version\"'\"}, \"registry_current\": {\"filename\": \"'\"$artifact\"'\", \"version\": \"'\"$version\"'\"}, \"consistency\": {\"registry_current_matches_state_artifact\": true, \"state_source_matches_state_artifact\": true, \"code_version_matches_state_source\": true}}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)


def test_release_control_adopt_current_verifies_and_adopts_without_running_tests(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.9"
    artifact = f"chatgpt_claudecode_workflow_{version}.zip"
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    (repo / artifact).write_bytes(b"fake zip; pb artifact verify is mocked")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    _write_release_control_fake_commands(fake_bin, calls, version=version)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)

    result = subprocess.run(
        [str(script), "--adopt-current", "--version", version],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "adopt_current:  1" in result.stdout
    assert "Adopt verified" in result.stdout
    call_text = calls.read_text(encoding="utf-8")
    assert "pb artifact verify" in call_text
    assert "pb src list --json" in call_text
    assert f"pb artifact adopt {artifact} --from-project-source --local-path {repo / artifact} --json" in call_text
    assert "pb artifact current --json" in call_text
    assert "pb test full" not in call_text
    assert "promptbranch src add" not in call_text



def test_release_control_rejects_run_tests_adopt_if_green_without_tests_only(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    _write_release_control_fake_commands(fake_bin, calls, version="v9.9.9")

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)

    result = subprocess.run(
        [str(script), "--run-tests", "--adopt-if-green", "--version", "v9.9.9"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--adopt-if-green is only supported with --tests-only" in result.stderr
    assert not calls.exists()


def test_release_control_docker_logs_missing_container_is_best_effort(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.9"
    artifact = f"chatgpt_claudecode_workflow_{version}.zip"
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    import zipfile

    with zipfile.ZipFile(downloads / artifact, "w") as archive:
        archive.writestr("VERSION", f"{version}\n")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    _write_release_control_fake_commands(fake_bin, calls, version=version)
    (fake_bin / "pipx").write_text("#!/usr/bin/env bash\necho pipx \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n", encoding="utf-8")
    (fake_bin / "pipx").chmod(0o755)
    (fake_bin / "git").write_text("#!/usr/bin/env bash\necho git \"$@\" >> \"$PB_FAKE_CALL_LOG\"\nexit 0\n", encoding="utf-8")
    (fake_bin / "git").chmod(0o755)
    (fake_bin / "docker").write_text(
        "#!/usr/bin/env bash\n"
        "echo docker \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"ps\" ]]; then echo 'deadbeef promptbranch-service promptbranch'; exit 0; fi\n"
        "if [[ \"$1\" == \"inspect\" ]]; then exit 1; fi\n"
        "if [[ \"$1\" == \"logs\" ]]; then echo should-not-call-logs >&2; exit 9; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (fake_bin / "docker").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-docker-missing.log"

    result = subprocess.run(
        [
            str(script),
            "--version", version,
            "--downloads-dir", str(downloads),
            "--skip-compare",
            "--skip-commit",
            "--skip-source-add",
            "--skip-install",
            "--skip-chown",
            "--skip-service",
            "--run-tests",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "WARN: docker container no longer exists; skipping docker logs: deadbeef" in result.stderr
    assert "Release workflow completed." in result.stdout
    call_text = calls.read_text(encoding="utf-8")
    assert "docker ps" in call_text
    assert "docker inspect deadbeef" in call_text
    assert "docker logs" not in call_text


def test_release_control_adopt_if_green_is_explicitly_guarded() -> None:
    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    text = script.read_text(encoding="utf-8")

    assert "--adopt-if-green" in text
    assert 'report_is_green "${report_json}"' in text
    assert "adopt_current_artifact" in text
    assert "--adopt-if-green is only supported with --tests-only" in text
    assert "--tests-only = no baseline mutation" not in text  # behavior is enforced by explicit flag checks, not prose


def test_release_control_accepts_numeric_repair_version_for_adopt_current(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.9.1"
    artifact = f"chatgpt_claudecode_workflow_{version}.zip"
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    (repo / artifact).write_bytes(b"fake zip; pb artifact verify is mocked")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    _write_release_control_fake_commands(fake_bin, calls, version=version)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)

    result = subprocess.run(
        [str(script), "--adopt-current", "--version", version],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "version:        v9.9.9.1" in result.stdout
    assert "Adopt verified" in result.stdout
    call_text = calls.read_text(encoding="utf-8")
    assert f"pb artifact adopt {artifact}" in call_text
