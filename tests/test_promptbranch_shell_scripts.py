import json
import os
import re
import subprocess
import sys
from pathlib import Path

from promptbranch_eta import append_eta_observation


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

    calls = tmp_path / "calls.log"
    fake_promptbranch = repo / "promptbranch_cli.py"
    fake_promptbranch.write_text(
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "with Path(os.environ['PB_FAKE_CALL_LOG']).open('a', encoding='utf-8') as fh: fh.write('promptbranch ' + ' '.join(args) + '\\n')\n"
        "if args[:2] == ['artifact', 'current']:\n"
        f" print(json.dumps({{'ok': True, 'action': 'artifact_current_all', 'repo_count': 1, 'repos': {{'chatgpt_claudecode_workflow': {{'ok': True, 'action': 'artifact_current', 'runtime': {{'version': {version!r}, 'package_version': '9.9.9.1'}}, 'state': {{'artifact_version': {version!r}, 'source_version': {version!r}, 'artifact_ref': {artifact!r}, 'source_ref': {artifact!r}}}, 'registry_current': {{'version': {version!r}, 'filename': {artifact!r}}}, 'baseline_roles': {{'adopted_artifact_version': {version!r}, 'adopted_source_version': {version!r}, 'registry_current_version': {version!r}}}, 'consistency': {{'registry_current_matches_state_artifact': True, 'state_source_matches_state_artifact': True, 'code_version_matches_state_source': True}}}}}}, 'missing_repo_count': 0, 'missing_repos': []}})); raise SystemExit(0)\n"
        "if args and args[0] in {'ask', 'ask-release'}: print(json.dumps({'ok': True, 'action': 'ask_protocol_run', 'status': 'reply_validated', 'reply_status': 'no_artifact'})); raise SystemExit(0)\n"
        "if args[:2] == ['artifact', 'intake']: print(json.dumps({'ok': True, 'action': 'artifact_intake', 'status': 'no_artifact', 'download_performed': False})); raise SystemExit(0)\n"
        "if args[:2] == ['artifact', 'candidate-run']: print(json.dumps({'ok': True, 'action': 'artifact_candidate_run', 'status': 'candidate_next_inspection_required', 'mode': 'plan_only', 'mutating_actions_executed': False})); raise SystemExit(0)\n"
        f"if args[:2] == ['test', 'full']: print(json.dumps({{'ok': True, 'action': 'test_suite', 'version': {version!r}}})); raise SystemExit(0)\n"
        "if args[:2] == ['test', 'report']: print(json.dumps({'ok': True, 'action': 'test_report', 'status': 'verified', 'failure_count': 0, 'suite': {'release_validation_groups': {'ok': True, 'missing_required_groups': [], 'groups': {'artifact_json_contracts': {'ok': True}, 'browser_scheduler_source_lifecycle': {'ok': True}, 'project_control_surface': {'ok': True}}}}})); raise SystemExit(0)\n"
        "if args[:2] == ['release', 'lifecycle-status']: print(json.dumps({'ok': True, 'action': 'release_lifecycle_status', 'status': 'passed', 'severity': 'ok', 'lifecycle_phase': 'adopted_current', 'operator_verdict': 'continue_normal_development', 'warning_codes': [], 'blocker_codes': [], 'next_safe_action': {'kind': 'continue_normal_development'}})); raise SystemExit(0)\n"
        "print(json.dumps({'ok': False, 'error': 'unexpected_args', 'argv': args})); raise SystemExit(2)\n",
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "scripts" / "post-release-validation.sh"
    env = os.environ.copy()
    env["PB_PYTHON"] = sys.executable
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
    calls = tmp_path / "candidate_run_calls.json"
    fake_cli = repo / "promptbranch_cli.py"
    fake_cli.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        f"Path({str(calls)!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n"
        "print(json.dumps({'ok': True, 'action': 'artifact_candidate_run', 'status': 'candidate_run_cycle_acceptance_ready', 'mvp_complete': True, 'download_performed': True, 'verification_performed': True, 'migration_performed': True, 'candidate_test_performed': True, 'adoption_performed': False}))\n",
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "finalize-artifact-intake-mvp.sh"
    env = os.environ.copy()
    env["PB_PYTHON"] = sys.executable

    result = subprocess.run(
        [
            str(script),
            "--version", "v9.9.9",
            "--target-version", "v9.9.10",
            "--candidate-mvp-max-steps", "6",
            "--candidate-run-step-timeout", "42",
            "--require-real-candidate-mvp",
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "final Artifact Intake MVP validation starting" in result.stdout
    assert "final Artifact Intake MVP validation passed" in result.stdout
    args = json.loads(calls.read_text(encoding="utf-8"))
    assert args == [
        "artifact", "candidate-run", "--execute-until-blocked", "--max-steps", "6",
        "--step-timeout", "42", "--require-complete", "--profile", "smoke", "--json", "--require-real-candidate",
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
    fake_cli = repo / "promptbranch_cli.py"
    fake_cli.write_text(
        "import json\n"
        "print(json.dumps({'ok': True, 'status': 'candidate_run_cycle_completed', 'mvp_complete': True, 'download_performed': True, 'verification_performed': True, 'migration_performed': True, 'candidate_test_performed': True, 'adoption_performed': True}))\n",
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "finalize-artifact-intake-mvp.sh"
    env = os.environ.copy()
    env["PB_PYTHON"] = sys.executable

    result = subprocess.run(
        [str(script), "--version", "v9.9.9", "--target-version", "v9.9.10", "--require-real-candidate-mvp"],
        cwd=repo,
        env=env,
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





def test_gitignore_allows_intentional_release_harness_and_metadata() -> None:
    gitignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")

    assert '# ollama_mcp_verification_harness/  # intentionally tracked release verification harness' in gitignore
    assert '# ollama_mcp_verification_harness_v2/  # intentionally tracked release verification harness' in gitignore
    assert '!promptbranch.egg-info/' in gitignore
    assert '!promptbranch.egg-info/**' in gitignore




def test_post_release_validation_current_semantic_check_uses_repo_loop_entries() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "post-release-validation.sh"
    text = script.read_text(encoding="utf-8")
    assert text.count("def artifact_current_entries") >= 2
    assert 'result["checked_repos"]' in text
    assert 'result["matching_repos"]' in text
    assert '"field": "repos[*]"' in text






def test_docker_build_context_version_guard_declared():
    root = Path(__file__).resolve().parents[1]
    state_machine = (root / "promptbranch_release_state_machine.py").read_text(encoding="utf-8")
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    compose = (root / "docker-compose.chatgpt-service.yml").read_text(encoding="utf-8")

    assert "PROMPTBRANCH_VERSION" in compose
    assert "PROMPTBRANCH_ARTIFACT_SHA256" in compose
    assert "ARG PROMPTBRANCH_VERSION" in dockerfile
    assert "LABEL promptbranch.version" in dockerfile
    assert "Docker build context version mismatch" in dockerfile
    assert '"version_label_exact"' in state_machine
    assert '"artifact_sha_label_exact"' in state_machine
    assert '"source_fingerprint_label_exact"' in state_machine
    assert '"candidate_health_version_exact"' in state_machine








































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









def test_standard_cloudflare_validation_rejects_backend_api_guardrail_static() -> None:
    script = Path("scripts/pb-browser-cloudflare-validation.sh").read_text(encoding="utf-8")
    assert "backend_api_guardrail_seen = _backend_guardrail_403_seen(payload)" in script
    assert "browser_backend_403_guardrail" in script
    assert "backend_api_guardrail_seen is true; browser/profile is forbidden" in script











































def test_install_sh_is_thin_canonical_lifecycle_bootstrap_static() -> None:
    script = (Path(__file__).resolve().parents[1] / "install.sh").read_text(encoding="utf-8")

    assert "run-release-lifecycle-proof.py" in script
    assert '--artifact-conversation-url' in script
    assert '--release-type' in script
    assert '--profile full' in script
    assert '--test-timeout 3600' in script
    obsolete = 'chatgpt_claudecode_workflow_' + 'release_control.sh'
    assert obsolete not in script
    assert '--run-all-tests' not in script
    assert '--adopt-after-validation' not in script
    assert 'set -euo pipefail' not in script

def test_install_sh_is_executable() -> None:
    script = Path(__file__).resolve().parents[1] / "install.sh"
    assert script.is_file()
    assert script.stat().st_mode & 0o111





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






def test_install_sh_rejects_transport_zip_internal_version_mismatch(tmp_path: Path) -> None:
    import sys
    import zipfile

    transport = tmp_path / "promptbranch-transport-unique.zip"
    with zipfile.ZipFile(transport, "w") as archive:
        archive.writestr("VERSION", "v9.9.80\n")
        archive.writestr("pyproject.toml", "[project]\nname='promptbranch'\nversion='9.9.80'\n")
        archive.writestr("promptbranch_cli.py", "print('stub')\n")
        archive.writestr("scripts/run-release-lifecycle-proof.py", "print('stub')\n")

    install = Path(__file__).resolve().parents[1] / "install.sh"
    env = dict(os.environ)
    env["PB_PYTHON"] = sys.executable
    result = subprocess.run(
        [
            str(install),
            "--version", "v9.9.81",
            "--artifact", str(transport),
            "--artifact-conversation-url", "https://chatgpt.com/g/g-p-demo/c/00000000-0000-0000-0000-000000000001",
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode != 0
    assert "candidate ZIP VERSION mismatch" in result.stderr
    assert "expected v9.9.81, got v9.9.80" in result.stderr

def test_import_smoke_explicit_candidate_python_ignores_shadow_path(monkeypatch, tmp_path: Path) -> None:
    import promptbranch_test_suite as suite

    (tmp_path / "VERSION").write_text("v0.0.166\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.setuptools]\npy-modules = ["promptbranch_version"]\n',
        encoding="utf-8",
    )
    candidate_python = tmp_path / "candidate" / "bin" / "python"
    shadow_bin = tmp_path / "shadow" / "bin"
    candidate_python.parent.mkdir(parents=True)
    shadow_bin.mkdir(parents=True)
    candidate_python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    candidate_python.chmod(0o755)
    (shadow_bin / "python").write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    (shadow_bin / "python").chmod(0o755)
    monkeypatch.setenv("PATH", f"{shadow_bin}:{os.environ.get('PATH', '')}")
    captured: dict[str, object] = {}

    class Completed:
        returncode = 0
        stdout = '{"imports":[{"module":"promptbranch_version","ok":true}],"version_consistency":{"ok":true,"expected_version":"0.0.166","observations":[],"missing":[],"mismatches":[]},"runtime_identity":{"ok":true,"expected_python":"candidate","actual_python":"candidate","expected_prefix":"candidate","actual_prefix":"candidate"},"dependency_consistency":{"ok":true,"expected":{},"observations":[],"mismatches":[]}}'
        stderr = ""

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env")
        return Completed()

    monkeypatch.setattr(suite.subprocess, "run", fake_run)

    result = suite.package_import_smoke(repo_path=tmp_path, python_executable=str(candidate_python))

    assert result["ok"] is True
    assert captured["cmd"][0] == str(candidate_python)
    assert str(shadow_bin) in str(captured["env"]["PATH"])










def test_release_validation_group_includes_cross_process_profile_handoff_regressions() -> None:
    source = (Path(__file__).resolve().parents[1] / "promptbranch_test_suite.py").read_text(encoding="utf-8")
    assert "test_cross_process_profile_lock_waits_until_external_owner_releases" in source
    assert "test_cross_process_profile_lock_timeout_honors_queue_deadline_and_reports_owner" in source




def test_finalize_mvp_proof_cycle_contract() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "finalize-mvp-proof-cycle.sh"
    text = script.read_text(encoding="utf-8")
    assert "--from-current-baseline" in text
    assert "--intent-kind mvp_proof_continuation" in text
    assert "scripts/verify-mvp-proof-cycle.py" in text
    assert "pb artifact adopt" not in text
    assert "pb src add" not in text
