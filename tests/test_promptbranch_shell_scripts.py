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
    assert (log_dir / "release-control-tests-only.log").is_file()
    assert "release_logs:" in result.stdout
    assert "service_log:   skipped" in result.stdout
    assert "service_start: skipped" in result.stdout
    assert "service_pid:   skipped" in result.stdout
    call_text = calls.read_text(encoding="utf-8")
    assert "pb test full --json" in call_text
    assert f"pb test report {log_dir / 'pb_test.full.v9.9.9.log'} --json" in call_text
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



def test_release_control_automatically_imports_candidate_zip_without_bcompare(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    version = "v9.9.10"
    artifact = f"chatgpt_claudecode_workflow_{version}.zip"
    (repo / "VERSION").write_text("v0.0.0\n", encoding="utf-8")
    (repo / "stale.txt").write_text("remove me\n", encoding="utf-8")
    (repo / ".env").write_text("LOCAL=1\n", encoding="utf-8")
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

    assert 'local preserved_csv=".git,.env,.generated,.pb_profile,profile,debug_artifacts"' in text
    assert '! -name "debug_artifacts"' in text
    assert "--exclude='debug_artifacts/'" in text
    assert "--exclude='.env'" in text
    assert "--exclude='.env.*'" in text
    assert 'required_root_files = ["VERSION", "pyproject.toml", ".gitignore", ".not_to_zip", script_name]' in text
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
    assert 'mkdir -p "${container_home}" "${container_cache}" "${container_config}" /app/.pb_profile /app/debug_artifacts' in container_script



def test_release_control_recreates_docker_service_and_verifies_version() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    run_script = (root / "run_chatgpt_service.sh").read_text(encoding="utf-8")

    assert 'docker compose -f "${compose_file}" down --remove-orphans' in script
    assert 'docker compose -f "${compose_file}" build --pull' in script
    assert 'docker compose -f "${compose_file}" up -d --force-recreate --remove-orphans' in script
    assert 'service_health_json="${release_log_dir}/promptbranch_service_health.${ver}.json"' in script
    assert 'service version mismatch: expected {expected}, got {actual!r}' in script
    assert 'Docker container was not recreated' in script
    assert 'deploy_promptbranch_service_detached || fail "Docker service recreate/version verification failed"' in script
    assert 'up --build --force-recreate "$@"' in run_script




def test_release_control_health_probe_heredoc_is_valid_python() -> None:
    script = (Path(__file__).resolve().parents[1] / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")
    match = re.search(
        r"service_health_probe\(\) \{.*?<<'INNERPY'\n(?P<code>.*?)\nINNERPY\n\}",
        script,
        flags=re.DOTALL,
    )
    assert match is not None
    code = match.group("code")

    compile(code, "<release-control-service-health-probe>", "exec")
    assert 'handle.write("\\n")' in code

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

def test_release_control_renames_git_hash_packager_output_for_repair_version(tmp_path: Path):
    repo = tmp_path / "repo"
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
        "if [[ \"$1 $2\" == \"test report\" ]]; then echo '{\"ok\": true, \"action\": \"test_report\", \"status\": \"verified\", \"failure_count\": 0}'; exit 0; fi\n"
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
