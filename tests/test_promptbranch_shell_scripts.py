import json
import os
import re
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
    assert "alias pbsa='promptbranch src add'" in text
    assert "alias pbsf='promptbranch src add --type file --file'" in text
    assert "alias pbsr='promptbranch src rm'" in text
    assert "alias pbss='promptbranch src sync'" in text
    assert "alias pbac='promptbranch artifact current'" in text





def test_release_control_generated_project_name_is_capped_to_chatgpt_limit():
    script_path = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    script_text = script_path.read_text(encoding="utf-8")
    assert "chatgpt_project_name_max_length=50" in script_text
    assert "shorten_chatgpt_project_name" in script_text
    assert 'release_test_project_name="$(shorten_chatgpt_project_name "itest-promptbranch-${release_test_project_version}-${release_test_project_stamp}")"' in script_text
    assert "PROMPTBRANCH_RELEASE_TEST_PROJECT_NAME exceeds ChatGPT project-name limit" in script_text

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
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
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
    log_dir = repo / ".pb_profile" / "release_logs" / "v9.9.9"
    assert not (repo / "chatgpt_claudecode_workflow_v9.9.9.zip").exists()
    assert (log_dir / "pb_test.full.v9.9.9.log").is_file()
    assert (log_dir / "pb_test.full.v9.9.9.report.json").is_file()
    structured_summary = log_dir / "post_release_validation.v9.9.9.summary.json"
    assert structured_summary.is_file()
    summary_payload = json.loads(structured_summary.read_text(encoding="utf-8"))
    assert summary_payload["source_kind"] == "release_control_full_test_summary"
    assert summary_payload["ok"] is True
    assert summary_payload["failure_count"] == 0
    assert summary_payload["full_test_evidence"]["full_test_green"] is True
    assert summary_payload["full_test_evidence"]["report_json"] == str(log_dir / "pb_test.full.v9.9.9.report.json")
    assert (log_dir / "release-control-tests-only.log").is_file()
    assert "release_logs:" in result.stdout
    assert f"structured_summary: {structured_summary}" in result.stdout
    assert "service_log:   skipped" in result.stdout
    assert "service_start: skipped" in result.stdout
    assert "service_pid:   skipped" in result.stdout
    call_text = calls.read_text(encoding="utf-8")
    assert re.search(r"pb test full --project-name itest-promptbranch-v9-9-9-[0-9]{8}T[0-9]{6}Z-[0-9]+ --keep-project --fail-fast --json", call_text)
    assert f"pb test report {log_dir / 'pb_test.full.v9.9.9.log'} --json" in call_text
    assert "promptbranch src add" not in call_text




def test_release_control_test_transport_localhost_sets_service_base_url_and_writes_transport_logs(tmp_path: Path):
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
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.9\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"

    result = subprocess.run(
        [
            str(script),
            "--tests-only",
            "--version",
            "v9.9.9",
            "--test-transport",
            "localhost",
            "--localhost-base-url",
            "http://127.0.0.1:8123",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_dir = repo / ".pb_profile" / "release_logs" / "v9.9.9"
    localhost_log = log_dir / "pb_test.full.localhost.v9.9.9.log"
    localhost_report = log_dir / "pb_test.full.localhost.v9.9.9.report.json"
    assert localhost_log.is_file()
    assert localhost_report.is_file()
    assert "test_transport: localhost" in result.stdout
    assert f"localhost_log: {localhost_log}" in result.stdout
    call_text = calls.read_text(encoding="utf-8")
    assert re.search(r"pb test full --project-name itest-promptbranch-v9-9-9-[0-9]{8}T[0-9]{6}Z-[0-9]+ --keep-project --fail-fast --json CHATGPT_SERVICE_BASE_URL=http://127.0.0.1:8123", call_text)
    assert f"pb test report {localhost_log} --json CHATGPT_SERVICE_BASE_URL=" in call_text


def test_release_control_test_transport_both_runs_direct_and_localhost(tmp_path: Path):
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
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.9\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"

    subprocess.run(
        [str(script), "--tests-only", "--version", "v9.9.9", "--test-transport", "both"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_dir = repo / ".pb_profile" / "release_logs" / "v9.9.9"
    assert (log_dir / "pb_test.full.direct.v9.9.9.log").is_file()
    assert (log_dir / "pb_test.full.direct.v9.9.9.report.json").is_file()
    assert (log_dir / "pb_test.full.localhost.v9.9.9.log").is_file()
    assert (log_dir / "pb_test.full.localhost.v9.9.9.report.json").is_file()
    call_text = calls.read_text(encoding="utf-8")
    assert len(re.findall(r"pb test full --project-name itest-promptbranch-v9-9-9-[0-9]{8}T[0-9]{6}Z-[0-9]+ --keep-project --fail-fast --json", call_text)) == 2
    assert "CHATGPT_SERVICE_BASE_URL=http://127.0.0.1:8000" in call_text

def _write_release_control_fake_commands(fake_bin: Path, calls: Path, *, version: str = "v9.9.9") -> None:
    artifact = f"repo_{version}.zip"
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
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
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
    artifact = f"repo_{version}.zip"
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
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"

    result = subprocess.run(
        [str(script), "--adopt-current", "--version", version],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "adopt_current:  1" in result.stdout
    assert "release_adopted_and_verified" in result.stdout
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



def test_release_control_automatically_imports_candidate_zip_without_bcompare(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.10"
    artifact = f"chatgpt_claudecode_workflow_{version}.zip"
    (repo / "VERSION").write_text("v0.0.0\n", encoding="utf-8")
    (repo / "stale.txt").write_text("remove me\n", encoding="utf-8")
    (repo / ".env").write_text("LOCAL=1\n", encoding="utf-8")
    (repo / ".promptbranch-repo.json").write_text(json.dumps({"schema_version": 1, "project_id": "stale", "project_home_url": "https://chatgpt.com/g/g-p-stale/project", "repo_id": "stale", "artifact_pattern": "stale_<version>.zip", "role": "member"}), encoding="utf-8")
    (repo / ".pb_profile").mkdir()
    (repo / ".pb_profile" / "state.json").write_text("{}\n", encoding="utf-8")
    (repo / "debug_artifacts").mkdir()
    (repo / "debug_artifacts" / "trace.zip").write_text("preserve debug trace\n", encoding="utf-8")

    downloads = tmp_path / "downloads"
    downloads.mkdir()
    import zipfile

    with zipfile.ZipFile(downloads / artifact, "w") as archive:
        archive.writestr("VERSION", f"{version}\n")
        archive.writestr("pyproject.toml", f"[project]\nname = 'promptbranch'\nversion = '{version.lstrip('v')}'\n")
        archive.writestr(".gitignore", "*.zip\n.env\n.pb_profile/\ndebug_artifacts/\n")
        archive.writestr(".not_to_zip", "*.zip\n.env\n.pb_profile/\ndebug_artifacts/\n")
        archive.writestr(".promptbranch-repo.json", json.dumps({"schema_version": 1, "project_id": "g-p-demo", "project_home_url": "https://chatgpt.com/g/g-p-demo/project", "repo_id": "chatgpt_claudecode_workflow", "artifact_pattern": "chatgpt_claudecode_workflow_<version>.zip", "role": "release_authority"}))
        archive.writestr("fresh.txt", "installed\n")
        archive.writestr("ollama_mcp_verification_harness/README.md", "tracked harness\n")
        archive.writestr("ollama_mcp_verification_harness_v2/README.md", "tracked harness v2\n")
        archive.writestr("promptbranch.egg-info/PKG-INFO", "Metadata-Version: 2.4\n")
        archive.writestr("scripts/example.sh", "#!/usr/bin/env bash\n")
        archive.writestr("run_chatgpt_service.sh", "#!/usr/bin/env bash\n")
        archive.writestr("chatgpt_claudecode_workflow_release_control.sh", "#!/usr/bin/env bash\n")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    (fake_bin / "promptbranch").write_text("#!/usr/bin/env bash\necho promptbranch \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n", encoding="utf-8")
    (fake_bin / "promptbranch").chmod(0o755)
    (fake_bin / "pipx").write_text("#!/usr/bin/env bash\necho pipx \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n", encoding="utf-8")
    (fake_bin / "pipx").chmod(0o755)
    (fake_bin / "git").write_text(
        "#!/usr/bin/env bash\n"
        "echo git \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"status\" ]]; then exit 0; fi\n"
        "if [[ \"$1 $2 $3\" == \"rev-parse --short HEAD\" ]]; then echo abc1234; exit 0; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (fake_bin / "git").chmod(0o755)
    packager = tmp_path / "packager.sh"
    packager.write_text(
        "#!/usr/bin/env bash\n"
        "python3 - <<'INNERPY'\n"
        "import zipfile\n"
        f"with zipfile.ZipFile('{artifact}', 'w') as archive:\n"
        f"    archive.writestr('VERSION', '{version}\\n')\n"
        "    archive.writestr('fresh.txt', 'installed\\n')\n"
        "INNERPY\n",
        encoding="utf-8",
    )
    packager.chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    env["PROMPTBRANCH_ARTIFACT_PROJECT_NAME"] = "chatgpt_claudecode_workflow"

    result = subprocess.run(
        [
            str(script),
            "--version", version,
            "--downloads-dir", str(downloads),
            "--packager", str(packager),
            "--skip-compare",
            "--skip-commit",
            "--skip-source-add",
            "--skip-install",
            "--skip-chown",
            "--skip-service",
            "--skip-docker-logs",
            "--skip-tests",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "zip_import:     1" in result.stdout
    assert "== Install ZIP into working tree ==" in result.stdout
    assert "bcompare" not in result.stdout + result.stderr
    assert (repo / "fresh.txt").read_text(encoding="utf-8") == "installed\n"
    assert not (repo / "stale.txt").exists()
    assert (repo / ".env").read_text(encoding="utf-8") == "LOCAL=1\n"
    installed_binding = json.loads((repo / ".promptbranch-repo.json").read_text(encoding="utf-8"))
    assert installed_binding["project_id"] == "g-p-demo"
    assert installed_binding["repo_id"] == "chatgpt_claudecode_workflow"
    assert (repo / ".pb_profile" / "state.json").is_file()
    assert (repo / "debug_artifacts" / "trace.zip").read_text(encoding="utf-8") == "preserve debug trace\n"
    assert (repo / "ollama_mcp_verification_harness" / "README.md").read_text(encoding="utf-8") == "tracked harness\n"
    assert (repo / "ollama_mcp_verification_harness_v2" / "README.md").read_text(encoding="utf-8") == "tracked harness v2\n"
    assert (repo / "promptbranch.egg-info" / "PKG-INFO").is_file()
    assert (repo / ".gitignore").is_file()
    assert (repo / ".not_to_zip").is_file()
    assert (repo / artifact).is_file()
    assert os.access(repo / "run_chatgpt_service.sh", os.X_OK)
    assert os.access(repo / "chatgpt_claudecode_workflow_release_control.sh", os.X_OK)
    assert os.access(repo / "scripts" / "example.sh", os.X_OK)
    assert "Source add skipped: --skip-source-add" in result.stdout
    call_text = calls.read_text(encoding="utf-8")
    assert "promptbranch src add" not in call_text


def test_release_control_stage0_delegation_preserves_skip_source_add(tmp_path: Path):
    repo = tmp_path / "chatgpt_claudecode_workflow"
    repo.mkdir()
    version = "v9.9.31"
    artifact = f"chatgpt_claudecode_workflow_{version}.zip"
    (repo / "VERSION").write_text("v0.0.0\n", encoding="utf-8")
    (repo / ".env").write_text("LOCAL=1\n", encoding="utf-8")

    downloads = tmp_path / "downloads"
    downloads.mkdir()
    import zipfile

    release_script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    with zipfile.ZipFile(downloads / artifact, "w") as archive:
        archive.writestr("VERSION", f"{version}\n")
        archive.writestr("pyproject.toml", f"[project]\nname = 'promptbranch'\nversion = '{version.lstrip('v')}'\n")
        archive.writestr(".gitignore", "*.zip\n.env\n.pb_profile/\ndebug_artifacts/\n")
        archive.writestr(".not_to_zip", "*.zip\n.env\n.pb_profile/\ndebug_artifacts/\n")
        archive.writestr(".promptbranch-repo.json", json.dumps({"schema_version": 1, "project_id": "g-p-demo", "project_home_url": "https://chatgpt.com/g/g-p-demo/project", "repo_id": "chatgpt_claudecode_workflow", "artifact_pattern": "chatgpt_claudecode_workflow_<version>.zip", "role": "release_authority"}))
        archive.writestr("fresh.txt", "installed by delegated candidate\n")
        archive.writestr("chatgpt_claudecode_workflow_release_control.sh", release_script.read_text(encoding="utf-8"))

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    (fake_bin / "promptbranch").write_text(
        "#!/usr/bin/env bash\n"
        "echo promptbranch \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n",
        encoding="utf-8",
    )
    (fake_bin / "promptbranch").chmod(0o755)
    (fake_bin / "git").write_text(
        "#!/usr/bin/env bash\n"
        "echo git \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"status\" ]]; then exit 0; fi\n"
        "if [[ \"$1 $2 $3\" == \"rev-parse --short HEAD\" ]]; then echo abc1234; exit 0; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (fake_bin / "git").chmod(0o755)
    packager = tmp_path / "packager.sh"
    packager.write_text(
        "#!/usr/bin/env bash\n"
        "python3 - <<'INNERPY'\n"
        "import zipfile\n"
        f"with zipfile.ZipFile('{artifact}', 'w') as archive:\n"
        f"    archive.writestr('VERSION', '{version}\\n')\n"
        "    archive.writestr('fresh.txt', 'packaged\\n')\n"
        "INNERPY\n",
        encoding="utf-8",
    )
    packager.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)

    result = subprocess.run(
        [
            str(release_script),
            "--version", version,
            "--install-from-zip", str(downloads / artifact),
            "--packager", str(packager),
            "--skip-commit",
            "--skip-source-add",
            "--skip-install",
            "--skip-chown",
            "--skip-service",
            "--skip-docker-logs",
            "--skip-tests",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "== Delegate to workflow runner from candidate ZIP ==" in result.stdout
    assert "Source add skipped: --skip-source-add" in result.stdout
    call_text = calls.read_text(encoding="utf-8")
    assert "promptbranch src add" not in call_text
    assert (repo / "fresh.txt").read_text(encoding="utf-8") == "installed by delegated candidate\n"


def _extract_first_json_object(text: str) -> dict:
    start = text.find("{")
    assert start >= 0, text
    return json.loads(text[start:])


def _write_release_candidate_zip(path: Path, *, version: str, include_version: bool = True, include_script: bool = True, wrapper: bool = False) -> None:
    import zipfile

    prefix = "wrapped/" if wrapper else ""
    with zipfile.ZipFile(path, "w") as archive:
        if include_version:
            archive.writestr(f"{prefix}VERSION", f"{version}\n")
        archive.writestr(f"{prefix}pyproject.toml", f"[project]\nname = 'promptbranch'\nversion = '{version.lstrip('v')}'\n")
        archive.writestr(f"{prefix}.gitignore", "*.zip\n.env\n.pb_profile/\ndebug_artifacts/\n")
        archive.writestr(f"{prefix}.not_to_zip", "*.zip\n.env\n.pb_profile/\ndebug_artifacts/\n")
        archive.writestr(f"{prefix}.promptbranch-repo.json", json.dumps({"schema_version": 1, "project_id": "g-p-demo", "project_home_url": "https://chatgpt.com/g/g-p-demo/project", "repo_id": "chatgpt_claudecode_workflow", "artifact_pattern": "chatgpt_claudecode_workflow_<version>.zip", "role": "release_authority"}))
        archive.writestr(f"{prefix}fresh.txt", "installed\n")
        if include_script:
            archive.writestr(f"{prefix}chatgpt_claudecode_workflow_release_control.sh", "#!/usr/bin/env bash\n")


def test_release_control_import_plan_validates_candidate_without_mutating_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v0.0.0\n", encoding="utf-8")
    (repo / "stale.txt").write_text("keep until real import\n", encoding="utf-8")
    version = "v9.9.12"
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    artifact = downloads / f"chatgpt_claudecode_workflow_{version}.zip"
    _write_release_candidate_zip(artifact, version=version)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    result = subprocess.run(
        [str(script), "--version", version, "--downloads-dir", str(downloads), "--import-plan"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = _extract_first_json_object(result.stdout)
    assert payload["ok"] is True
    assert payload["action"] == "release_zip_import_plan"
    assert payload["zip_version"] == version
    assert payload["zip_root_layout"] == "repo_root"
    assert payload["candidate_script_present"] is True
    assert payload["missing_required_root_files"] == []
    assert payload["would_install"] is True
    assert ".git" in payload["preserved_paths"]
    assert "debug_artifacts" in payload["preserved_paths"]
    assert ".pb_profile_local_debug_pools" in payload["preserved_paths"]
    assert "stale.txt" in payload["would_remove_root_entries_sample"]
    assert (repo / "stale.txt").read_text(encoding="utf-8") == "keep until real import\n"
    assert not (repo / "fresh.txt").exists()


def test_release_control_import_plan_rejects_wrong_version(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.13"
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    artifact = downloads / f"chatgpt_claudecode_workflow_{version}.zip"
    _write_release_candidate_zip(artifact, version="v9.9.12")

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    result = subprocess.run(
        [str(script), "--version", version, "--downloads-dir", str(downloads), "--import-plan"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    payload = _extract_first_json_object(result.stdout)
    assert payload["ok"] is False
    assert "version_mismatch" in payload["errors"]


def test_release_control_import_plan_rejects_wrapper_missing_version_and_missing_script(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"

    scenarios = [
        ("v9.9.14", {"wrapper": True}, "wrapper_folder"),
        ("v9.9.15", {"include_version": False}, "missing_root_VERSION"),
        ("v9.9.16", {"include_script": False}, "candidate_script_missing"),
    ]
    for version, options, expected_error in scenarios:
        downloads = tmp_path / f"downloads-{version}"
        downloads.mkdir()
        artifact = downloads / f"chatgpt_claudecode_workflow_{version}.zip"
        _write_release_candidate_zip(artifact, version=version, **options)
        result = subprocess.run(
            [str(script), "--version", version, "--downloads-dir", str(downloads), "--import-plan"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode != 0
        payload = _extract_first_json_object(result.stdout)
        assert payload["ok"] is False
        assert expected_error in payload["errors"]


def test_release_control_stage0_fails_when_candidate_script_missing(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v9.9.17\n", encoding="utf-8")
    version = "v9.9.17"
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    artifact = downloads / f"chatgpt_claudecode_workflow_{version}.zip"
    _write_release_candidate_zip(artifact, version=version, include_script=False)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    result = subprocess.run(
        [str(script), "--version", version, "--downloads-dir", str(downloads)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "candidate ZIP does not contain chatgpt_claudecode_workflow_release_control.sh" in result.stderr


def test_release_control_delegates_to_candidate_script_before_install(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v9.9.11\n", encoding="utf-8")
    version = "v9.9.11"
    artifact = f"chatgpt_claudecode_workflow_{version}.zip"
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    import zipfile

    candidate_script = "#!/usr/bin/env bash\necho candidate-stage0:${PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0}:${PROMPTBRANCH_RELEASE_WORKFLOW_REPO_ROOT}\n"
    with zipfile.ZipFile(downloads / artifact, "w") as archive:
        archive.writestr("VERSION", f"{version}\n")
        archive.writestr("chatgpt_claudecode_workflow_release_control.sh", candidate_script)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    result = subprocess.run(
        [str(script), "--version", version, "--downloads-dir", str(downloads)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "== Delegate to workflow runner from candidate ZIP ==" in result.stdout
    assert f"candidate-stage0:1:{repo}" in result.stdout

def test_dockerfile_normalizes_app_permissions_for_non_root_runtime() -> None:
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY . ." in dockerfile
    assert "Normalize application source permissions for non-root runtime users" in dockerfile
    assert "find /app -type d -exec chmod 755" in dockerfile
    assert "find /app -type f -exec chmod 644" in dockerfile
    assert "chmod +x /app/docker/run-chatgpt-service-in-container.sh" in dockerfile
    assert "find /app -maxdepth 1 -type f -name '*.sh' -exec chmod +x" in dockerfile
    assert "find /app/scripts -type f -name '*.sh' -exec chmod +x" in dockerfile


def test_dockerignore_excludes_repo_generated_state_and_python_artifacts() -> None:
    root = Path(__file__).resolve().parents[1]
    patterns = set((root / ".dockerignore").read_text(encoding="utf-8").splitlines())

    expected = {
        ".pb_profile",
        "debug_artifacts",
        "profile",
        ".pb_profile_docker",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "*.pyc",
        "*.pyo",
        "*.log",
        "*.zip",
        "session_*.log",
        "task_*.show",
    }
    assert expected <= patterns


def test_release_control_import_preserves_debug_artifacts_in_plan_and_delete_filter() -> None:
    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    text = script.read_text(encoding="utf-8")

    assert 'local preserved_csv=".git,.env,.generated,.pb_profile,.pb_profile_local_debug,.pb_profile_local_debug_pools,profile,debug_artifacts"' in text
    assert '! -name "debug_artifacts"' in text
    assert "--exclude='debug_artifacts/'" in text
    assert "--exclude='.env'" in text
    assert "--exclude='.env.*'" in text
    assert 'required_root_files = ["VERSION", "pyproject.toml", ".gitignore", ".not_to_zip", ".promptbranch-repo.json", script_name]' in text
    assert 'verify_release_import_copied_entries "${download_zip}" "${repo_root}"' in text
    assert 'force_add_intentional_ignored_release_paths' in text
    assert 'assert_release_staging_safe' in text
    assert 'normalize_generated_ownership "pre-import"' in text
    assert 'normalize_generated_ownership "post-release"' in text
    assert "find \"${repo_root}\" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} +" in text
    assert "find \"${repo_root}/scripts\" -type f -name '*.sh' -exec chmod +x {} +" in text
    assert "find \"${repo_root}/docker\" -type f -name '*.sh' -exec chmod +x {} +" in text
    assert 'service script not executable and chmod failed' in text


def test_docker_service_runs_as_host_user_to_avoid_root_owned_artifacts() -> None:
    root = Path(__file__).resolve().parents[1]
    compose = (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")
    run_script = (root / "run_chatgpt_service.sh").read_text(encoding="utf-8")
    dev_script = (root / "run_chatgpt_service_dev.sh").read_text(encoding="utf-8")
    container_script = (root / "docker" / "run-chatgpt-service-in-container.sh").read_text(encoding="utf-8")

    assert 'user: "${PROMPTBRANCH_DOCKER_UID:-1000}:${PROMPTBRANCH_DOCKER_GID:-1000}"' in compose
    assert 'pull_policy: build' in compose
    assert 'PYTHONDONTWRITEBYTECODE: "1"' in compose
    assert 'export PROMPTBRANCH_DOCKER_UID="${PROMPTBRANCH_DOCKER_UID:-$(id -u)}"' in run_script
    assert 'export PROMPTBRANCH_DOCKER_GID="${PROMPTBRANCH_DOCKER_GID:-$(id -g)}"' in run_script
    assert 'export PROMPTBRANCH_DOCKER_UID="${PROMPTBRANCH_DOCKER_UID:-$(id -u)}"' in dev_script
    assert 'mkdir -p "${container_home}" "${container_cache}" "${container_config}" /app/.pb_profile /app/profile /app/debug_artifacts' in container_script
    assert 'PROMPTBRANCH_DOCKER_BROWSER_PROFILE:-standard-browser' in container_script
    assert 'docker-browser-parity' in container_script
    assert 'export PROMPTBRANCH_PROFILE_DIR="/app/profile"' in container_script



def test_release_control_recreates_docker_service_and_verifies_version() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    run_script = (root / "run_chatgpt_service.sh").read_text(encoding="utf-8")

    assert 'run_docker_compose down --remove-orphans' in script
    assert 'run_docker_compose build --pull' in script
    assert 'run_docker_compose up -d --no-build --force-recreate --remove-orphans' in script
    assert 'service_health_json="${release_log_dir}/promptbranch_service_health.${ver}.json"' in script
    assert 'service version mismatch: ' in script
    assert 'actual_normalized == expected_normalized' in script
    assert 'Docker container was not recreated' in script
    assert 'if ! deploy_promptbranch_service_detached; then' in script
    assert 'fail "Docker service recreate/version verification failed"' in script
    assert 'up --build --force-recreate "$@"' in run_script
    assert 'PROMPTBRANCH_SERVICE_IMAGE_TAG' in script
    assert 'promptbranch_service_image_ref' in script
    assert 'PROMPTBRANCH_SERVICE_IMAGE="${image_ref}"' in script
    assert 'PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE' in script
    assert 'release_version_plain_from_version_file' in script


def test_release_control_pins_compose_service_image_to_release_version() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    run_script = (root / "run_chatgpt_service.sh").read_text(encoding="utf-8")
    dev_script = (root / "run_chatgpt_service_dev.sh").read_text(encoding="utf-8")

    assert 'promptbranch_service_image_ref()' in script
    assert 'local default_image="promptbranch-service:${image_tag}"' in script
    assert 'PROMPTBRANCH_SERVICE_IMAGE="${image_ref}"' in script
    assert 'PROMPTBRANCH_SERVICE_IMAGE=%q' in script
    assert 'PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE' in script
    assert 'export PROMPTBRANCH_SERVICE_IMAGE="promptbranch-service:${PROMPTBRANCH_SERVICE_IMAGE_TAG}"' in run_script
    assert 'export PROMPTBRANCH_SERVICE_IMAGE="promptbranch-service:${PROMPTBRANCH_SERVICE_IMAGE_TAG}"' in dev_script



def test_docker_parity_check_exports_versioned_service_image_without_local_fallback() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "docker-browser-parity-cloudflare-check.sh").read_text(encoding="utf-8")
    compose = (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")

    assert 'export PROMPTBRANCH_SERVICE_IMAGE_TAG="$(promptbranch_service_image_tag)"' in script
    assert 'export PROMPTBRANCH_VERSION="${PROMPTBRANCH_VERSION:-${PROMPTBRANCH_SERVICE_IMAGE_TAG}}"' in script
    assert 'export PROMPTBRANCH_SERVICE_IMAGE="$(promptbranch_service_image_ref)"' in script
    assert "printf 'promptbranch-service:%s\\n'" in script
    assert 'promptbranch-service:local' not in script
    assert 'PROMPTBRANCH_VERSION: ${PROMPTBRANCH_VERSION:-local}' in compose
    assert 'image: ${PROMPTBRANCH_SERVICE_IMAGE:-promptbranch-service:${PROMPTBRANCH_VERSION:-local}}' in compose
    assert 'export PROMPTBRANCH_SERVICE_IMAGE="$(promptbranch_service_image_ref)"' in script
    assert '${PROMPTBRANCH_VERSION:-unknown}' not in compose



def test_release_control_uses_single_default_runtime_identity() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    compose = (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")
    run_script = (root / "run_chatgpt_service.sh").read_text(encoding="utf-8")

    assert 'runtime_mode="single_default"' in script
    assert 'compose_project_name="${PROMPTBRANCH_DEFAULT_COMPOSE_PROJECT_NAME:-${project_name}}"' in script
    assert 'service_port="${PROMPTBRANCH_DEFAULT_SERVICE_PORT:-8000}"' in script
    assert 'service_base_url="http://localhost:${service_port}"' in script
    assert '_out_args=(pb test full --project-name "${release_test_project_name}" --keep-project)' in script
    assert 'name: chatgpt_claudecode_workflow' in compose
    assert 'image: ${PROMPTBRANCH_SERVICE_IMAGE:-promptbranch-service:${PROMPTBRANCH_VERSION:-local}}' in compose
    assert '      - "8000:8000"' in compose
    assert 'export COMPOSE_PROJECT_NAME="chatgpt_claudecode_workflow"' in run_script
    assert 'export PROMPTBRANCH_SERVICE_PORT="8000"' in run_script
    assert 'release_version_plain_from_version_file VERSION' in run_script
    assert 'PROMPTBRANCH_SERVICE_IMAGE_TAG' in script
    assert 'export CHATGPT_SERVICE_BASE_URL="http://localhost:8000"' in run_script


def _release_control_health_probe_code() -> str:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    match = re.search(
        r"service_health_probe\(\) \{.*?<<'INNERPY'\n(?P<code>.*?)\nINNERPY\n\}",
        script,
        flags=re.DOTALL,
    )
    assert match is not None
    return match.group("code")


def test_release_control_health_probe_heredoc_is_valid_python() -> None:
    code = _release_control_health_probe_code()

    compile(code, "<release-control-service-health-probe>", "exec")
    assert 'handle.write("\\n")' in code


def test_release_control_health_probe_normalizes_v_prefixed_versions(tmp_path: Path, monkeypatch) -> None:
    import sys
    import urllib.request

    code = _release_control_health_probe_code()
    out_path = tmp_path / "health.json"

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"ok": True, "version": "v0.1.71.3"}).encode("utf-8")

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(sys, "argv", ["-", "0.1.71.3", str(out_path), "8000"])

    try:
        exec(compile(code, "<release-control-service-health-probe>", "exec"), {})
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("health probe did not exit")

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["version"] == "v0.1.71.3"


def test_release_control_health_probe_prefers_package_version_when_present(tmp_path: Path, monkeypatch) -> None:
    import sys
    import urllib.request

    code = _release_control_health_probe_code()
    out_path = tmp_path / "health.json"

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"ok": True, "package_version": "0.1.71.3", "version": "stale"}).encode("utf-8")

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(sys, "argv", ["-", "v0.1.71.3", str(out_path), "8000"])

    try:
        exec(compile(code, "<release-control-service-health-probe>", "exec"), {})
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("health probe did not exit")

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["package_version"] == "0.1.71.3"

def test_release_control_summary_mentions_service_health_artifact() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'service_health: $(summary_value "${service_summary_active}" "${service_health_json}")' in script
    assert 'compose_ps:     $(summary_value "${service_summary_active}" "${service_compose_ps_json}")' in script

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
        archive.writestr("pyproject.toml", f"[project]\nname = 'promptbranch'\nversion = '{version.lstrip('v')}'\n")
        archive.writestr(".gitignore", "*.zip\n.env\n.pb_profile/\ndebug_artifacts/\n")
        archive.writestr(".not_to_zip", "*.zip\n.env\n.pb_profile/\ndebug_artifacts/\n")
        archive.writestr(".promptbranch-repo.json", json.dumps({"schema_version": 1, "project_id": "g-p-demo", "project_home_url": "https://chatgpt.com/g/g-p-demo/project", "repo_id": "chatgpt_claudecode_workflow", "artifact_pattern": "chatgpt_claudecode_workflow_<version>.zip", "role": "release_authority"}))
        archive.writestr("chatgpt_claudecode_workflow_release_control.sh", "#!/usr/bin/env bash\n")

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
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
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
    assert "release_logs:" in result.stdout
    assert ".pb_profile/release_logs/v9.9.9/promptbranch-service.9.9.9.log" in result.stdout
    assert "service_start: skipped" in result.stdout
    call_text = calls.read_text(encoding="utf-8")
    assert "docker ps" in call_text
    assert "docker inspect deadbeef" in call_text
    assert "docker logs" not in call_text




def test_release_control_prunes_old_release_logs_only_when_requested(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.9"
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    _write_release_control_fake_commands(fake_bin, calls, version=version)

    release_root = repo / ".pb_profile" / "release_logs"
    old1 = release_root / "v0.0.190"
    old2 = release_root / "v0.0.191"
    current = release_root / version
    old1.mkdir(parents=True)
    old2.mkdir(parents=True)
    (old1 / "old.log").write_text("old1\n", encoding="utf-8")
    (old2 / "old.log").write_text("old2\n", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-prune.log"

    result = subprocess.run(
        [
            str(script),
            "--tests-only",
            "--version", version,
            "--prune-release-logs",
            "--release-log-keep", "1",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert current.is_dir()
    assert (current / "pb_test.full.v9.9.9.log").is_file()
    assert not old1.exists()
    assert not old2.exists()
    assert "Release log pruning completed" in result.stdout
    assert "log_prune:     keep=1" in result.stdout


def test_release_control_does_not_prune_release_logs_by_default(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.9"
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    _write_release_control_fake_commands(fake_bin, calls, version=version)

    release_root = repo / ".pb_profile" / "release_logs"
    old = release_root / "v0.0.190"
    old.mkdir(parents=True)
    (old / "old.log").write_text("old\n", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-no-prune.log"

    result = subprocess.run(
        [str(script), "--tests-only", "--version", version],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert old.is_dir()
    assert "log_prune:     skipped" in result.stdout

def test_release_control_writes_generated_logs_under_pb_profile() -> None:
    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    text = script.read_text(encoding="utf-8")

    assert 'release_log_root="${release_log_root_arg:-${repo_root}/.pb_profile/release_logs}"' in text
    assert 'release_log_dir="${release_log_root}/${ver}"' in text
    assert 'full_log="${release_log_dir}/pb_test.full.${ver}.log"' in text
    assert 'direct_full_log="${release_log_dir}/pb_test.full.direct.${ver}.log"' in text
    assert 'localhost_full_log="${release_log_dir}/pb_test.full.localhost.${ver}.log"' in text
    assert 'service_log="${release_log_dir}/promptbranch-service.${ver_plain}.log"' in text
    assert 'service_log:   $(summary_value "${docker_log_summary_active}" "${service_log}")' in text
    assert 'service_start: $(summary_value "${service_summary_active}" "${service_start_log}")' in text
    assert "--prune-release-logs" in text
    assert "--release-log-keep" in text
    assert 'log_prune:     $(summary_value "${prune_summary_active}" "keep=${release_log_keep}")' in text

def test_release_control_adopt_if_green_is_explicitly_guarded() -> None:
    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    text = script.read_text(encoding="utf-8")

    assert "--adopt-if-green" in text
    assert 'report_is_green "${selected_report_json}"' in text
    assert "adopt_current_artifact" in text
    assert "--adopt-if-green is only supported with --tests-only" in text
    assert "--tests-only = no baseline mutation" not in text  # behavior is enforced by explicit flag checks, not prose


def test_release_control_accepts_numeric_repair_version_for_adopt_current(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.9.1"
    artifact = f"repo_{version}.zip"
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

def test_release_control_renames_git_hash_packager_output_for_repair_version(tmp_path: Path):
    repo = tmp_path / "chatgpt_claudecode_workflow"
    repo.mkdir()
    version = "v9.9.9.1"
    artifact = f"chatgpt_claudecode_workflow_{version}.zip"
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    import zipfile

    with zipfile.ZipFile(downloads / artifact, "w") as archive:
        archive.writestr("VERSION", f"{version}\n")
        archive.writestr("pyproject.toml", f"[project]\nname = 'promptbranch'\nversion = '{version.lstrip('v')}'\n")
        archive.writestr(".gitignore", "*.zip\n.env\n.pb_profile/\ndebug_artifacts/\n")
        archive.writestr(".not_to_zip", "*.zip\n.env\n.pb_profile/\ndebug_artifacts/\n")
        archive.writestr(".promptbranch-repo.json", json.dumps({"schema_version": 1, "project_id": "g-p-demo", "project_home_url": "https://chatgpt.com/g/g-p-demo/project", "repo_id": "chatgpt_claudecode_workflow", "artifact_pattern": "chatgpt_claudecode_workflow_<version>.zip", "role": "release_authority"}))
        archive.writestr("chatgpt_claudecode_workflow_release_control.sh", "#!/usr/bin/env bash\n")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    _write_release_control_fake_commands(fake_bin, calls, version=version)
    (fake_bin / "git").write_text(
        "#!/usr/bin/env bash\n"
        "echo git \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1 $2 $3\" == \"rev-parse --short HEAD\" ]]; then echo abc1234; exit 0; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (fake_bin / "git").chmod(0o755)
    packager = tmp_path / "legacy-packager.sh"
    packager.write_text(
        "#!/usr/bin/env bash\n"
        "python3 - <<'INNERPY'\n"
        "import zipfile\n"
        "with zipfile.ZipFile('chatgpt_claudecode_workflow-abc1234.zip', 'w') as archive:\n"
        "    archive.writestr('VERSION', 'v9.9.9.1\\n')\n"
        "INNERPY\n",
        encoding="utf-8",
    )
    packager.chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"

    result = subprocess.run(
        [
            str(script),
            "--version", version,
            "--downloads-dir", str(downloads),
            "--packager", str(packager),
            "--skip-compare",
            "--skip-commit",
            "--skip-source-add",
            "--skip-install",
            "--skip-chown",
            "--skip-service",
            "--skip-docker-logs",
            "--skip-tests",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "ZIP verified" in result.stdout
    assert (repo / artifact).is_file()
    assert not (repo / "chatgpt_claudecode_workflow-abc1234.zip").exists()
    with zipfile.ZipFile(repo / artifact) as archive:
        assert archive.read("VERSION").decode("utf-8").strip() == version


def test_post_release_validation_script_runs_standard_sequence_with_fake_promptbranch(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.9.1"
    target = "v9.9.10"
    artifact = f"chatgpt_claudecode_workflow_{version}.zip"
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    import zipfile

    with zipfile.ZipFile(repo / artifact, "w") as archive:
        archive.writestr("VERSION", f"{version}\n")
        archive.writestr("promptbranch_version.py", "PACKAGE_VERSION = '9.9.9.1'\n")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    fake_promptbranch = fake_bin / "promptbranch"
    fake_promptbranch.write_text(
        "#!/usr/bin/env bash\n"
        "echo promptbranch \"$@\" >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1 $2\" == \"artifact current\" ]]; then echo '{\"ok\": true, \"action\": \"artifact_current\"}'; exit 0; fi\n"
        "if [[ \"$1\" == \"ask\" ]]; then echo '{\"ok\": true, \"action\": \"ask_protocol_run\", \"status\": \"reply_validated\", \"reply_status\": \"no_artifact\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact intake\" ]]; then echo '{\"ok\": true, \"action\": \"artifact_intake\", \"status\": \"no_artifact\", \"download_performed\": false}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact candidate-run\" ]]; then echo '{\"ok\": true, \"action\": \"artifact_candidate_run\", \"status\": \"candidate_next_inspection_required\", \"mode\": \"plan_only\", \"mutating_actions_executed\": false}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"'" + version + "'\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"release lifecycle-status\" ]]; then echo '{\"ok\": true, \"action\": \"release_lifecycle_status\", \"status\": \"passed\", \"severity\": \"ok\", \"lifecycle_phase\": \"adopted_current\", \"operator_verdict\": \"continue_normal_development\", \"warning_codes\": [], \"blocker_codes\": [], \"next_safe_action\": {\"kind\": \"continue_normal_development\"}}'; exit 0; fi\n"
        "echo unexpected promptbranch args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    fake_promptbranch.chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "scripts" / "post-release-validation.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)

    result = subprocess.run(
        [str(script), "--version", version, "--target-version", target, "--test-timeout", "5"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "post-release validation passed" in result.stdout
    log_dir = repo / ".pb_profile" / "release_logs" / version
    summary = json.loads((log_dir / f"post_release_validation.{version}.summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["version"] == version
    assert summary["target_version"] == target
    assert (log_dir / f"pb_ask_protocol_smoke.{version}.json").is_file()
    assert (log_dir / f"pb_artifact_intake_dry_run.{version}.json").is_file()
    assert (log_dir / f"pb_artifact_candidate_run.{version}.json").is_file()
    assert (log_dir / f"pb_test.full.{version}.report.json").is_file()
    assert (log_dir / f"zip_hygiene.{version}.json").is_file()
    assert (log_dir / f"pb_release_lifecycle_status.{version}.json").is_file()
    assert summary["steps"]["release_lifecycle_status"]["rc"] == 0
    assert summary["steps"]["release_lifecycle_status"]["performed"] is True
    assert summary["lifecycle_status_snapshot"]["lifecycle_phase"] == "adopted_current"
    assert summary["lifecycle_status_snapshot_path"].endswith(f"pb_release_lifecycle_status.{version}.json")

    call_text = calls.read_text(encoding="utf-8")
    assert "promptbranch artifact current --json" in call_text
    assert f"--target-version {target}" in call_text
    assert "promptbranch artifact intake --from-last-answer --dry-run --json" in call_text
    assert "promptbranch artifact candidate-run --json" in call_text
    assert "promptbranch test full --json" in call_text
    assert "promptbranch test report" in call_text
    assert f"promptbranch release lifecycle-status --version {version} --target-version {target}" in call_text
    assert "artifact adopt" not in call_text
    assert "src sync" not in call_text


def test_finalize_artifact_intake_mvp_delegates_to_candidate_run(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    fake_pb = tmp_path / "pb"
    calls = tmp_path / "candidate_run_calls.json"
    fake_pb.write_text(
        "#!/usr/bin/env bash\n"
        f"python3 - <<'PY' {str(calls)!r} \"$@\"\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        "Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))\n"
        "print(json.dumps({\n"
        "  'ok': True,\n"
        "  'action': 'artifact_candidate_run',\n"
        "  'status': 'candidate_run_cycle_acceptance_ready',\n"
        "  'mvp_complete': True,\n"
        "  'download_performed': True,\n"
        "  'verification_performed': True,\n"
        "  'migration_performed': True,\n"
        "  'candidate_test_performed': True,\n"
        "  'adoption_performed': False\n"
        "}))\n"
        "PY\n",
        encoding="utf-8",
    )
    fake_pb.chmod(0o755)
    script = Path(__file__).resolve().parents[1] / "scripts" / "finalize-artifact-intake-mvp.sh"

    result = subprocess.run(
        [
            str(script),
            "--version",
            "v9.9.9",
            "--target-version",
            "v9.9.10",
            "--candidate-mvp-max-steps",
            "6",
            "--candidate-run-step-timeout",
            "42",
            "--require-real-candidate-mvp",
            "--pb-cmd",
            str(fake_pb),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "final Artifact Intake MVP validation starting" in result.stdout
    assert "final Artifact Intake MVP validation passed" in result.stdout
    args = json.loads(calls.read_text(encoding="utf-8"))
    assert args == [
        "artifact",
        "candidate-run",
        "--execute-until-blocked",
        "--max-steps",
        "6",
        "--step-timeout",
        "42",
        "--require-complete",
        "--profile",
        "smoke",
        "--json",
        "--require-real-candidate",
    ]
    summary = json.loads((repo / ".pb_profile" / "release_logs" / "v9.9.9" / "finalize_artifact_intake_mvp.v9.9.9.summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["checks"]["download_performed"] is True
    assert summary["checks"]["verification_performed"] is True
    assert summary["checks"]["migration_performed"] is True
    assert summary["checks"]["candidate_test_passed"] is True


def test_finalize_artifact_intake_mvp_rejects_unrequested_adoption(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    fake_pb = tmp_path / "pb"
    fake_pb.write_text(
        "#!/usr/bin/env bash\n"
        "python3 - <<'PY'\n"
        "import json\n"
        "print(json.dumps({\n"
        "  'ok': True,\n"
        "  'status': 'candidate_run_cycle_completed',\n"
        "  'mvp_complete': True,\n"
        "  'download_performed': True,\n"
        "  'verification_performed': True,\n"
        "  'migration_performed': True,\n"
        "  'candidate_test_performed': True,\n"
        "  'adoption_performed': True\n"
        "}))\n"
        "PY\n",
        encoding="utf-8",
    )
    fake_pb.chmod(0o755)
    script = Path(__file__).resolve().parents[1] / "scripts" / "finalize-artifact-intake-mvp.sh"

    result = subprocess.run(
        [
            str(script),
            "--version",
            "v9.9.9",
            "--target-version",
            "v9.9.10",
            "--require-real-candidate-mvp",
            "--pb-cmd",
            str(fake_pb),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    summary = json.loads((repo / ".pb_profile" / "release_logs" / "v9.9.9" / "finalize_artifact_intake_mvp.v9.9.9.summary.json").read_text(encoding="utf-8"))
    assert "adoption_not_performed_without_explicit_flag" in summary["failures"]

def test_finalize_artifact_intake_mvp_rejects_conflicting_flags(tmp_path: Path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "finalize-artifact-intake-mvp.sh"

    result = subprocess.run(
        [str(script), "--version", "v9.9.9", "--target-version", "v9.9.10", "--skip-candidate-run"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "conflicts with final Artifact Intake MVP completion validation" in result.stderr



def test_release_control_required_control_files_and_staging_guard_present() -> None:
    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    text = script.read_text(encoding="utf-8")

    assert '".gitignore", ".not_to_zip"' in text
    assert 'protected_zip_entries_present' in text
    assert 'unsafe release-control staged paths detected' in text
    assert '.env|.env.*|.generated|.generated/*|.pb_profile' in text
    assert 'git add -f -- "${path}"' in text


def test_gitignore_allows_intentional_release_harness_and_metadata() -> None:
    gitignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")

    assert '# ollama_mcp_verification_harness/  # intentionally tracked release verification harness' in gitignore
    assert '# ollama_mcp_verification_harness_v2/  # intentionally tracked release verification harness' in gitignore
    assert '!promptbranch.egg-info/' in gitignore
    assert '!promptbranch.egg-info/**' in gitignore


def test_release_control_current_semantic_check_uses_repo_loop_entries() -> None:
    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    text = script.read_text(encoding="utf-8")
    assert 'scripts/verify-release-adoption-current.py' in text
    assert 'verify_current_matches_version "${current_json}" "${adoption_source_evidence_json}"' in text
    assert 'verify_current_matches_version "${current_json}"' in text


def test_post_release_validation_current_semantic_check_uses_repo_loop_entries() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "post-release-validation.sh"
    text = script.read_text(encoding="utf-8")
    assert text.count("def artifact_current_entries") >= 2
    assert 'result["checked_repos"]' in text
    assert 'result["matching_repos"]' in text
    assert '"field": "repos[*]"' in text


def test_release_control_accepts_multi_segment_repair_versions(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v0.1.78.2.1\n", encoding="utf-8")
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
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v0.1.78.2.1\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-multi-segment-version.log"

    result = subprocess.run(
        [str(script), "--tests-only", "--version", "v0.1.78.2.1"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "version:        v0.1.78.2.1" in result.stdout
    assert "version must be" not in result.stderr
    log_dir = repo / ".pb_profile" / "release_logs" / "v0.1.78.2.1"
    assert (log_dir / "pb_test.full.v0.1.78.2.1.log").is_file()
    assert (log_dir / "pb_test.full.v0.1.78.2.1.report.json").is_file()
    call_text = calls.read_text(encoding="utf-8")
    assert re.search(r"pb test full --project-name itest-promptbranch-v9-9-9-[0-9]{8}T[0-9]{6}Z-[0-9]+ --keep-project --fail-fast --json", call_text)
    assert "promptbranch src add" not in call_text


def test_release_control_run_all_tests_continues_and_writes_final_report(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".pb_profile_local_debug").mkdir()
    (repo / "VERSION").write_text("v9.9.9\n", encoding="utf-8")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "verify-sandbox-mutation-rollback-release-gate.py").write_text(
        "import json\nprint(json.dumps({'ok': True, 'status': 'sandbox_mutation_rollback_verified'}))\n",
        encoding="utf-8",
    )
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
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"login-check\" ]]; then echo 'login result: logged_in=True'; exit 0; fi\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"project-ensure\" ]]; then echo '{\"ok\": true, \"action\": \"project_ensure\", \"status\": \"resolved\", \"created\": true, \"project_name\": \"shared-test-project\", \"project_url\": \"https://chatgpt.com/g/g-p-shared/project\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.9\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test ask-live\" ]]; then echo '{\"ok\": true, \"profile\": \"ask-live\", \"status\": \"verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test visual-artifact-roundtrip\" ]]; then echo '{\"ok\": true, \"profile\": \"visual-artifact-roundtrip\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test release-live\" ]]; then echo '{\"ok\": true, \"profile\": \"release-live\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test import-smoke\" ]]; then echo '{\"ok\": true, \"action\": \"package_import_smoke\", \"status\": \"verified\", \"failures\": []}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact guard\" ]]; then echo '{\"ok\": true, \"status\": \"guard_passed\", \"failure_count\": 0}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-run-all-tests.log"

    result = subprocess.run(
        [str(script), "--tests-only", "--run-all-tests", "--version", "v9.9.9"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_dir = repo / ".pb_profile" / "release_logs" / "v9.9.9"
    summary_path = log_dir / "pb_test.all.v9.9.9.summary.json"
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["final_verdict"] == "GO"
    assert [step["name"] for step in summary["steps"]] == [
        "full_direct",
        "full_localhost",
        "sandbox_mutation_rollback_gate",
        "live_profile_preflight",
        "live_project_ensure",
        "ask_live",
        "visual_artifact_roundtrip",
        "release_live",
        "import_smoke",
        "artifact_guard",
    ]
    assert "run_all_tests:  1" in result.stdout
    assert f"all_tests_summary: {summary_path}" in result.stdout
    call_text = calls.read_text(encoding="utf-8")
    assert call_text.count("pb test full") == 2
    assert "full_localhost_policy: independent_execution_required" in result.stdout
    assert "full_localhost_direct_evidence_reuse: forbidden" in result.stdout
    assert "--skip source_add_text,source_remove_text" in call_text
    live_steps = {step["name"]: step for step in summary["steps"] if step["name"] in {"live_profile_preflight", "live_project_ensure", "ask_live", "visual_artifact_roundtrip", "release_live"}}
    assert live_steps
    assert all(step["status"] == "external_live_not_requested" for step in live_steps.values())
    assert summary["external_live_tests_requested"] is False
    assert summary["external_live_not_requested_steps"] == ["live_profile_preflight", "live_project_ensure", "ask_live", "visual_artifact_roundtrip", "release_live"]
    assert "pb --profile-dir ./.pb_profile_local_debug_pools/release-live/slots/slot-1 login-check" not in call_text
    assert "pb --profile-dir ./.pb_profile_local_debug_pools/release-live/slots/slot-1 project-ensure" not in call_text
    assert "pb test ask-live" not in call_text
    assert "pb test visual-artifact-roundtrip" not in call_text
    assert "pb test release-live" not in call_text
    assert "pb test import-smoke --json" in call_text
    assert "pb artifact guard --zip repo_v9.9.9.zip --version v9.9.9 --json" in call_text


def test_docker_build_context_version_guard_declared():
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    compose = (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")

    assert "PROMPTBRANCH_VERSION" in compose
    assert "PROMPTBRANCH_ARTIFACT_SHA256" in compose
    assert "ARG PROMPTBRANCH_VERSION" in dockerfile
    assert "LABEL promptbranch.version" in dockerfile
    assert "Docker build context version mismatch" in dockerfile
    assert "assert_host_build_context_versions" in script
    assert "docker_image_version_probe" in script
    assert "docker_container_version_probe" in script
    assert "docker_image_content" in script
    assert "docker_container_content" in script



def test_release_control_run_all_reuses_one_shared_live_project_url() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "run_all_ensure_shared_live_project" in script
    assert "one_run_scoped_project_for_all_test_all_live_steps" in script
    assert 'pb --profile-dir "${live_profile_pool_slot_dir}" project-ensure "${release_test_project_name}"' in script
    assert 'pb --profile-dir "${live_profile_pool_slot_dir}" project ensure "${release_test_project_name}"' not in script
    assert '--keep-open --json 2>&1 | tee -a ${run_all_project_ensure_log}' not in script
    assert 'pb test ask-live --profile-dir "${live_profile_pool_slot_dir}" --profile-lease' in script
    assert '--conversation-url "${run_all_shared_conversation_url}"' in script
    assert '--project-name "${release_test_project_name}" --keep-project --fail-fast --json' not in script.split("run_all_live_validation_steps", 1)[1]


def test_release_control_docker_probe_json_writers_have_valid_python_newline_literals():
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    escaped_newline_literal = "'" + "\\n" + "'"
    actual_newline_literal = "'" + "\n" + "'"
    assert "json.dumps(payload, indent=2, sort_keys=True) + " + escaped_newline_literal in script
    assert "sort_keys=True) + " + escaped_newline_literal + ", encoding='utf-8')" in script
    assert "sort_keys=True) + " + actual_newline_literal + "\n" not in script
    assert "sort_keys=True) + " + "'" + "\n\n" + "'" not in script

def test_release_control_docker_probe_pyproject_reader_is_shell_quoted_safely():
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'tomllib.load(open(/app/pyproject.toml, rb))' not in script
    assert 'awk -F' not in script or 'print \\$2' not in script
    assert 'grep -E "^version = " /app/pyproject.toml | head -n 1 | cut -d "\\\"" -f 2' in script

def test_release_control_run_all_has_rate_limit_retry_policy_declared():
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "PROMPTBRANCH_RUN_ALL_RATE_LIMIT_RETRIES" in script
    assert "PROMPTBRANCH_RUN_ALL_RATE_LIMIT_COOLDOWN_SECONDS" in script
    assert "run_all_log_has_rate_limit_evidence" in script
    assert "run_all_rate_limit_cooldown_sleep" in script
    assert 'RATE_LIMIT_STATUSES = {"rate_limited", "rate_limited_failed", "rate_limited_contaminated"}' in script
    assert 'value.get("rate_limit_modal_detected") is True' in script
    assert 'value.get("conversation_history_429_seen") is True' in script
    assert "structured-only" in script
    assert "tee -a" in script
    assert "retry after rate-limit cooldown" in script


def test_release_control_import_plan_preserves_live_seed_and_live_pool():
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'local preserved_csv=".git,.env,.generated,.pb_profile,.pb_profile_local_debug,.pb_profile_local_debug_pools,profile,debug_artifacts"' in script
    assert '! -name ".pb_profile_local_debug"' in script
    assert '! -name ".pb_profile_local_debug_pools"' in script
    assert "--exclude='.pb_profile_local_debug/'" in script
    assert "--exclude='.pb_profile_local_debug_pools/'" in script
    assert 'protected_zip_roots = [".env", ".generated", ".pb_profile", ".pb_profile_local_debug", ".pb_profile_local_debug_pools", "profile", "debug_artifacts"]' in script
    assert 'protected_roots = {".git", ".env", ".generated", ".pb_profile", ".pb_profile_local_debug", ".pb_profile_local_debug_pools", "profile", "debug_artifacts"}' in script
    assert '! -name ".promptbranch-repo.json"' not in script
    assert "--exclude='.promptbranch-repo.json'" not in script
    assert '".promptbranch-repo.json", script_name' in script


def test_release_control_run_all_defaults_text_source_to_compatibility_probe():
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "run_all_strict_source_kind_matrix" in script
    assert "PROMPTBRANCH_RUN_ALL_STRICT_SOURCE_KIND_MATRIX" in script
    assert "--strict-source-kind-matrix" in script
    assert "--skip source_add_text,source_remove_text" in script
    assert "text_source_compatibility: skipped_non_blocking" in script
    assert "text_source_compatibility_enable: --strict-source-kind-matrix" in script


def test_release_control_run_failing_tests_is_focused_text_source_mode():
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "--run-failing-tests" in script
    assert "run_failing_tests=1" in script
    assert "--only project_ensure,source_add_text" in script
    assert "focused_failing_tests: text_source_add_compatibility" in script
    assert "skipped_steps: live_profile_preflight, ask_live, visual_artifact_roundtrip, release_live, import_smoke, artifact_guard" in script


def test_release_control_rate_limit_detection_is_strict_not_generic():
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "structured-only" in script
    assert "rate[-_ ]limit|rate_limited|cooldown_seconds|cooldown_until" not in script
    detector = script.split("run_all_log_has_rate_limit_evidence()", 1)[1].split("run_all_log_has_live_bootstrap_guardrail()", 1)[0]
    assert "re.search" not in detector
    assert "raw_text.lower" not in detector
    assert 'value.get("rate_limit_modal_detected") is True' in detector
    assert 'value.get("conversation_history_429_seen") is True' in detector
    assert 'value.get("backend_api_guardrail_seen") is True' not in detector

def test_release_control_run_all_retries_unrecovered_rate_limited_step_once() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'run_all_rate_limit_retries="${PROMPTBRANCH_RUN_ALL_RATE_LIMIT_RETRIES:-1}"' in script
    assert "${attempt} -lt ${run_all_rate_limit_retries}" in script
    assert 'run_all_log_has_rate_limit_evidence "${step_log}"' in script
    assert "PROMPTBRANCH_RUN_ALL_RATE_LIMIT_SKIP_SLEEP" in script

def test_release_control_full_localhost_rate_limit_retry_is_denylisted_before_sleep():
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "run_all_step_disallows_browser_rate_limit_retry" in script
    assert "full_localhost|localhost|full_offline|offline" in script
    assert "full_direct|full_localhost" not in script
    assert "full_direct|" not in script.split("run_all_step_disallows_browser_rate_limit_retry()", 1)[1].split("run_all_rate_limit_cooldown_sleep()", 1)[0]
    assert "browser rate-limit cooldown retry denied for ${step_name}" in script
    assert "rate_limit_retry_denied_for_offline_step: ${step_name}" in script

    sleep_body = script.split("run_all_rate_limit_cooldown_sleep() {", 1)[1].split("build_run_all_full_test_args()", 1)[0]
    deny_index = sleep_body.index("run_all_step_disallows_browser_rate_limit_retry")
    generic_warn_index = sleep_body.index("WARN: rate-limit evidence detected for ${step_name}")
    assert deny_index < generic_warn_index

    assert 'if run_all_rate_limit_cooldown_sleep "full_${label}" "${selected_full_log}"; then' in script
    assert 'run_all_rate_limit_cooldown_sleep "full_${label}" "${selected_full_log}"\n    echo "== pb test transport retry after rate-limit cooldown: ${label} =="' not in script
    assert "suppressing rate-limit retry for full_${label}" in script




def test_release_control_all_tests_summary_prefers_top_level_recovered_ask_live_payload(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".pb_profile_local_debug").mkdir()
    (repo / "VERSION").write_text("v9.9.15\n", encoding="utf-8")
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

    recovered_payload = json.dumps(
        {
            "ok": True,
            "action": "test_ask_live",
            "profile": "ask-live",
            "status": "verified_with_recovered_rate_limit",
            "failure_count": 0,
            "functional_failure_count": 0,
            "profile_lease": {
                "ok": True,
                "action": "profile_lease",
                "status": "leased",
                "metadata": {
                    "pid": 123,
                    "action": "test_ask_live",
                    "profile_pool": "release-live",
                },
            },
            "steps": [
                {
                    "name": "plain",
                    "ok": True,
                    "status": "verified_with_recovered_rate_limit",
                    "functional_status": "verified",
                    "contains_expected_sentinel": True,
                }
            ],
            "rate_limit_telemetry": {
                "service_rate_limit_events": [
                    {"kind": "modal_acknowledged"},
                    {"kind": "modal_ack_wait_satisfied_cooldown"},
                ]
            },
        },
        separators=(",", ":"),
    )

    (fake_bin / "pb").write_text(
        "#!/usr/bin/env bash\n"
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"login-check\" ]]; then echo 'login result: logged_in=True'; exit 0; fi\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"project-ensure\" ]]; then echo '{\"ok\": true, \"action\": \"project_ensure\", \"status\": \"resolved\", \"created\": true, \"project_name\": \"shared-test-project\", \"project_url\": \"https://chatgpt.com/g/g-p-shared/project\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.15\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        f"if [[ \"$1 $2\" == \"test ask-live\" ]]; then echo '{recovered_payload}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test visual-artifact-roundtrip\" ]]; then echo '{\"ok\": true, \"profile\": \"visual-artifact-roundtrip\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test release-live\" ]]; then echo '{\"ok\": true, \"profile\": \"release-live\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test import-smoke\" ]]; then echo '{\"ok\": true, \"action\": \"package_import_smoke\", \"status\": \"verified\", \"failures\": []}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact guard\" ]]; then echo '{\"ok\": true, \"status\": \"guard_passed\", \"failure_count\": 0}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-run-all-top-level-recovered-ask-live.log"
    env["PROMPTBRANCH_RUN_ALL_RATE_LIMIT_SKIP_SLEEP"] = "1"

    subprocess.run(
        [str(script), "--tests-only", "--run-all-tests", "--version", "v9.9.15"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_dir = repo / ".pb_profile" / "release_logs" / "v9.9.15"
    summary = json.loads((log_dir / "pb_test.all.v9.9.15.summary.json").read_text(encoding="utf-8"))
    ask_step = next(step for step in summary["steps"] if step["name"] == "ask_live")
    assert summary["ok"] is True
    assert summary["final_verdict"] == "GO"
    assert ask_step["ok"] is True
    assert ask_step["status"] == "verified_with_recovered_rate_limit"
    assert ask_step["action"] == "test_ask_live"
    assert ask_step["recovered_rate_limit_success"] is True


def _run_release_control_with_fake_ask_live_payload(tmp_path: Path, *, version: str, payload: dict, ask_exit_code: int) -> tuple[subprocess.CompletedProcess[str], dict, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".pb_profile_local_debug").mkdir()
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
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

    ask_payload = json.dumps(payload, separators=(",", ":"))
    (fake_bin / "pb").write_text(
        "#!/usr/bin/env bash\n"
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"login-check\" ]]; then echo 'login result: logged_in=True'; exit 0; fi\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"project-ensure\" ]]; then echo '{\"ok\": true, \"action\": \"project_ensure\", \"status\": \"resolved\", \"created\": true, \"project_name\": \"shared-test-project\", \"project_url\": \"https://chatgpt.com/g/g-p-shared/project\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"'" + version + "'\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test ask-live\" ]]; then cat <<'ASKPAYLOAD'\n"
        + ask_payload
        + "\nASKPAYLOAD\nexit " + str(ask_exit_code) + "\nfi\n"
        "if [[ \"$1 $2\" == \"test visual-artifact-roundtrip\" ]]; then echo '{\"ok\": true, \"profile\": \"visual-artifact-roundtrip\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test release-live\" ]]; then echo '{\"ok\": true, \"profile\": \"release-live\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test import-smoke\" ]]; then echo '{\"ok\": true, \"action\": \"package_import_smoke\", \"status\": \"verified\", \"failures\": []}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact guard\" ]]; then echo '{\"ok\": true, \"status\": \"guard_passed\", \"failure_count\": 0}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = f"release-control-run-all-{version}.log"
    env["PROMPTBRANCH_RUN_ALL_RATE_LIMIT_SKIP_SLEEP"] = "1"
    env["PROMPTBRANCH_RUN_ALL_RATE_LIMIT_RETRIES"] = "0"

    result = subprocess.run(
        [str(script), "--tests-only", "--run-all-tests", "--version", version],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    log_dir = repo / ".pb_profile" / "release_logs" / version
    summary = json.loads((log_dir / f"pb_test.all.{version}.summary.json").read_text(encoding="utf-8"))
    return result, summary, calls.read_text(encoding="utf-8")


def test_release_control_all_tests_summary_accepts_ok_false_verified_recovered_ask_live_payload(tmp_path: Path):
    payload = {
        "ok": False,
        "action": "test_ask_live",
        "profile": "ask-live",
        "status": "verified_with_recovered_rate_limit",
        "failure_count": 1,
        "functional_failure_count": 0,
        "steps": [
            {
                "name": "plain",
                "ok": False,
                "status": "verified_with_recovered_rate_limit",
                "functional_status": "verified",
                "contains_expected_sentinel": True,
            }
        ],
        "rate_limit_telemetry": {
            "service_rate_limit_events": [
                {"kind": "modal_acknowledged"},
                {"kind": "modal_ack_wait_satisfied_cooldown"},
            ]
        },
    }

    result, summary, calls_text = _run_release_control_with_fake_ask_live_payload(
        tmp_path,
        version="v9.9.16",
        payload=payload,
        ask_exit_code=42,
    )

    assert result.returncode == 0
    assert summary["ok"] is True
    assert summary["final_verdict"] == "GO"
    ask_step = next(step for step in summary["steps"] if step["name"] == "ask_live")
    assert ask_step["ok"] is True
    assert ask_step["status"] == "verified_with_recovered_rate_limit"
    assert ask_step["action"] == "test_ask_live"
    assert ask_step["failure_count"] == 1
    assert ask_step["recovered_rate_limit_success"] is True
    assert calls_text.count("pb test ask-live") == 1
    assert "retry after rate-limit cooldown" not in result.stdout



def test_release_control_all_tests_summary_accepts_top_level_rate_limit_recovered_flag_without_modal_ack(tmp_path: Path):
    payload = {
        "ok": False,
        "action": "test_ask_live",
        "profile": "ask-live",
        "status": "verified_with_recovered_rate_limit",
        "failure_count": 1,
        "functional_failure_count": 0,
        "rate_limit_recovered": True,
        "steps": [
            {
                "name": "plain",
                "ok": False,
                "status": "rate_limited_contaminated",
                "functional_status": "verified",
                "contains_expected_sentinel": True,
            },
            {
                "name": "prompt_file_with_attachment",
                "ok": False,
                "status": "verified_with_recovered_rate_limit",
                "functional_status": "verified",
                "contains_expected_sentinel": True,
            },
        ],
        "rate_limit_telemetry": {
            "conversation_history_429_seen": True,
            "backend_api_guardrail_seen": True,
            "cooldown_wait_seconds_total": 842.789,
            "cooldown_wait_count": 5,
            "service_rate_limit_events": [
                {"kind": "conversation_history_rate_limit", "status": 429},
                {"kind": "backend_api_guardrail", "status": 429},
                {"kind": "cooldown_wait", "wait_seconds": 175.335},
            ],
        },
    }

    result, summary, calls_text = _run_release_control_with_fake_ask_live_payload(
        tmp_path,
        version="v9.9.18",
        payload=payload,
        ask_exit_code=42,
    )

    assert result.returncode == 0
    assert summary["ok"] is True
    assert summary["final_verdict"] == "GO"
    ask_step = next(step for step in summary["steps"] if step["name"] == "ask_live")
    assert ask_step["ok"] is True
    assert ask_step["status"] == "verified_with_recovered_rate_limit"
    assert ask_step["recovered_rate_limit_success"] is True
    assert calls_text.count("pb test ask-live") == 1

def test_release_control_all_tests_summary_rejects_verified_recovered_ask_live_with_functional_failure(tmp_path: Path):
    payload = {
        "ok": False,
        "action": "test_ask_live",
        "profile": "ask-live",
        "status": "verified_with_recovered_rate_limit",
        "failure_count": 1,
        "functional_failure_count": 1,
        "steps": [
            {
                "name": "plain",
                "ok": False,
                "status": "verified_with_recovered_rate_limit",
                "functional_status": "failed",
                "contains_expected_sentinel": False,
            }
        ],
        "rate_limit_telemetry": {
            "service_rate_limit_events": [
                {"kind": "modal_acknowledged"},
                {"kind": "modal_ack_wait_satisfied_cooldown"},
            ]
        },
    }

    result, summary, calls_text = _run_release_control_with_fake_ask_live_payload(
        tmp_path,
        version="v9.9.17",
        payload=payload,
        ask_exit_code=42,
    )

    assert result.returncode != 0
    assert summary["ok"] is False
    assert summary["final_verdict"] == "FIX"
    ask_step = next(step for step in summary["steps"] if step["name"] == "ask_live")
    assert ask_step["ok"] is False
    assert ask_step["status"] == "verified_with_recovered_rate_limit"
    assert ask_step["recovered_rate_limit_success"] is False
    assert "ask_live" in {step["name"] for step in summary["failed_steps"]}
    assert calls_text.count("pb test ask-live") >= 1


def test_release_control_run_all_does_not_retry_recovered_rate_limited_step(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".pb_profile_local_debug").mkdir()
    (repo / "VERSION").write_text("v9.9.11\n", encoding="utf-8")
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
    recovered_payload = (
        '{"ok": false, "action": "test_ask_live", "profile": "ask-live", '
        '"status": "rate_limited_contaminated", "failure_count": 1, '
        '"functional_failure_count": 0, '
        '"steps": [{"name": "plain", "ok": false, "status": "rate_limited_contaminated", '
        '"functional_status": "verified", "contains_expected_sentinel": true}], '
        '"rate_limit_telemetry": {"service_rate_limit_events": ['
        '{"kind": "modal_acknowledged"}, '
        '{"kind": "modal_ack_wait_satisfied_cooldown"}, '
        '{"kind": "cooldown_wait_satisfied_by_modal_ack_wait"}]}}'
    )
    (fake_bin / "pb").write_text(
        "#!/usr/bin/env bash\n"
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"login-check\" ]]; then echo 'login result: logged_in=True'; exit 0; fi\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"project-ensure\" ]]; then echo '{\"ok\": true, \"action\": \"project_ensure\", \"status\": \"resolved\", \"created\": true, \"project_name\": \"shared-test-project\", \"project_url\": \"https://chatgpt.com/g/g-p-shared/project\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.11\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        f"if [[ \"$1 $2\" == \"test ask-live\" ]]; then echo '{recovered_payload}'; exit 42; fi\n"
        "if [[ \"$1 $2\" == \"test visual-artifact-roundtrip\" ]]; then echo '{\"ok\": true, \"profile\": \"visual-artifact-roundtrip\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test release-live\" ]]; then echo '{\"ok\": true, \"profile\": \"release-live\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test import-smoke\" ]]; then echo '{\"ok\": true, \"action\": \"package_import_smoke\", \"status\": \"verified\", \"failures\": []}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact guard\" ]]; then echo '{\"ok\": true, \"status\": \"guard_passed\", \"failure_count\": 0}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-run-all-recovered-rate-limit.log"
    env["PROMPTBRANCH_RUN_ALL_RATE_LIMIT_SKIP_SLEEP"] = "1"

    result = subprocess.run(
        [str(script), "--tests-only", "--run-all-tests", "--version", "v9.9.11"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_dir = repo / ".pb_profile" / "release_logs" / "v9.9.11"
    summary = json.loads((log_dir / "pb_test.all.v9.9.11.summary.json").read_text(encoding="utf-8"))
    ask_log = (log_dir / "pb_test.ask_live.v9.9.11.log").read_text(encoding="utf-8")
    calls_text = calls.read_text(encoding="utf-8")
    assert summary["ok"] is True
    assert summary["final_verdict"] == "GO"
    ask_step = next(step for step in summary["steps"] if step["name"] == "ask_live")
    assert ask_step["ok"] is True
    assert ask_step["status"] == "verified_with_recovered_rate_limit"
    assert ask_step["recovered_rate_limit_success"] is True
    assert "recovered rate-limit evidence detected for ask_live" in ask_log
    assert "retry after rate-limit cooldown" not in ask_log
    assert calls_text.count("pb test ask-live") == 1
    assert "WARN: rate-limit evidence detected for ask_live" not in result.stdout



def test_release_control_live_project_ensure_accepts_recovered_rate_limit_with_project_url(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".pb_profile_local_debug").mkdir()
    (repo / "VERSION").write_text("v9.9.14\n", encoding="utf-8")
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
    project_payload = (
        '{"ok": true, "action": "ensure_project", "status": "verified", '
        '"project_name": "shared-test-project", '
        '"project_url": "https://chatgpt.com/g/g-p-shared/project", '
        '"rate_limit_summary": {"conversation_history_429_seen": true, '
        '"service_rate_limit_events": [{"kind": "modal_acknowledged"}, '
        '{"kind": "modal_ack_wait_satisfied_cooldown"}]}}'
    )
    (fake_bin / "pb").write_text(
        "#!/usr/bin/env bash\n"
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"login-check\" ]]; then echo 'login result: logged_in=True'; exit 0; fi\n"
        f"if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"project-ensure\" ]]; then echo '{project_payload}'; echo '{{\"kind\": \"modal_acknowledged\"}}'; exit 42; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.14\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test ask-live\" ]]; then echo '{\"ok\": true, \"profile\": \"ask-live\", \"status\": \"verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test visual-artifact-roundtrip\" ]]; then echo '{\"ok\": true, \"profile\": \"visual-artifact-roundtrip\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test release-live\" ]]; then echo '{\"ok\": true, \"profile\": \"release-live\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test import-smoke\" ]]; then echo '{\"ok\": true, \"action\": \"package_import_smoke\", \"status\": \"verified\", \"failures\": []}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact guard\" ]]; then echo '{\"ok\": true, \"status\": \"guard_passed\", \"failure_count\": 0}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-live-project-ensure-recovered-rate-limit.log"
    env["PROMPTBRANCH_RUN_ALL_RATE_LIMIT_SKIP_SLEEP"] = "1"

    result = subprocess.run(
        [str(script), "--tests-only", "--run-all-tests", "--version", "v9.9.14"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_dir = repo / ".pb_profile" / "release_logs" / "v9.9.14"
    summary = json.loads((log_dir / "pb_test.all.v9.9.14.summary.json").read_text(encoding="utf-8"))
    ensure_log = (log_dir / "pb_test.live_project_ensure.v9.9.14.log").read_text(encoding="utf-8")
    calls_text = calls.read_text(encoding="utf-8")

    assert summary["ok"] is True
    assert summary["final_verdict"] == "GO"
    ensure_step = next(step for step in summary["steps"] if step["name"] == "live_project_ensure")
    assert ensure_step["ok"] is True
    assert ensure_step["exit_code"] == 0
    assert "shared_live_project_url: https://chatgpt.com/g/g-p-shared/project" in ensure_log
    assert "verified_with_recovered_rate_limit" in ensure_log
    assert "project_url was verified" in ensure_log
    assert "live_project_ensure failed" not in result.stderr
    assert calls_text.count("pb test ask-live") == 1
    assert "--conversation-url https://chatgpt.com/g/g-p-shared/project" in calls_text

def test_release_control_declares_browser_read_timeout_service_recovery() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "run_all_log_has_browser_read_timeout" in script
    assert "run_all_recover_service_after_browser_read_timeout" in script
    assert "service_client_read_timeout" in script
    assert "The browser service may still finish after the CLI timed out" in script
    assert "release-control will recover the Promptbranch service before the next browser-backed phase" in script
    assert "live_profile_preflight retry after service recovery" in script


def test_release_control_retries_live_preflight_once_after_browser_read_timeout(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".pb_profile_local_debug").mkdir()
    (repo / "VERSION").write_text("v9.9.12\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    login_counter = tmp_path / "login_counter"

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
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"login-check\" ]]; then n=$(cat \"$PB_FAKE_LOGIN_COUNTER\" 2>/dev/null || echo 0); n=$((n+1)); echo $n > \"$PB_FAKE_LOGIN_COUNTER\"; if [[ $n -eq 1 ]]; then echo 'service_client_read_timeout: timed out'; echo 'The browser service may still finish after the CLI timed out.'; exit 42; fi; echo 'login result: logged_in=True'; exit 0; fi\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"project-ensure\" ]]; then echo '{\"ok\": true, \"action\": \"project_ensure\", \"status\": \"resolved\", \"created\": true, \"project_name\": \"shared-test-project\", \"project_url\": \"https://chatgpt.com/g/g-p-shared/project\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.12\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test ask-live\" ]]; then echo '{\"ok\": true, \"profile\": \"ask-live\", \"status\": \"verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test visual-artifact-roundtrip\" ]]; then echo '{\"ok\": true, \"profile\": \"visual-artifact-roundtrip\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test release-live\" ]]; then echo '{\"ok\": true, \"profile\": \"release-live\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test import-smoke\" ]]; then echo '{\"ok\": true, \"action\": \"package_import_smoke\", \"status\": \"verified\", \"failures\": []}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact guard\" ]]; then echo '{\"ok\": true, \"status\": \"guard_passed\", \"failure_count\": 0}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PB_FAKE_LOGIN_COUNTER"] = str(login_counter)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-live-preflight-recovery.log"

    result = subprocess.run(
        [str(script), "--tests-only", "--run-all-tests", "--version", "v9.9.12"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    log_dir = repo / ".pb_profile" / "release_logs" / "v9.9.12"
    summary = json.loads((log_dir / "pb_test.all.v9.9.12.summary.json").read_text(encoding="utf-8"))
    preflight_log = (log_dir / "pb_test.live_profile_preflight.v9.9.12.log").read_text(encoding="utf-8")
    calls_text = calls.read_text(encoding="utf-8")
    assert summary["ok"] is True
    assert summary["final_verdict"] == "GO"
    preflight_step = next(step for step in summary["steps"] if step["name"] == "live_profile_preflight")
    assert preflight_step["ok"] is True
    assert preflight_step["status"] == "verified"
    assert login_counter.read_text(encoding="utf-8").strip() == "2"
    assert "live_profile_preflight retry after service recovery" in preflight_log
    assert "service_recovery: skipped_skip_service" in preflight_log
    assert calls_text.count("pb --profile-dir ./.pb_profile_local_debug_pools/release-live/slots/slot-1 login-check") == 2
    assert "browser ReadTimeout detected for live_profile_preflight" in result.stdout + result.stderr


def test_release_control_marks_full_transport_read_timeout_for_service_recovery(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".pb_profile_local_debug").mkdir()
    (repo / "VERSION").write_text("v9.9.13\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    full_counter = tmp_path / "full_counter"

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
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"login-check\" ]]; then echo 'login result: logged_in=True'; exit 0; fi\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"project-ensure\" ]]; then echo '{\"ok\": true, \"action\": \"project_ensure\", \"status\": \"resolved\", \"created\": true, \"project_name\": \"shared-test-project\", \"project_url\": \"https://chatgpt.com/g/g-p-shared/project\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then n=$(cat \"$PB_FAKE_FULL_COUNTER\" 2>/dev/null || echo 0); n=$((n+1)); echo $n > \"$PB_FAKE_FULL_COUNTER\"; if [[ $n -eq 1 ]]; then echo '{\"ok\": false, \"section\": \"browser\", \"name\": \"ask_question\", \"status\": \"ReadTimeout\", \"diagnostic\": \"timed out\"}'; exit 42; fi; echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.13\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test ask-live\" ]]; then echo '{\"ok\": true, \"profile\": \"ask-live\", \"status\": \"verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test visual-artifact-roundtrip\" ]]; then echo '{\"ok\": true, \"profile\": \"visual-artifact-roundtrip\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test release-live\" ]]; then echo '{\"ok\": true, \"profile\": \"release-live\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test import-smoke\" ]]; then echo '{\"ok\": true, \"action\": \"package_import_smoke\", \"status\": \"verified\", \"failures\": []}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact guard\" ]]; then echo '{\"ok\": true, \"status\": \"guard_passed\", \"failure_count\": 0}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PB_FAKE_FULL_COUNTER"] = str(full_counter)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = "release-control-full-timeout-recovery.log"

    result = subprocess.run(
        [str(script), "--tests-only", "--run-all-tests", "--version", "v9.9.13"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    log_dir = repo / ".pb_profile" / "release_logs" / "v9.9.13"
    summary = json.loads((log_dir / "pb_test.all.v9.9.13.summary.json").read_text(encoding="utf-8"))
    direct_log = (log_dir / "pb_test.full.direct.v9.9.13.log").read_text(encoding="utf-8")
    assert summary["ok"] is False
    assert summary["final_verdict"] == "FIX"
    direct_step = next(step for step in summary["steps"] if step["name"] == "full_direct")
    assert direct_step["ok"] is False
    assert "recovery_reason: browser_read_timeout" in direct_log
    assert "service_recovery: skipped_skip_service" in direct_log
    assert "browser ReadTimeout detected for full_direct" in result.stdout + result.stderr
    assert calls.read_text(encoding="utf-8").count("pb test full") == 2

def test_prompt_file_live_smoke_script_validates_button_first_submit_contract():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "smoke-pb-ask-prompt-file.sh"
    content = script.read_text(encoding="utf-8")

    assert script.exists()
    assert os.access(script, os.X_OK)
    assert 'pb ask "Use the prompt file." --prompt-file "$tmp_prompt" --json > "$out_json"' in content
    assert "pb_ask_exit_code" in content
    assert "diagnostic JSON kept at" in content
    assert "CV_LIVE_PROMPT_FILE_OK" in content
    assert 'EXPECTED_TOKEN = "CV_LIVE_PROMPT_FILE_OK"' in content
    assert 'answer_obj.get("token")' in content
    assert 'ask_phase_timings = payload.get("ask_phase_timings")' in content
    assert 'prefer_button_submit is not true' in content
    assert 'submit_method not in {"button_click", "button_after_focus_retry", "send_button_click"}' in content
    assert "prepare_token_set_not_consumed remained unresolved" in content


def test_release_control_adopt_after_validation_rejects_skip_source_add_before_tests(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.91.1"
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls = tmp_path / "calls.log"
    _write_release_control_fake_commands(fake_bin, calls, version=version)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"

    result = subprocess.run(
        [
            str(script),
            "--version", version,
            "--skip-source-add",
            "--run-tests",
            "--adopt-after-validation",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "requires the current run's authoritative Project Source upload" in result.stderr
    call_text = calls.read_text(encoding="utf-8") if calls.exists() else ""
    assert "pb test full" not in call_text
    assert "pb artifact adopt" not in call_text


def test_release_control_adoption_identity_preflight_precedes_expensive_tests() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    source_add_index = script.index('promptbranch src add "${canonical_artifact_zip}" --json')
    preflight_call_index = script.index('release_control_capture_source_evidence_and_join_identity \\', source_add_index)
    test_index = script.index('if [[ ${skip_tests} -eq 0 ]]; then')
    assert source_add_index < preflight_call_index < test_index
    assert 'pb project join \\' in script
    assert '--source-evidence-json "${adoption_source_evidence_json}"' in script
    assert 'assigned_source_filename:' in script
    assert 'processed_file_id:' in script
    assert 'library_metadata_object_id:' in script

def test_release_control_rejects_adopt_after_validation_without_tests(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "VERSION").write_text("v9.9.92\n", encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"

    result = subprocess.run(
        [str(script), "--version", "v9.9.92", "--adopt-after-validation", "--skip-tests"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "--adopt-after-validation requires --run-tests or --run-all-tests" in result.stderr


def _run_release_control_with_fake_full_payloads(
    tmp_path: Path,
    *,
    version: str,
    direct_payload: dict,
    direct_exit_code: int,
    localhost_payload: dict,
    localhost_exit_code: int,
) -> tuple[subprocess.CompletedProcess[str], dict, str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".pb_profile_local_debug").mkdir()
    (repo / "VERSION").write_text(f"{version}\n", encoding="utf-8")
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

    direct_json = json.dumps(direct_payload, separators=(",", ":"))
    localhost_json = json.dumps(localhost_payload, separators=(",", ":"))
    report_json = json.dumps(
        {
            "ok": True,
            "action": "test_report",
            "status": "verified",
            "failure_count": 0,
            "suite": {
                "release_validation_groups": {
                    "ok": True,
                    "missing_required_groups": [],
                    "groups": {
                        "artifact_json_contracts": {"ok": True},
                        "browser_scheduler_source_lifecycle": {"ok": True},
                        "project_control_surface": {"ok": True},
                    },
                }
            },
        },
        separators=(",", ":"),
    )
    (fake_bin / "pb").write_text(
        "#!/usr/bin/env bash\n"
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"login-check\" ]]; then echo 'login result: logged_in=True'; exit 0; fi\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"project-ensure\" ]]; then echo '{\"ok\": true, \"action\": \"project_ensure\", \"status\": \"resolved\", \"created\": true, \"project_name\": \"shared-test-project\", \"project_url\": \"https://chatgpt.com/g/g-p-shared/project\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then\n"
        "  if [[ \"${CHATGPT_SERVICE_BASE_URL:-}\" == \"http://127.0.0.1:8000\" ]]; then cat <<'LOCALHOSTPAYLOAD'\n"
        + localhost_json
        + "\nLOCALHOSTPAYLOAD\n  exit "
        + str(localhost_exit_code)
        + "\n  fi\n  cat <<'DIRECTPAYLOAD'\n"
        + direct_json
        + "\nDIRECTPAYLOAD\n  exit "
        + str(direct_exit_code)
        + "\nfi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then cat <<'REPORTJSON'\n"
        + report_json
        + "\nREPORTJSON\nexit 0\nfi\n"
        "if [[ \"$1 $2\" == \"test ask-live\" ]]; then echo '{\"ok\": true, \"action\": \"test_ask_live\", \"profile\": \"ask-live\", \"status\": \"verified\", \"failure_count\": 0}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test visual-artifact-roundtrip\" ]]; then echo '{\"ok\": true, \"profile\": \"visual-artifact-roundtrip\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test release-live\" ]]; then echo '{\"ok\": true, \"profile\": \"release-live\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test import-smoke\" ]]; then echo '{\"ok\": true, \"action\": \"package_import_smoke\", \"status\": \"verified\", \"failures\": []}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact guard\" ]]; then echo '{\"ok\": true, \"status\": \"guard_passed\", \"failure_count\": 0}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    env["PROMPTBRANCH_TEST_SESSION_LOG"] = f"release-control-run-all-{version}.log"
    env["PROMPTBRANCH_RUN_ALL_RATE_LIMIT_SKIP_SLEEP"] = "1"

    result = subprocess.run(
        [str(script), "--tests-only", "--run-all-tests", "--strict-source-kind-matrix", "--version", version],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    log_dir = repo / ".pb_profile" / "release_logs" / version
    summary = json.loads((log_dir / f"pb_test.all.{version}.summary.json").read_text(encoding="utf-8"))
    return result, summary, calls.read_text(encoding="utf-8"), log_dir


def test_release_control_all_tests_summary_diagnoses_source_add_readtimeout_by_transport(tmp_path: Path):
    result, summary, _calls_text, log_dir = _run_release_control_with_fake_full_payloads(
        tmp_path,
        version="v9.9.18",
        direct_payload={
            "ok": False,
            "action": "test_suite",
            "status": "failed",
            "section": "browser",
            "name": "project_source_add_text",
            "diagnostic": "ReadTimeout timed out while waiting for Project Source persistence",
            "failures": [
                {
                    "section": "browser",
                    "name": "project_source_add_text",
                    "status": "ReadTimeout",
                    "diagnostic": "timed out",
                }
            ],
        },
        direct_exit_code=42,
        localhost_payload={"ok": True, "action": "test_suite", "status": "verified", "version": "v9.9.18"},
        localhost_exit_code=0,
    )

    assert result.returncode != 0
    assert summary["final_verdict"] == "FIX"
    direct_step = next(step for step in summary["steps"] if step["name"] == "full_direct")
    direct_diag = direct_step["diagnostics"]
    assert direct_diag["transport_class"] == "direct_browser_service"
    assert direct_diag["browser_read_timeout_detected"] is True
    assert direct_diag["source_add_timeout_detected"] is True
    assert direct_diag["likely_failure_phase"] == "project_source_add_read_timeout"
    assert direct_diag["next_action"] == "inspect_source_add_timing_and_browser_service_log"
    assert "full_direct" in summary["diagnostics"]["source_add_timeout_steps"]

    full_summary = json.loads((log_dir / "post_release_validation.direct.v9.9.18.summary.json").read_text(encoding="utf-8"))
    assert full_summary["diagnostics"]["source_add_timeout_detected"] is True
    assert full_summary["diagnostics"]["likely_failure_phase"] == "project_source_add_read_timeout"


def test_release_control_all_tests_summary_diagnoses_localhost_rate_limit_retry_denial(tmp_path: Path):
    result, summary, _calls_text, _log_dir = _run_release_control_with_fake_full_payloads(
        tmp_path,
        version="v9.9.19",
        direct_payload={"ok": False, "action": "test_suite", "status": "failed", "version": "v9.9.19"},
        direct_exit_code=42,
        localhost_payload={
            "ok": False,
            "action": "test_suite",
            "status": "rate_limited_failed",
            "rate_limit_summary": {
                "status": "rate_limited_failed",
                "blocking": True,
                "rate_limit_modal_detected": True,
                "conversation_history_429_seen": True,
            },
        },
        localhost_exit_code=42,
    )

    assert result.returncode != 0
    assert "waiting 190s before retry" not in result.stdout + result.stderr
    localhost_step = next(step for step in summary["steps"] if step["name"] == "full_localhost")
    localhost_diag = localhost_step["diagnostics"]
    assert localhost_diag["transport_class"] == "localhost"
    assert localhost_diag["rate_limit_evidence_detected"] is True
    assert localhost_diag["rate_limit_retry_allowed"] is False
    assert localhost_diag["rate_limit_retry_denied"] is True
    assert localhost_diag["likely_failure_phase"] == "rate_limit_blocking_or_contaminated"
    assert "full_localhost" in summary["diagnostics"]["rate_limit_retry_denied_steps"]


def test_new_task_smoke_script_uses_schema_v2_current_conversation_path():
    script = Path(__file__).resolve().parents[1] / "scripts" / "smoke-pb-ask-new-task.sh"
    text = script.read_text(encoding="utf-8")
    assert "pb ask --new-task" in text
    assert "jq -r '.current.conversation_url // empty'" in text
    assert "jq -r '.conversation_url // empty'" not in text
    assert 'test -n "$after"' not in text  # script uses bash [[ ]] form, not stale copied one-liner
    assert '[[ -n "$after" && "$before" != "$after" ]]' in text
    assert "sentinel_ok=1" in text
    assert "new_task_state_ok=1" in text



def test_release_control_declares_validation_evidence_reuse_fail_closed_contract():
    script_path = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    text = script_path.read_text(encoding="utf-8")
    assert "promptbranch.release_control.validation_evidence" in text
    assert "validation_evidence_dir=" in text
    assert "full_direct_validation_evidence_json=" in text
    assert "validate_release_validation_reuse_evidence" in text
    assert "artifact_sha256" in text
    assert "command_signature" in text
    assert "strict_source_kind_matrix" in text
    assert "runtime_mode" in text
    assert "service_base" in text
    assert "validation_evidence_reuse: reused full_direct" in text
    assert "write_reused_full_test_summary" in text
    assert "reused_validation_evidence" in text


def test_release_control_all_tests_summary_reports_validation_reuse_groups():
    script_path = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    text = script_path.read_text(encoding="utf-8")
    assert "promptbranch.release_control.validation_reuse_summary" in text
    assert '"reused_groups": reused_groups' in text
    assert '"executed_groups": executed_groups' in text
    assert '"invalidated_groups": []' in text
    assert '"failed_groups": [step["name"] for step in failed]' in text
    assert '"validation_reuse": validation_reuse_summary' in text


def test_release_control_run_all_reuses_prior_run_tests_direct_evidence_and_audits_localhost(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".pb_profile_local_debug").mkdir()
    (repo / "VERSION").write_text("v9.9.91\n", encoding="utf-8")
    log_dir = repo / ".pb_profile" / "release_logs" / "v9.9.91"
    evidence_dir = log_dir / "validation_evidence"
    evidence_dir.mkdir(parents=True)
    evidence_path = evidence_dir / "full_direct.v9.9.91.json"
    evidence_path.write_text(
        json.dumps(
            {
                "schema": "promptbranch.release_control.validation_evidence",
                "schema_version": "1.0",
                "ok": True,
                "status": "passed",
                "version": "v9.9.91",
                "artifact": "repo_v9.9.91.zip",
                "artifact_sha256": "missing",
                "test_group_id": "full_direct",
                "transport": "direct",
                "service_base": "http://localhost:8000",
                "runtime_mode": "single_default",
                "strict_source_kind_matrix": True,
                "command_signature": "pb test full --keep-project --fail-fast --json --source-kind-matrix=strict --run-failing-tests=0 --duplicate-release-validation-groups-skip=0",
                "test_exit_code": 0,
                "report_exit_code": 0,
                "release_validation_groups_ok": True,
                "summary_json": str(log_dir / "post_release_validation.v9.9.91.summary.json"),
                "full_log": str(log_dir / "pb_test.full.v9.9.91.log"),
                "report_json": str(log_dir / "pb_test.full.v9.9.91.report.json"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

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
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} PROMPTBRANCH_RELEASE_VALIDATION_GROUPS_SKIP_DUPLICATE=${PROMPTBRANCH_RELEASE_VALIDATION_GROUPS_SKIP_DUPLICATE:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"login-check\" ]]; then echo 'login result: logged_in=True'; exit 0; fi\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"project-ensure\" ]]; then echo '{\"ok\": true, \"action\": \"project_ensure\", \"status\": \"resolved\", \"created\": false, \"project_name\": \"shared-test-project\", \"project_url\": \"https://chatgpt.com/g/g-p-shared/project\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.91\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"rate_limit_summary\": {\"status\": \"none\", \"cooldown_wait_seconds_total\": 0, \"cooldown_wait_count\": 0}, \"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test ask-live\" ]]; then echo '{\"ok\": true, \"profile\": \"ask-live\", \"status\": \"verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test visual-artifact-roundtrip\" ]]; then echo '{\"ok\": true, \"profile\": \"visual-artifact-roundtrip\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test release-live\" ]]; then echo '{\"ok\": true, \"profile\": \"release-live\", \"status\": \"verified\", \"download_status\": \"downloaded\", \"verification_status\": \"smoke_zip_verified\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test import-smoke\" ]]; then echo '{\"ok\": true, \"action\": \"package_import_smoke\", \"status\": \"verified\", \"failures\": []}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact guard\" ]]; then echo '{\"ok\": true, \"status\": \"guard_passed\", \"failure_count\": 0}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    result = subprocess.run(
        [str(script), "--tests-only", "--run-all-tests", "--strict-source-kind-matrix", "--version", "v9.9.91"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    summary = json.loads((log_dir / "pb_test.all.v9.9.91.summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["validation_reuse"]["reused_groups"] == ["full_direct"]
    assert "full_localhost" in summary["validation_reuse"]["executed_groups"]
    assert summary["localhost_matrix_cooldown_audit"]["status"] == "clear"
    assert summary["localhost_matrix_cooldown_audit"]["localhost_steps"] == ["full_localhost"]
    assert summary["localhost_matrix_cooldown_audit"]["rate_limit_retry_allowed_violations"] == []
    localhost_step = next(step for step in summary["steps"] if step["name"] == "full_localhost")
    assert localhost_step["action"] != "reused_browser_source_lifecycle"
    call_text = calls.read_text(encoding="utf-8")
    assert call_text.count("pb test full") == 1
    assert "CHATGPT_SERVICE_BASE_URL=http://127.0.0.1:8000" in call_text
    assert "PROMPTBRANCH_RELEASE_VALIDATION_GROUPS_SKIP_DUPLICATE=1" in call_text
    assert "validation_evidence_reuse: reused full_direct" in result.stdout
    assert "full_localhost_policy: independent_execution_required" in result.stdout



def test_release_control_adopt_after_run_all_accepts_reused_direct_evidence_without_direct_report():
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "report_or_reused_full_direct_evidence_green" in script
    assert "verify_reused_full_direct_evidence_green" in script
    assert 'validate_release_validation_reuse_evidence "${full_direct_validation_evidence_json}" "full_direct" "direct" "${service_base_url}"' in script
    assert "run-all validation reuse evidence is missing or stale" in script
    assert 'report_or_reused_full_direct_evidence_green "${direct_report_json}"' in script
    assert 'report_or_reused_full_direct_evidence_green "${report_json}"' in script
    assert '[[ -f "${path}" ]]' in script




def test_release_control_adopt_after_run_all_requires_independent_localhost_report():
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "require_independent_full_localhost_report_green" in script
    assert 'require_independent_full_localhost_report_green "${localhost_report_json}"' in script
    assert 'require_independent_full_localhost_report_green "${report_json}"' in script
    assert "independent full_localhost report is missing" in script
    assert "verify_reused_full_localhost_lifecycle_green" not in script


def test_release_control_run_all_emits_percent_progress_contract():
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "promptbranch.release_control.all_tests_progress" in script
    assert "all_tests_progress:" in script
    assert "tested_percent_of_expected" in script
    assert "success_percent_of_tested" in script
    assert "failure_percent_of_tested" in script
    assert "run_all_emit_progress" in script
    assert 'all_test_step_specs+=("${name}|${log_path}|${rc}")\n  run_all_emit_progress' in script

def test_release_control_all_tests_summary_reports_localhost_cooldown_audit_contract():
    script_path = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    text = script_path.read_text(encoding="utf-8")
    assert "promptbranch.release_control.localhost_matrix_cooldown_audit" in text
    assert '"localhost_matrix_cooldown_audit": localhost_matrix_cooldown_audit' in text
    assert '"rate_limit_retry_allowed_violations": localhost_retry_allowed_violations' in text
    assert "localhost/offline matrix groups must not sleep/retry on browser cooldown evidence" in text
    assert '"full_localhost_policy": "independent_execution_required"' in text
    assert '"reusable_browser_source_lifecycle_groups": []' in text




def test_release_control_run_all_executes_full_localhost_independently() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    function = script[script.index("run_full_test_transport()") : script.index("all_test_step_specs=()")]
    assert 'if [[ ${run_all_tests} -eq 1 && "${label}" == "localhost" ]]' in function
    assert "full_localhost_policy: independent_execution_required" in function
    assert "full_localhost_direct_evidence_reuse: forbidden" in function
    assert "write_reused_localhost_browser_lifecycle_summary" not in function
    assert '"reusable_browser_source_lifecycle_groups": []' in script

def test_release_control_all_tests_summary_prefers_live_step_result_payloads_over_nested_schema_objects() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert '"project_ensure"' in script
    assert '"ensure_project"' in script
    assert 'command_profiles = {"visual-artifact-roundtrip", "release-live", "ask-live"}' in script
    assert 'if profile in command_profiles and "ok" in value and status:' in script


def test_release_control_all_tests_summary_reads_pretty_live_json_with_nested_metadata(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".pb_profile_local_debug").mkdir()
    (repo / "VERSION").write_text("v9.9.912\n", encoding="utf-8")
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
        "echo pb \"$@\" CHATGPT_SERVICE_BASE_URL=${CHATGPT_SERVICE_BASE_URL:-} >> \"$PB_FAKE_CALL_LOG\"\n"
        "emit_pretty_project_ensure() {\n"
        "  echo '[debug] before project ensure payload'\n"
        "  cat <<'JSON'\n"
        "{\n"
        "  \"ok\": true,\n"
        "  \"action\": \"ensure_project\",\n"
        "  \"project_name\": \"shared-test-project\",\n"
        "  \"project_url\": \"https://chatgpt.com/g/g-p-shared/project\",\n"
        "  \"created\": false,\n"
        "  \"match_count\": 1,\n"
        "  \"matched_by\": \"exact_name\",\n"
        "  \"error\": null,\n"
        "  \"rate_limit_telemetry\": {\n"
        "    \"rate_limit_modal_detected\": false,\n"
        "    \"conversation_history_429_seen\": false,\n"
        "    \"service_rate_limit_events\": []\n"
        "  },\n"
        "  \"browser_action_audit\": {\n"
        "    \"schema\": \"promptbranch.browser_action_audit\",\n"
        "    \"schema_version\": \"1.0\",\n"
        "    \"event_count\": 0,\n"
        "    \"recommendation\": \"nested schema must not outrank ensure_project\"\n"
        "  }\n"
        "}\n"
        "JSON\n"
        "  echo 'shared_live_project_url: https://chatgpt.com/g/g-p-shared/project'\n"
        "}\n"
        "emit_pretty_live() {\n"
        "  local action=\"$1\" profile=\"$2\"\n"
        "  echo '[browser] noisy log before pretty JSON'\n"
        "  cat <<JSON\n"
        "{\n"
        "  \"ok\": true,\n"
        "  \"action\": \"${action}\",\n"
        "  \"profile\": \"${profile}\",\n"
        "  \"status\": \"verified\",\n"
        "  \"failure_count\": 0,\n"
        "  \"download_status\": \"downloaded\",\n"
        "  \"verification_status\": \"smoke_zip_verified\",\n"
        "  \"profile_lease\": {\n"
        "    \"ok\": true,\n"
        "    \"action\": \"profile_lease\",\n"
        "    \"status\": \"leased\",\n"
        "    \"metadata\": {\"action\": \"${action}\", \"profile\": \"${profile}\"}\n"
        "  }\n"
        "}\n"
        "JSON\n"
        "}\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"login-check\" ]]; then echo 'login result: logged_in=True'; exit 0; fi\n"
        "if [[ \"$1\" == \"--profile-dir\" && \"$3\" == \"project-ensure\" ]]; then emit_pretty_project_ensure; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test full\" ]]; then echo '{\"ok\": true, \"action\": \"test_suite\", \"version\": \"v9.9.912\"}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0, \"suite\": {\"release_validation_groups\": {\"ok\": true, \"missing_required_groups\": [], \"groups\": {\"artifact_json_contracts\": {\"ok\": true}, \"browser_scheduler_source_lifecycle\": {\"ok\": true}, \"project_control_surface\": {\"ok\": true}}}}}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test ask-live\" ]]; then emit_pretty_live test_ask_live ask-live; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test visual-artifact-roundtrip\" ]]; then emit_pretty_live test_visual_artifact_roundtrip visual-artifact-roundtrip; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test release-live\" ]]; then emit_pretty_live test_visual_artifact_roundtrip release-live; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"test import-smoke\" ]]; then echo '{\"ok\": true, \"action\": \"package_import_smoke\", \"status\": \"verified\", \"failures\": []}'; exit 0; fi\n"
        "if [[ \"$1 $2\" == \"artifact guard\" ]]; then echo '{\"ok\": true, \"action\": \"artifact_guard\", \"status\": \"guard_passed\", \"failure_count\": 0}'; exit 0; fi\n"
        "echo unexpected pb args >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    (fake_bin / "pb").chmod(0o755)

    script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PB_FAKE_CALL_LOG"] = str(calls)
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"
    result = subprocess.run(
        [str(script), "--tests-only", "--run-all-tests", "--version", "v9.9.912"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    summary_path = repo / ".pb_profile" / "release_logs" / "v9.9.912" / "pb_test.all.v9.9.912.summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["final_verdict"] == "GO"
    assert summary["failed_steps"] == []
    live_steps = {step["name"]: step for step in summary["steps"] if step["name"] in {"live_project_ensure", "ask_live", "visual_artifact_roundtrip", "release_live"}}
    assert set(live_steps) == {"live_project_ensure", "ask_live", "visual_artifact_roundtrip", "release_live"}
    assert all(step["ok"] is True and step["json_error"] is None for step in live_steps.values())
    assert live_steps["live_project_ensure"]["action"] == "ensure_project"
    assert live_steps["live_project_ensure"]["status"] == "passed"
    assert live_steps["ask_live"]["action"] == "test_ask_live"
    assert live_steps["visual_artifact_roundtrip"]["action"] == "test_visual_artifact_roundtrip"
    assert live_steps["release_live"]["profile"] == "release-live"
    assert "all_tests_final_verdict: GO" in result.stdout
    assert "all_tests_failed_steps" not in result.stdout


def test_release_control_docker_service_lookup_is_clean_system_safe() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'compose_service_name="${PROMPTBRANCH_COMPOSE_SERVICE_NAME:-chatgpt-service}"' in script
    assert 'run_docker_compose ps -q "${compose_service_name}"' in script
    assert 'run_docker_compose ps -q 2>/dev/null | head -n 1' not in script
    assert 'wait_for_compose_service_container()' in script
    assert 'docker inspect -f \'{{.State.Status}}\'' in script
    assert 'docker inspect -f \'{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}\'' in script
    assert 'docker_service_container_missing_after_recreate' in script
    assert 'docker_service_container_not_running_after_recreate' in script
    assert 'write_docker_service_diagnostics "no_cache_recreate_container_not_running"' in script


def test_release_control_docker_preflight_and_diagnostics_are_declared() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'docker_preflight_json="${release_log_dir}/docker_preflight.${ver}.json"' in script
    assert 'docker_compose_config_json="${release_log_dir}/docker_compose_config.${ver}.json"' in script
    assert 'docker_compose_ps_all_json="${release_log_dir}/docker_compose_ps_all.${ver}.json"' in script
    assert 'docker_compose_logs_path="${release_log_dir}/docker_compose_logs.${ver}.log"' in script
    assert 'docker_release_preflight()' in script
    assert '["docker", "compose", "version"]' in script
    assert '["docker", "context", "show"]' in script
    assert 'run_docker_compose ps -a > "${docker_compose_ps_all_json}"' in script
    assert 'run_docker_compose logs --tail=200 "${compose_service_name}"' in script
    assert 'run_docker_compose config > "${docker_compose_config_json}"' in script


def test_release_control_pre_source_add_service_bootstrap_is_clean_system_safe() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'pre_source_add_service_health_json="${release_log_dir}/pre_source_add_service_health.${ver}.json"' in script
    assert 'pre_source_add_service_start_log="${release_log_dir}/pre_source_add_service_start.${ver}.log"' in script
    assert 'ensure_service_before_source_add || fail "pre-source-add service bootstrap failed"' in script
    assert 'pre_source_add_service_unavailable' in script
    assert 'Pre-source-add service unavailable or stale; bootstrapping candidate service before Project Source add.' in script
    assert 'docker compose --project-directory "${repo_root}" -p "${compose_project_name}" -f "${compose_file}" "$@"' in script
    assert 'run_pre_source_add_docker_compose build --pull' in script
    assert 'run_pre_source_add_docker_compose up -d --no-build --force-recreate --remove-orphans' in script
    assert 'run_pre_source_add_docker_compose ps "${compose_service_name}"' in script
    assert 'pre_source_add_build_context_json="${release_log_dir}/pre_source_add_build_context.${ver}.json"' in script
    assert 'write_pre_source_add_build_context_snapshot' in script
    assert 'Pre-source-add Promptbranch service health/version verified: ${ver#v}' in script


def test_release_control_pre_source_add_docker_build_context_freshness_is_fail_closed() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'pre_source_add_docker_build_context_version_mismatch' in script
    assert 'Docker build context version mismatch' in script
    assert 'classify_pre_source_add_bootstrap_failure()' in script
    assert 'ERROR: inspect pre_source_add_build_context_json=${pre_source_add_build_context_json}' in script
    assert 'build --no-cache --pull' in script
    assert 'refresh_docker_build_context_mtimes' in script
    assert 'PROMPTBRANCH_SOURCE_FINGERPRINT' in script
    assert 'Docker build context fingerprint mismatch' in (root / 'Dockerfile').read_text(encoding='utf-8')
    assert 'pre_source_add_docker_build_context_stale' in script
    assert 'up -d --no-build --force-recreate --remove-orphans' in script
    assert "'source_kind': 'pre_source_add_build_context'" in script
    assert "'status': 'verified' if all(checks.values()) else 'pre_source_add_repo_version_surface_mismatch'" in script
    assert "['docker', 'compose', '--project-directory', str(root), '-p', compose_project, '-f', str(compose), 'config']" in script


def test_release_control_installs_and_smokes_candidate_before_source_add_bootstrap() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    install_idx = script.index('# Reinstall local CLI from the release ZIP before any service-mediated source')
    smoke_idx = script.index('verify_installed_candidate_cli || fail "installed candidate CLI smoke failed before browser bootstrap and Project Source mutation"')
    ensure_idx = script.index('ensure_service_before_source_add || fail "pre-source-add service bootstrap failed"')
    source_add_idx = script.index('promptbranch src add "${canonical_artifact_zip}"')
    assert install_idx < smoke_idx < ensure_idx < source_add_idx
    assert 'installed_candidate_cli_smoke_log="${release_log_dir}/installed_candidate_cli_smoke.${ver}.json"' in script
    assert '["promptbranch", "--version"]' in script
    assert '["promptbranch", "release", "contract-plan", "--repo-path", repo_root, "--json"]' in script
    assert 'env.pop("PYTHONPATH", None)' in script
    assert 'env["PYTHONSAFEPATH"] = "1"' in script
    assert '"status": "installed_candidate_cli_verified" if ok else "installed_candidate_cli_failed"' in script
    assert "'source_kind': 'pre_source_add_service_health'" in script
    assert "'source_kind': 'pre_source_add_docker_preflight'" in script


def test_release_control_all_tests_progress_writer_uses_chr10_newline() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert '"schema": "promptbranch.release_control.all_tests_progress"' in script
    assert 'out.write_text(json.dumps(payload, indent=2, sort_keys=True) + chr(10), encoding="utf-8")' in script
    assert 'out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")' not in script
    assert 'all_tests_progress: ' in script


def test_docker_browser_parity_diagnostic_script_is_present_and_safe() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "docker-browser-parity-auth-readiness.sh").read_text(encoding="utf-8")

    assert "PROMPTBRANCH_DOCKER_BROWSER_PROFILE" in script
    assert "docker-browser-parity" in script
    assert "/v1/auth-readiness" in script
    assert "/v1/auth-readiness/session/status" in script
    assert "--keep-open" in script
    assert "--no-recreate" in script
    assert "PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS" in script
    assert "PROMPTBRANCH_DOCKER_BROWSER_NO_RECREATE" in script
    assert "/v1/login-check" not in script
    assert 'summary["ok"] = bool(runtime.get("ok") and auth.get("ok"))' in script
    assert "/v1/docker/browser-runtime" in script
    assert "/v1/project-sources" not in script
    assert "/v1/project-sources" not in script


def test_docker_browser_profile_bootstrap_script_is_promptbranch_native() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "docker-browser-profile-bootstrap-host-chrome.sh").read_text(encoding="utf-8")

    assert ".pb_profile_docker" in script
    assert "/app/profile" in (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")
    assert "google-chrome" in script
    assert "docker-browser-parity" not in script.lower()


def test_docker_browser_parity_export_challenge_artifacts_is_bounded_and_safe() -> None:
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "docker-browser-parity-export-challenge-artifacts.sh"
    script = script_path.read_text(encoding="utf-8")

    assert script_path.exists()
    assert "/tmp/pb-challenge-artifacts" in script
    assert "auth_readiness_auth_challenge_detected_*" in script
    assert "PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_FILES" in script
    assert "PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_MAX_BYTES" in script
    assert "artifact_export_size_limit_exceeded" in script
    assert "no_matching_artifacts" in script
    assert "refusing_destination_inside_repo_debug_artifacts" in script
    assert 'docker cp "${CID}:/tmp/pb-challenge-artifacts/."' in script
    assert 'docker cp "$CID:/app/debug_artifacts/."' not in script
    assert 'docker cp "${CID}:/app/debug_artifacts/."' not in script
    assert 'docker cp "$CID:/app/debug_artifacts"' not in script
    assert 'docker cp "${CID}:/app/debug_artifacts"' not in script

def test_docker_browser_parity_cloudflare_check_is_kiss_and_non_mutating() -> None:
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "docker-browser-parity-cloudflare-check.sh"
    script = script_path.read_text(encoding="utf-8")

    assert script_path.exists()
    assert "docker browser parity Cloudflare check" in script
    assert "/v1/docker/browser-runtime" in script
    assert "/v1/auth-readiness" in script
    assert "/v1/auth-readiness/session/status" in script
    assert "{\"keep_open\": true}" in script
    assert "PROMPTBRANCH_CLOUDFLARE_CHECK_MAX_WAIT_SECONDS" in script
    assert "PROMPTBRANCH_CLOUDFLARE_CHECK_POLL_SECONDS" in script
    assert "standard-browser" in script
    assert "CHATGPT_PATCHRIGHT_HEADED_SAFE_ARGS" in script
    assert "chrome-argv-" in script
    assert "docker-browser-parity-export-challenge-artifacts.sh" in script
    assert "auth_readiness_auth_challenge_detected_*" in script
    assert "assert_host_profile_not_in_docker_build_context" in script
    assert "host_profile_would_enter_docker_build_context" in script
    assert "cloudflare_timeout" in script
    assert "cloudflare_cleared_auth_ready" in script
    assert "successful_auth_readiness_no_challenge_manifest_required" in script
    assert "evidence_export_status=ok_no_challenge_manifest_required" in script
    assert "missing_staged_manifest" in script
    assert "cloudflare_cleared_not_auth_ready" in script
    assert "docker cp" not in script
    assert "curl -sS -o" in script
    assert "http://localhost:8000/v1/project-sources" not in script
    assert "http://localhost:8000/v1/login-check" not in script



def test_docker_bonnetjes_cloudflare_check_runs_seeded_and_clean_profiles() -> None:
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "docker-bonnetjes-cloudflare-check.sh"
    script = script_path.read_text(encoding="utf-8")

    assert script_path.exists()
    assert "standard-browser" in script
    assert ".pb_profile/browser/default" in script
    assert "docker-browser-parity-cloudflare-check.sh" in script
    assert "docker-browser-parity-cloudflare-check.sh" in script
    assert "http://localhost:8000/v1/project-sources" not in script
    assert "http://localhost:8000/v1/login-check" not in script


def test_dockerignore_excludes_browser_profiles_from_build_context() -> None:
    root = Path(__file__).resolve().parents[1]
    dockerignore = (root / ".dockerignore").read_text(encoding="utf-8")

    assert ".pb_profile*" in dockerignore
    assert ".pb_profile_*" in dockerignore
    assert "debug_artifacts/" in dockerignore
    assert "*.zip" in dockerignore


def test_docker_bonnetjes_clean_login_profile_bootstrap_documents_manual_phase() -> None:
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "docker-bonnetjes-clean-login-profile-bootstrap.sh"
    script = script_path.read_text(encoding="utf-8")

    assert script_path.exists()
    assert "pb-browser-profile-bootstrap.sh" in script
    neutral = (root / "scripts" / "pb-browser-profile-bootstrap.sh").read_text(encoding="utf-8")
    assert "google-chrome" in neutral
    assert ".pb_profile/browser/default" in neutral
    assert "PROMPTBRANCH_HOST_PROFILE_DIR" in neutral
    assert "standard-browser" in neutral
    assert "docker-browser-parity-cloudflare-check.sh" in neutral
    assert "http://localhost:8000/v1/project-sources" not in script
    assert "http://localhost:8000/v1/login-check" not in script


def test_standard_browser_profile_bootstrap_repairs_empty_root_owned_placeholder() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "pb-browser-profile-bootstrap.sh").read_text(encoding="utf-8")

    assert "prepare_profile_dir_for_host_chrome" in script
    assert 'rmdir -- "${dir}"' in script
    assert "Repaired empty non-writable browser profile placeholder" in script
    assert "sudo chown -R $(id -u):$(id -g)" in script
    assert "Failed to create a ProcessSingleton" not in script


def test_docker_cloudflare_check_prepares_bind_mount_profile_before_compose() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "docker-browser-parity-cloudflare-check.sh").read_text(encoding="utf-8")

    assert "prepare_bind_mount_profile_dir" in script
    assert 'export PROMPTBRANCH_HOST_PROFILE_DIR="${dir}"' in script
    assert "docker compose -f docker-compose.chatgpt-service.yml up -d --build" in script
    assert script.index("prepare_bind_mount_profile_dir") < script.index("docker compose -f docker-compose.chatgpt-service.yml up -d --build")
    assert "Repaired empty non-writable browser profile placeholder" in script


def test_docker_bonnetjes_cloudflare_validation_wraps_install_bootstrap_and_check() -> None:
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "docker-bonnetjes-cloudflare-validation.sh"
    script = script_path.read_text(encoding="utf-8")

    assert script_path.exists()
    assert "pb-browser-cloudflare-validation.sh" in script
    neutral = (root / "scripts" / "pb-browser-cloudflare-validation.sh").read_text(encoding="utf-8")
    assert "--install-artifact" in neutral
    assert "pb release install" in neutral
    assert "pb-browser-profile-bootstrap.sh" in neutral
    assert "docker-browser-parity-cloudflare-check.sh" in neutral
    assert "standard-browser" in neutral
    assert "PROMPTBRANCH_HOST_PROFILE_DIR" in neutral
    assert "validation-summary.json" in neutral
    assert "project_source_mutation_allowed" in neutral
    assert "http://localhost:8000/v1/project-sources" not in script
    assert "http://localhost:8000/v1/login-check" not in script
    assert "docker cp" not in script


def test_release_control_declares_auth_only_validation_path() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "--auth-only-validation" in script
    assert "auth_only_validation=1; skip_source_add=1" in script
    assert "run_auth_only_validation" in script
    assert "verify_auth_only_validation_green" in script
    assert "pb artifact adopt \"${artifact_zip}\" --local-only --local-path \"${local_zip}\" --json" in script
    assert "skipped_auth_only_validation" in script


def test_docker_challenge_exporter_returns_no_matching_artifacts_without_manifest() -> None:
    script = (Path(__file__).resolve().parents[1] / "scripts" / "docker-browser-parity-export-challenge-artifacts.sh").read_text(encoding="utf-8")
    assert "status': 'no_matching_artifacts'" in script
    assert "missing staging manifest treated as clean no-op" in script
    assert "matching_count" in script

def test_docker_browser_profile_bootstrap_runs_chrome_inside_container() -> None:
    root = Path(__file__).resolve().parents[1]
    script_path = root / "scripts" / "pb-docker-browser-profile-bootstrap.sh"
    script = script_path.read_text(encoding="utf-8")

    assert script_path.exists()
    assert "Docker-launched Chrome" in script
    assert "docker run --rm -it" in script
    assert "--shm-size \"${shm_size}\"" in script
    assert "PROMPTBRANCH_DOCKER_SHM_SIZE" in script
    assert "google-chrome" in script
    assert "--user-data-dir=/app/profile" in script
    assert "/tmp/.X11-unix:/tmp/.X11-unix" in script
    assert "XAUTHORITY=/tmp/.docker.xauth" in script
    assert "PROMPTBRANCH_HOST_PROFILE_DIR" in script
    assert ".pb_profile/browser/default" in script
    assert "resolve_state_url" in script
    assert "PROMPTBRANCH_BROWSER_BOOTSTRAP_URL" in script
    assert "current_conversation_url" in script
    assert "PROMPTBRANCH_DOCKER_BOOTSTRAP_EXTRA_ARGS" in script
    assert "http://localhost:8000/v1/project-sources" not in script
    assert "http://localhost:8000/v1/login-check" not in script


def test_standard_browser_validation_defaults_to_docker_visual_bootstrap() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "scripts" / "pb-browser-cloudflare-validation.sh").read_text(encoding="utf-8")

    assert 'bootstrap_mode="${PROMPTBRANCH_BROWSER_BOOTSTRAP_MODE:-docker}"' in script
    assert "--docker-bootstrap" in script
    assert "--host-bootstrap" in script
    assert "pb-docker-browser-profile-bootstrap.sh" in script
    assert "visible Docker Chrome login bootstrap" in script
    assert "bootstrap_mode=${bootstrap_mode}" in script
    assert "target_url=${target_url}" in script
    assert "bootstrap_url=${bootstrap_url}" in script
    assert "PROMPTBRANCH_BROWSER_BOOTSTRAP_MODE=docker|host" in script
    assert "PROMPTBRANCH_BROWSER_VALIDATION_URL" in script
    assert "PROMPTBRANCH_BROWSER_BOOTSTRAP_URL" in script
    assert "--bootstrap-url" in script
    assert 'CHATGPT_PROJECT_URL="${target_url}"' in script
    assert '--url "${bootstrap_url}"' in script
    assert 'bootstrap_url="https://chatgpt.com/"' in script
    assert 'PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS="${PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS:-${max_wait_seconds}}"' in script
    assert script.index("pb-docker-browser-profile-bootstrap.sh") < script.index("docker-browser-parity-cloudflare-check.sh")

def test_release_control_auth_bootstrap_before_live_operations() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'pb_auth_bootstrap()' in script
    assert 'release_control_resolve_auth_bootstrap_url()' in script
    assert 'bootstrap_url="$(release_control_resolve_auth_bootstrap_url "${phase}")"' in script
    assert 'PROMPTBRANCH_BROWSER_VALIDATION_URL="${bootstrap_url}"' in script
    assert 'PROMPTBRANCH_BROWSER_BOOTSTRAP_URL="${bootstrap_url}"' in script
    assert 'pb_auth_bootstrap "pre_source_add" || fail "release-control auth bootstrap failed before Project Source add"' in script
    assert 'pb_auth_bootstrap "pre_tests" || fail "release-control auth bootstrap failed before tests"' in script
    assert 'Release-control auth bootstrap skipped for ${phase}: --auth-only-validation is already the auth bootstrap path.' in script
    assert 'promptbranch.release_control.auth_bootstrap' in script
    assert 'release_control_clear_auth_bootstrap_held_session()' in script
    assert 'strategy: docker_compose_restart_service' in script
    assert 'clear in-memory held auth-readiness session after successful auth bootstrap while preserving browser profile on disk' in script
    assert 'release_control_wait_for_no_held_auth_session()' in script
    assert 'PROMPTBRANCH_RELEASE_AUTH_BOOTSTRAP_KEEP_OPEN_SECONDS:-1' in script
    assert 'held_auth_session_released' in script
    assert 'held_auth_session_release_timeout' in script



def test_release_control_pre_source_add_accepts_project_page_auth_ready_without_composer() -> None:
    root = Path(__file__).resolve().parents[1]
    release_script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    validation_script = (root / "scripts" / "pb-browser-cloudflare-validation.sh").read_text(encoding="utf-8")

    assert 'local allow_project_page_ready=0' in release_script
    assert 'if [[ "${phase}" == "pre_source_add" ]]; then' in release_script
    assert 'allow_project_page_ready=1' in release_script
    assert 'PROMPTBRANCH_BROWSER_VALIDATION_ALLOW_PROJECT_PAGE_READY="${allow_project_page_ready}"' in release_script
    assert 'allow_project_page_ready: ${allow_project_page_ready}' in release_script

    assert 'allow_project_page_ready = sys.argv[5].strip().lower()' in validation_script
    assert "target_is_project_page = parsed_target.path.rstrip('/').endswith('/project')" in validation_script
    assert "last.get('project_page_visible') is True" in validation_script
    assert "if not composer_ready and not project_page_ready_accepted:" in validation_script
    assert "errors.append('composer_visible is not true')" in validation_script
    assert "PROMPTBRANCH_BROWSER_VALIDATION_ALLOW_PROJECT_PAGE_READY=1" in validation_script


def test_release_control_pre_tests_prefers_current_conversation_url_before_composer_validation() -> None:
    root = Path(__file__).resolve().parents[1]
    release_script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    validation_script = (root / "scripts" / "pb-browser-cloudflare-validation.sh").read_text(encoding="utf-8")

    assert 'bootstrap_url="$(release_control_resolve_auth_bootstrap_url "${phase}")"' in release_script
    assert 'phase = sys.argv[3]' in release_script
    assert 'if phase == "pre_tests":' in release_script
    assert 'PROMPTBRANCH_RELEASE_AUTH_BOOTSTRAP_PRE_TESTS_URL' in release_script
    assert 'is_project_conversation_url(value)' in release_script
    assert 'print(value)' in release_script
    assert 'current_conversation_url' in release_script
    assert 'task_list_cache' in release_script
    assert 'pre_tests_project_page_fallback: ${project_page_fallback}' in release_script

    assert 'local allow_project_page_ready=0' in release_script
    assert 'if [[ "${phase}" == "pre_source_add" ]]; then' in release_script
    assert 'elif [[ "${phase}" == "pre_tests" ]] && release_control_url_is_project_page "${bootstrap_url}"; then' in release_script
    assert 'PROMPTBRANCH_RELEASE_AUTH_BOOTSTRAP_PRE_TESTS_PROJECT_PAGE_FALLBACK:-1' in release_script
    assert 'PROMPTBRANCH_BROWSER_VALIDATION_ALLOW_PROJECT_PAGE_READY="${allow_project_page_ready}"' in release_script

    # The validation script only relaxes composer readiness for /project URLs;
    # conversation URLs still require composer_visible=true.
    assert "target_is_project_page = parsed_target.path.rstrip('/').endswith('/project')" in validation_script
    assert "project_page_ready_accepted = (" in validation_script
    assert "target_is_project_page" in validation_script
    assert "if not composer_ready and not project_page_ready_accepted:" in validation_script


def test_release_control_run_all_live_profiles_are_explicit_bootstrapped_not_copied_static() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    bootstrap = (root / "scripts" / "pb-docker-live-profile-bootstrap.sh").read_text(encoding="utf-8")

    assert "live_profile_strategy: explicit_bootstrapped_slot_single_actor_no_copy_no_refresh" in script
    assert "live_profile_pool_slot_dir" in script
    assert "run_all_validate_live_pool_slot_profile" in script
    assert "live_profile_pool_slot_unavailable" in script
    assert "live_profile_pool_slot_not_authenticated" in script
    assert "Bootstrap this exact profile before rerunning --run-all-tests" in script
    assert "--profile-pool-refresh" not in script
    assert "optional_live_seed_profile_status: missing_not_blocking" in script
    assert 'record_all_test_nonblocking_skipped_step "ask_live"' not in script
    assert 'pb test ask-live --profile-dir "${live_profile_pool_slot_dir}" --profile-lease' in script
    assert 'pb test visual-artifact-roundtrip --profile-dir "${live_profile_pool_slot_dir}" --profile-lease' in script
    assert 'pb test release-live --profile-dir "${live_profile_pool_slot_dir}" --profile-lease' in script

    assert "pb-docker-live-profile-bootstrap.sh" in bootstrap
    assert ".pb_profile_local_debug" in bootstrap
    assert ".pb_profile_local_debug_pools" in bootstrap
    assert "No profile copying is performed" in bootstrap
    assert "pb-docker-browser-profile-bootstrap.sh --profile-dir" in bootstrap


def test_normal_browser_launches_do_not_use_unsupported_blink_fedcm_flag() -> None:
    root = Path(__file__).resolve().parents[1]
    browser_client = (root / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    compat_client = (root / "chatgpt_browser_auth" / "client.py").read_text(encoding="utf-8")
    compose = (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")
    docker_runner = (root / "docker" / "run-chatgpt-service-in-container.sh").read_text(encoding="utf-8")

    assert "--disable-blink-features=FedCm" not in browser_client
    assert "--disable-blink-features=FedCm" not in compat_client
    assert "CHATGPT_DISABLE_FEDCM: ${CHATGPT_DISABLE_FEDCM:-0}" in compose
    assert 'export CHATGPT_DISABLE_FEDCM="${CHATGPT_DISABLE_FEDCM:-0}"' in docker_runner


def test_release_control_run_all_live_steps_use_conversation_url_not_project_page_static() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "run_all_ensure_shared_live_conversation" in script
    assert "run_all_extract_conversation_url_from_log" in script
    assert "shared_live_conversation_url" in script
    assert "live_conversation_url_missing" in script
    assert "create_new_task_inside_shared_live_project" in script
    assert 'pb --profile-dir "${live_profile_pool_slot_dir}" use "${run_all_shared_project_url}" --json' in script
    assert 'pb --profile-dir "${live_profile_pool_slot_dir}" ask --new-task --retries 0' in script
    assert '--conversation-url "${run_all_shared_conversation_url}"' in script
    assert '--conversation-url "${run_all_shared_project_url}" --keep-project --fail-fast --json' not in script
    assert 'pb test ask-live --profile-dir "${live_profile_pool_slot_dir}" --profile-lease' in script
    assert 'pb test visual-artifact-roundtrip --profile-dir "${live_profile_pool_slot_dir}" --profile-lease' in script
    assert 'pb test release-live --profile-dir "${live_profile_pool_slot_dir}" --profile-lease' in script


def test_release_control_live_steps_fail_fast_on_cloudflare_challenge_static() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    browser_client = (root / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    automation = (root / "promptbranch_automation" / "automation.py").read_text(encoding="utf-8")
    cli = (root / "promptbranch_cli.py").read_text(encoding="utf-8")

    assert "run_all_log_has_cloudflare_challenge" in script
    assert "docker_live_profile_challenged" in script
    assert "not retrying this live browser step" in script
    assert "run_all_log_has_docker_live_profile_challenge" in script
    assert 'grep -Fqi "docker_live_profile_challenged"' in script
    assert "just a moment" in script
    assert "__cf_chl" in script
    assert 'if [[ ${step_rc} -ne 0 ]] && [[ "${step_name}" == "ask_live"' in script
    assert "ask_live returned docker_live_profile_challenged; skipping remaining live browser steps" in script
    assert "skipped_ask_live_docker_live_profile_challenged" in script
    assert "grep -Eiq" not in script
    assert "return ${step_rc}" in script
    assert "--retries 0 --json" in script
    assert "PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1 CHATGPT_FAIL_FAST_ON_CHALLENGE=1" in script
    assert "_raise_fail_fast_challenge_if_configured" in browser_client
    assert "refusing manual-login wait" in browser_client
    assert "challenge_stage=stage" in browser_client
    assert "\n            stage=stage," not in browser_client
    assert "challenge_type=challenge_type" in browser_client
    assert "docker_live_profile_challenged" in browser_client
    assert "docker_standard_profile_challenged" in browser_client
    assert "browser_backend_403_guardrail" in browser_client
    assert "CHATGPT_FAIL_FAST_ON_CHALLENGE" in automation
    assert "PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE" in automation
    assert 'status = "docker_live_profile_challenged"' in cli
    assert "fail-fast mid-run browser challenge detected; refusing cooldown/retry cascade" in browser_client
    assert "backend-api 403 treated as browser challenge guardrail; skipping persisted cooldown" in browser_client
    assert "response-wait-exception" in browser_client
    assert "response-wait-page-closed" in browser_client
    assert "TargetClosedError" in browser_client



def test_release_control_backend_api_403_guardrail_is_terminal_static() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    browser_client = (root / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")
    compose = (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")

    assert "run_all_log_has_backend_api_guardrail_403" in script
    assert "status: browser_backend_403_guardrail" in script
    assert "refusing rate-limit retry/cooldown" in script
    assert "skipped_browser_backend_403_guardrail" in script
    assert "CHATGPT_FAIL_FAST_ON_CHALLENGE=1" in script
    assert "CHATGPT_FAIL_FAST_ON_CHALLENGE:" in compose
    assert "backend-api 403 treated as browser challenge guardrail" in browser_client
    assert "backend_403_guardrail_terminal" in browser_client
    assert "Browser profile hit a Cloudflare/backend-403 guardrail" in browser_client


def test_standard_cloudflare_validation_rejects_backend_api_guardrail_static() -> None:
    script = Path("scripts/pb-browser-cloudflare-validation.sh").read_text(encoding="utf-8")
    assert "backend_api_guardrail_seen = _backend_guardrail_403_seen(payload)" in script
    assert "browser_backend_403_guardrail" in script
    assert "backend_api_guardrail_seen is true; browser/profile is forbidden" in script


def test_release_control_auth_bootstrap_backend_api_guardrail_is_terminal_static() -> None:
    script = Path("chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "release_control_log_has_backend_api_guardrail_403" in script
    assert "auth bootstrap ${phase} observed backend-api 403 guardrail" in script
    assert "bootstrap_backend_guardrail=1" in script
    assert "release_control_clear_auth_bootstrap_held_session \"${phase}\" || true" in script
    assert "status: browser_backend_403_guardrail" in script


def test_release_control_full_validation_guardrail_is_terminal_even_when_command_succeeds_static() -> None:
    script = Path("chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "if [[ ${run_all_tests} -eq 1 ]] && run_all_log_has_backend_api_guardrail_403" in script
    assert "test_rc=1" in script
    assert "treating it as a terminal browser challenge" in script


def test_release_live_project_ensure_fail_fast_and_compose_down_safe_static() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    compose = (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")
    container_api = (root / "promptbranch_container_api.py").read_text(encoding="utf-8")
    cli = (root / "promptbranch_cli.py").read_text(encoding="utf-8")

    assert "PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1 CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb --profile-dir" in script
    assert "project-ensure" in script
    assert "live_project_ensure returned docker_live_profile_challenged" in script
    assert "skipped_live_project_ensure_docker_live_profile_challenged" in script
    assert "PROMPTBRANCH_VERSION: ${PROMPTBRANCH_VERSION:-local}" in compose
    assert "image: ${PROMPTBRANCH_SERVICE_IMAGE:-promptbranch-service:${PROMPTBRANCH_VERSION:-local}}" in compose
    assert 'fail_fast_on_challenge=_env_flag("CHATGPT_FAIL_FAST_ON_CHALLENGE", False)' in container_api
    assert "AuthChallengeRequiredError" in container_api
    assert "challenge_type={payload.get('challenge_type')}" in cli


def test_release_live_bootstrap_guardrail_blocks_ask_live_static() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "run_all_log_has_live_bootstrap_guardrail" in script
    assert "status: live_bootstrap_guardrail" in script
    assert "live_bootstrap_guardrail_terminal: true" in script
    assert "release_control_cooldown_policy: no_wait_no_retry_after_live_bootstrap_guardrail" in script
    assert "skipped_blocked_by_live_bootstrap_guardrail" in script
    assert "refusing to open ask_live" in script
    assert "rate_limit_modal/conversation_history_429/backend-api guardrail" in script


def test_release_live_continuous_uses_preflight_warmup_conversation_url_static() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    cli = (root / "promptbranch_cli.py").read_text(encoding="utf-8")
    browser_client = (root / "promptbranch_browser_auth" / "client.py").read_text(encoding="utf-8")

    assert "run_all_live_warmup_conversation_url" in script
    assert "live_profile_preflight_warmup_conversation_url" in script
    assert "--warmup-conversation-url" in script
    assert "release_live_continuous_warmup_conversation_url" in script
    assert "current_url" in script
    assert 'test_release_live_continuous.add_argument("--warmup-conversation-url"' in cli
    assert 'warmup_conversation_url=getattr(args, "warmup_conversation_url", None)' in cli
    assert 'warmup_strategy="trusted_preflight_conversation_url"' in browser_client
    assert "self.config.project_url = effective_warmup_url" in browser_client


def test_release_live_preflight_warmup_extracts_top_level_login_check_url_static() -> None:
    script = Path("chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert '("conversation_url", "current_conversation_url", "current_url", "url")' in script
    assert "pb login-check reports the validated page as" in script
    assert "top-level ``url``" in script
    assert "live_preflight_warmup_url_missing" in script
    assert "refusing to start release-live-continuous at chatgpt.com root" in script
    assert "skipped_live_preflight_warmup_url_missing" in script


def test_release_live_continuous_requires_warmup_url_before_launch_static() -> None:
    script = Path("chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    guard = script.index('if [[ -z "${run_all_live_warmup_conversation_url}" ]]')
    launch = script.index('echo "+ PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1 CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb test release-live-continuous')
    assert guard < launch
    assert 'warmup_args=(--warmup-conversation-url "${run_all_live_warmup_conversation_url}")' in script
    assert 'release_live_continuous_warmup_conversation_url: unavailable' in script
    assert 'status: live_preflight_warmup_url_missing' in script


def test_release_live_continuous_uses_docker_service_transport_not_profile_lease_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "release-live-continuous_service_transport_required" in script
    launch = script.index('CHATGPT_SERVICE_BASE_URL="${service_base_url}" PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1 CHATGPT_FAIL_FAST_ON_CHALLENGE=1')
    segment = script[launch: launch + 900]
    assert 'CHATGPT_SERVICE_BASE_URL="${service_base_url}"' in segment
    assert '--profile-lease' not in segment
    assert '--profile-dir "${live_profile_pool_slot_dir}"' in segment


def test_release_control_maps_release_live_slot_to_app_profile_before_live_preflight_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "run_all_recreate_service_for_live_slot_profile" in script
    assert 'CHATGPT_PROJECT_URL="${run_all_live_service_target_url}" PROMPTBRANCH_HOST_PROFILE_DIR="${live_profile_pool_slot_dir}" run_docker_compose up -d --no-build --force-recreate --remove-orphans' in script
    assert "docker_service_maps_release_live_slot_to_app_profile" in script
    assert "trusted_project_conversation_url_no_chatgpt_root" in script
    call = script.index('if run_all_resolve_live_service_target_url && run_all_recreate_service_for_live_slot_profile && run_all_live_profile_preflight; then')
    live = script.index('run_all_release_live_continuous_bootstrap_and_ask', call)
    assert call < live


def test_release_control_configures_live_slot_service_with_trusted_conversation_url_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "run_all_resolve_live_service_target_url" in script
    assert "live_preflight_target_url_missing" in script
    assert "refusing to start Docker live-slot service at chatgpt.com root" in script
    assert 'run_all_url_is_conversation_url "${resolved_url}"' in script
    assert 'CHATGPT_PROJECT_URL="${run_all_live_service_target_url}"' in script
    resolve = script.index('run_all_resolve_live_service_target_url()')
    recreate = script.index('run_all_recreate_service_for_live_slot_profile()', resolve)
    assert resolve < recreate


def test_release_control_live_preflight_does_not_recommend_chatgpt_root_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    bootstrap_block = script[script.index('run_all_write_live_profile_missing_json()'):script.index('run_all_validate_live_profile_dir()')]
    assert '<trusted-/g/.../c/...-conversation-url>' in bootstrap_block
    assert '--url {url or ' in bootstrap_block
    assert '--url {url}",' not in bootstrap_block


def test_release_control_default_run_all_external_live_not_requested_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "--run-external-live-tests" in script
    assert "--require-chatgpt-live-validation" in script
    assert "external_live_not_requested" in script
    assert "refusing to call POST /v1/login-check during default --run-all-tests" in script
    default_branch = script.index('if [[ ${run_external_live_tests} -eq 0 ]]; then')
    preflight_launch = script.index('if run_all_resolve_live_service_target_url && run_all_recreate_service_for_live_slot_profile && run_all_live_profile_preflight; then')
    assert default_branch < preflight_launch
    assert 'record_all_test_nonblocking_skipped_step "live_profile_preflight" "${live_profile_preflight_json}" "external_live_not_requested"' in script


def test_release_control_external_live_flag_explicitly_enables_probe_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'run_external_live_tests="${PROMPTBRANCH_RUN_EXTERNAL_LIVE_TESTS:-0}"' in script
    assert '--run-external-live-tests)' in script
    assert 'run_external_live_tests=1' in script
    assert '--require-chatgpt-live-validation)' in script
    assert 'require_chatgpt_live_validation=1' in script
    assert 'export PROMPTBRANCH_RELEASE_RUN_EXTERNAL_LIVE_TESTS="${run_external_live_tests}"' in script
    assert '"external_live_tests_requested": os.environ.get("PROMPTBRANCH_RELEASE_RUN_EXTERNAL_LIVE_TESTS") == "1"' in script




def test_release_control_all_tests_summary_normalizes_live_bootstrap_guardrail_status_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert 'if name == "live_project_ensure" and (' in script
    assert '"status: live_bootstrap_guardrail" in raw_log_lower' in script
    assert '"live_bootstrap_guardrail_terminal: true" in raw_log_lower' in script
    assert 'status = "live_bootstrap_guardrail"' in script
    assert 'elif status == "failed" and "skipped_blocked_by_live_bootstrap_guardrail" in raw_log_lower:' in script
    assert 'payload_status in {"live_external_browser_challenge", "docker_live_profile_challenged", "live_bootstrap_guardrail", "skipped_blocked_by_live_bootstrap_guardrail", "bootstrap_sentinel_missing_after_ask_success", "skipped_bootstrap_sentinel_missing_after_ask_success"}' in script

def test_release_control_classifies_docker_live_preflight_challenge_as_external_live_blocked_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "run_all_log_has_external_browser_challenge" in script
    assert "auth_challenge_required" in script
    assert "docker_standard_profile_challenged" in script
    assert "live_external_browser_challenge" in script
    assert "release_control_live_policy: external_browser_challenge_no_browser_repair" in script
    assert "skipped_live_external_browser_challenge" in script
    assert "LIVE_BLOCKED" in script
    assert "product_failure_count" in script
    assert "external_live_blocked" in script
    assert "external_live_blocked_raw" in script
    assert "product_failure_steps" in script
    assert "external_live_blocked = external_live_blocked_raw and not product_failed" in script
    assert "docker_live_profile_challenged" in script
    assert "skipped_ask_live_docker_live_profile_challenged" in script
    assert "skipped_live_project_ensure_docker_live_profile_challenged" in script
    assert "live_bootstrap_guardrail" in script
    assert "skipped_blocked_by_live_bootstrap_guardrail" in script
    assert "bootstrap_sentinel_missing_after_ask_success" in script
    assert "skipped_bootstrap_sentinel_missing_after_ask_success" in script


def test_release_control_live_slot_recreate_trace_does_not_duplicate_chatgpt_project_url_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "CHATGPT_PROJECT_URL=${run_all_live_service_target_url} PROMPTBRANCH_HOST_PROFILE_DIR=${live_profile_pool_slot_dir} $(compose_env_prefix)" not in script
    assert "PROMPTBRANCH_HOST_PROFILE_DIR=${live_profile_pool_slot_dir} CHATGPT_PROJECT_URL=${run_all_live_service_target_url}" in script


def test_install_sh_strict_all_all_release_gate_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "install.sh").read_text(encoding="utf-8")

    assert "set -euo pipefail" in script
    assert 'ver="$1"' in script
    assert 'zip="${zip:-$HOME/Downloads/chatgpt_claudecode_workflow-2_${ver}.zip}"' in script
    assert "--diagnostic-project-source-ab" in script
    assert '--install-from-zip "${zip}"' in script
    assert '--version "${ver}"' in script
    assert "--run-all-tests" in script
    assert "--run-external-live-tests" in script
    assert "--require-chatgpt-live-validation" in script
    assert "--adopt-after-validation" in script
    assert "--skip-docker-logs" in script
    assert "--prune-release-logs" in script
    assert "--release-log-keep 12" in script
    assert 'tee "${HOME}/tmp/release_control.${ver}.full.all-all.adopt.log"' in script
    assert 'pb artifact current --all --json | tee "${HOME}/tmp/pb_current_after_${ver}.json"' in script


def test_install_sh_is_executable() -> None:
    script = Path(__file__).resolve().parents[1] / "install.sh"
    assert script.is_file()
    assert script.stat().st_mode & 0o111



def test_release_1080_reuses_verified_candidate_service_for_pre_source_auth() -> None:
    root = Path(__file__).resolve().parents[1]
    release = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    validation = (root / "scripts" / "pb-browser-cloudflare-validation.sh").read_text(encoding="utf-8")
    assert 'validation_no_recreate=1' in release
    assert 'PROMPTBRANCH_BROWSER_VALIDATION_NO_RECREATE="${validation_no_recreate}"' in release
    assert '--no-recreate "${check_args[@]}"' in validation
    assert 'validation_no_recreate:' in release


def test_release_1080_docker_dependency_layers_precede_release_metadata() -> None:
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    assert dockerfile.index("RUN bash -lc") < dockerfile.index("ARG PROMPTBRANCH_VERSION")
    assert dockerfile.index("RUN playwright install --with-deps chromium") < dockerfile.index("ARG PROMPTBRANCH_VERSION")
    assert "PROMPTBRANCH_DOCKER_BROWSER_DEPENDENCY_DOWNLOAD_FAILED" in dockerfile
    assert "Retrying Patchright Chrome transport failure once" in dockerfile


def test_release_1080_pins_browser_automation_dependencies() -> None:
    root = Path(__file__).resolve().parents[1]
    requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "patchright==1.58.2" in requirements
    assert "playwright==1.52.0" in requirements
    assert '"patchright==1.58.2"' in pyproject
    assert '"playwright==1.52.0"' in pyproject


def test_release_1080_classifies_browser_dependency_download_failure_precisely() -> None:
    root = Path(__file__).resolve().parents[1]
    release = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    validation = (root / "scripts" / "pb-browser-cloudflare-validation.sh").read_text(encoding="utf-8")
    assert 'status="docker_browser_dependency_download_failed"' in release
    assert 'fail "docker_browser_dependency_download_failed"' in release
    assert '"status":"docker_browser_dependency_download_failed"' in validation
    assert "no Cloudflare check summary.json" in validation


def test_release_1080_pre_source_build_uses_cache() -> None:
    release = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    pre_source = release[release.index("ensure_service_before_source_add()") : release.index("# Add release ZIP to ChatGPT Project Sources.")]
    assert "build --pull" in pre_source
    assert "build --no-cache --pull" not in pre_source


def test_install_sh_rejects_transport_zip_internal_version_mismatch(tmp_path: Path) -> None:
    import zipfile

    transport = tmp_path / "promptbranch-transport-unique.zip"
    with zipfile.ZipFile(transport, "w") as archive:
        archive.writestr("VERSION", "v9.9.80\n")
        archive.writestr("pyproject.toml", "[project]\nname='promptbranch'\nversion='9.9.80'\n")
        archive.writestr(".gitignore", "*.zip\n")
        archive.writestr(".not_to_zip", "*.zip\n")
        archive.writestr(".promptbranch-repo.json", json.dumps({"schema_version": 1, "project_id": "g-p-demo", "project_home_url": "https://chatgpt.com/g/g-p-demo/project", "repo_id": "chatgpt_claudecode_workflow", "artifact_pattern": "chatgpt_claudecode_workflow_<version>.zip", "role": "release_authority"}))
        archive.writestr("chatgpt_claudecode_workflow_release_control.sh", "#!/usr/bin/env bash\n")

    install = Path(__file__).resolve().parents[1] / "install.sh"
    result = subprocess.run(
        [str(install), "v9.9.81", str(transport)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "candidate transport ZIP VERSION mismatch" in result.stderr
    assert "expected v9.9.81, got v9.9.80" in result.stderr


def test_release_control_separates_transport_and_canonical_artifact_identity(tmp_path: Path) -> None:
    import zipfile

    repo = tmp_path / "chatgpt_claudecode_workflow-2"
    repo.mkdir()
    version = "v9.9.81"
    transport = tmp_path / "downloads" / "unique-chatgpt-transport-b7c1de9f28.zip"
    transport.parent.mkdir()
    release_script = Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh"

    with zipfile.ZipFile(transport, "w") as archive:
        archive.writestr("VERSION", f"{version}\n")
        archive.writestr("pyproject.toml", "[project]\nname='promptbranch'\nversion='9.9.81'\n")
        archive.writestr(".gitignore", "*.zip\n")
        archive.writestr(".not_to_zip", "*.zip\n")
        archive.writestr(".promptbranch-repo.json", json.dumps({"schema_version": 1, "project_id": "g-p-demo", "project_home_url": "https://chatgpt.com/g/g-p-demo/project", "repo_id": "chatgpt_claudecode_workflow", "artifact_pattern": "chatgpt_claudecode_workflow_<version>.zip", "role": "release_authority"}))
        archive.writestr("chatgpt_claudecode_workflow_release_control.sh", release_script.read_text(encoding="utf-8"))
        archive.writestr("fresh.txt", "transport payload\n")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "git").write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"status\" ]]; then exit 0; fi\n"
        "if [[ \"$1 $2 $3\" == \"rev-parse --short HEAD\" ]]; then echo abc1234; exit 0; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (fake_bin / "git").chmod(0o755)
    for command in ("promptbranch", "pipx"):
        path = fake_bin / command
        path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)

    canonical = f"chatgpt_claudecode_workflow-2_{version}.zip"
    packager = tmp_path / "packager.sh"
    packager.write_text(
        "#!/usr/bin/env bash\n"
        "python3 - <<'INNERPY'\n"
        "import zipfile\n"
        f"with zipfile.ZipFile('{canonical}', 'w') as archive:\n"
        f"    archive.writestr('VERSION', '{version}\\n')\n"
        "    archive.writestr('fresh.txt', 'canonical package\\n')\n"
        "INNERPY\n",
        encoding="utf-8",
    )
    packager.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0"] = "1"

    result = subprocess.run(
        [
            str(release_script),
            "--version", version,
            "--install-from-zip", str(transport),
            "--packager", str(packager),
            "--skip-commit",
            "--skip-source-add",
            "--skip-install",
            "--skip-chown",
            "--skip-service",
            "--skip-docker-logs",
            "--skip-tests",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert f"candidate_transport_zip: {transport}" in result.stdout
    assert f"canonical_artifact_zip:  {repo / canonical}" in result.stdout
    assert f"artifact_zip:   {canonical}" in result.stdout
    assert (repo / canonical).is_file()
    assert not (repo / transport.name).exists()


def test_release_control_uploads_only_canonical_artifact_path() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    assert "artifact_prefix_from_zip_name" not in script
    assert 'artifact_project_name="${PROMPTBRANCH_ARTIFACT_PROJECT_NAME:-${repo_basename}}"' in script
    assert 'candidate_transport_zip="${download_zip}"' in script
    assert 'canonical_artifact_zip="${repo_root}/${artifact_zip}"' in script
    assert 'cp "${download_zip}" "${canonical_artifact_zip}"' in script
    assert 'promptbranch src add "${canonical_artifact_zip}"' in script
    assert 'promptbranch src add "${candidate_transport_zip}"' not in script
    assert 'pb artifact adopt "${artifact_zip}" --from-project-source' in script



def test_release_control_uses_one_exact_live_slot_without_profile_pooling_static() -> None:
    script = Path("chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")

    visual = 'pb test visual-artifact-roundtrip --profile-dir "${live_profile_pool_slot_dir}" --no-profile-lease'
    release = 'pb test release-live --profile-dir "${live_profile_pool_slot_dir}" --no-profile-lease'
    assert visual in script
    assert release in script
    assert 'pb test visual-artifact-roundtrip --profile-dir "${live_profile_pool_slot_dir}" --profile-lease' not in script
    assert 'pb test release-live --profile-dir "${live_profile_pool_slot_dir}" --profile-lease' not in script
    assert "continuous_live_profile_policy: exact_resolved_slot_without_profile_pooling" in script
    assert "continuous_live_profile_container_dir: /app/profile" in script


def test_release_control_requires_independent_full_localhost_execution_static() -> None:
    script = Path("chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    function = script[script.index("run_full_test_transport()") : script.index("all_test_step_specs=()")]

    assert "full_localhost_policy: independent_execution_required" in function
    assert "full_localhost_direct_evidence_reuse: forbidden" in function
    assert "write_reused_localhost_browser_lifecycle_summary" not in function
    assert '"reusable_browser_source_lifecycle_groups": []' in script
    assert '"full_localhost_policy": "independent_execution_required"' in script


def test_release_control_cloudflare_classification_requires_actual_challenge_evidence_static() -> None:
    script = Path("chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    function = script[script.index("run_all_log_has_cloudflare_challenge()") : script.index("run_all_ensure_shared_live_conversation()")]

    assert '"cloudflare",' not in function
    assert '"verify you are human"' in function
    assert '\"challenge_detected\": true' in function
    assert "submit_causality_not_confirmed" not in function


def test_release_control_rate_limit_retry_requires_structured_true_evidence(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    function_text = script.split("run_all_log_has_rate_limit_evidence() {", 1)[1].split(
        "run_all_log_has_live_bootstrap_guardrail() {", 1
    )[0]
    function_text = "run_all_log_has_rate_limit_evidence() {" + function_text

    passive_log = tmp_path / "passive.log"
    passive_log.write_text(
        "diagnostic prose mentions HTTP 429 and status=429 but is not structured evidence\n"
        + json.dumps(
            {
                "ok": False,
                "status": "verified_with_recovered_rate_limit",
                "rate_limit_telemetry": {
                    "rate_limit_modal_detected": False,
                    "conversation_history_429_seen": False,
                    "backend_api_guardrail_seen": False,
                    "service_rate_limit_events": [],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    true_log = tmp_path / "true.log"
    true_log.write_text(
        json.dumps(
            {
                "ok": False,
                "status": "rate_limited_failed",
                "rate_limit_telemetry": {
                    "rate_limit_modal_detected": True,
                    "conversation_history_429_seen": False,
                    "service_rate_limit_events": [{"kind": "rate_limit_modal", "status": 429}],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    passive = subprocess.run(
        ["bash", "-c", function_text + '\nrun_all_log_has_rate_limit_evidence "$1"', "bash", str(passive_log)],
        text=True,
        capture_output=True,
    )
    positive = subprocess.run(
        ["bash", "-c", function_text + '\nrun_all_log_has_rate_limit_evidence "$1"', "bash", str(true_log)],
        text=True,
        capture_output=True,
    )

    assert passive.returncode == 1, passive.stderr
    assert positive.returncode == 0, positive.stderr


def test_release_control_progress_eta_and_fail_fast_contract() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert "--fail-fast|--test-fail-fast" in script
    assert "--no-fail-fast|--no-test-fail-fast" in script
    assert '_out_args+=(--fail-fast)' in script
    assert "all_tests_current:" in script
    assert "eta_seconds_approx" in script
    assert "active_remaining" in script
    assert "eta_range" in script
    assert "eta_confidence" in script
    assert "eta_basis" in script
    assert "eta_approx=" in script
    assert "observed_average_per_completed_release_step" not in script
    assert 'PROMPTBRANCH_ETA_TRANSPORT="${label}"' in script
    assert "direct_same_step_eta_prior" in (Path(__file__).resolve().parents[1] / "promptbranch_eta.py").read_text(encoding="utf-8")


def test_release_control_idle_handoff_failure_is_one_causal_failure_with_dependency_skips() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    assert 'run_all_continuous_failure_kind="release_live_idle_handoff_failed"' in script
    assert 'status: release_live_idle_handoff_failed' in script
    assert 'record_all_test_dependency_skipped_step "ask_live"' in script
    assert 'record_all_test_dependency_skipped_step "visual_artifact_roundtrip"' in script
    assert 'record_all_test_dependency_skipped_step "release_live"' in script
    assert '"status": "skipped_dependency_failed"' in script
    assert '"dependency": dependency' in script
    assert '"skipped_count": len(skipped)' in script
    assert 'failed = [step for step in steps if not step["ok"] and step.get("skipped") is not True]' in script
