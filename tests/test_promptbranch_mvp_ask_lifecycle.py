from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

import promptbranch_cli as cli


REPO_ID = "chatgpt_claudecode_workflow-2"
BASELINE_VERSION = "v0.1.123.1"
TARGET_VERSION = "v0.1.124"
NEXT_VERSION = "v0.1.125"
ARTIFACT = f"{REPO_ID}_{TARGET_VERSION}.zip"
CANDIDATE_BYTES = b"candidate-v0.1.124"
CANDIDATE_SHA = hashlib.sha256(CANDIDATE_BYTES).hexdigest()


def _args(profile_dir: Path, *, target: str = TARGET_VERSION) -> argparse.Namespace:
    return argparse.Namespace(
        prompt="continue",
        prompt_file=None,
        prompt_file_mode=None,
        prompt_file_attach_threshold_bytes=None,
        file=None,
        attachments=[],
        new_task=False,
        conversation_url=None,
        protocol=False,
        parse_reply=False,
        print_request_json=False,
        json=False,
        text=False,
        keep_open=False,
        retries=None,
        target_version=target,
        release_type="normal",
        profile_dir=str(profile_dir),
        service_base_url=None,
        service_token=None,
        mvp_proof_step_timeout_seconds=10.0,
        mvp_proof_release_timeout_seconds=10.0,
    )


def _baseline() -> dict:
    return {
        "ok": True,
        "repo_id": REPO_ID,
        "version": BASELINE_VERSION,
        "artifact": f"{REPO_ID}_{BASELINE_VERSION}.zip",
        "sha256": "a" * 64,
        "artifact_current": {"ok": True},
        "selected": {},
    }


def _prepare_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    profile = repo / ".pb_profile"
    (repo / "scripts").mkdir(parents=True)
    profile.mkdir(parents=True)
    release = repo / "chatgpt_claudecode_workflow_release_control.sh"
    release.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    release.chmod(0o755)
    finalizer = repo / "scripts" / "finalize-mvp-proof-cycle.sh"
    finalizer.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    finalizer.chmod(0o755)
    return repo, profile


def test_parser_accepts_one_command_mvp_proof_spelling() -> None:
    args = cli.make_parser().parse_args([
        "ask", "continue", "--target-version", TARGET_VERSION, "--release-type", "normal"
    ])
    assert args.command == "ask"
    assert args.prompt == "continue"
    assert args.target_version == TARGET_VERSION
    assert cli._integrated_mvp_ask_requested(args, args.prompt) is True


def test_integrated_mvp_ask_runs_exact_correlated_lifecycle(monkeypatch, tmp_path, capsys) -> None:
    repo, profile = _prepare_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "_mvp_current_baseline", lambda *a, **k: _baseline())
    monkeypatch.setattr(cli, "_mvp_next_cycle", lambda *a, **k: {"ok": True, "cycle": 1, "status": "mvp_cycle_1_required", "records": []})

    commands: list[list[str]] = []

    def fake_run(command, *, cwd, timeout_seconds, stdout_path=None, stderr_path=None):
        commands.append(list(command))
        release_dir = profile / "release_logs" / TARGET_VERSION
        release_dir.mkdir(parents=True, exist_ok=True)
        if "ask-release" in command:
            payload = {
                "ok": True,
                "status": "reply_validated",
                "ask_release_validation": {"ok": True},
                "selected_protocol_reply": {
                    "request_id": "req-exact",
                    "conversation_url": "https://chatgpt.com/g/project/c/task",
                    "message_id": "message-exact",
                    "answer_id": "answer-exact",
                },
            }
        elif "intake" in command:
            (repo / ARTIFACT).write_bytes(CANDIDATE_BYTES)
            payload = {
                "ok": True,
                "status": "migrated_candidate",
                "download_performed": True,
                "verification_performed": True,
                "migration_performed": True,
                "download": {"filename": ARTIFACT, "sha256": CANDIDATE_SHA},
            }
        elif command[0].endswith("chatgpt_claudecode_workflow_release_control.sh"):
            for name, payload in [
                (f"pb_test.all.{TARGET_VERSION}.summary.json", {"tested": 10, "succeeded": 10, "failed": 0, "skipped": 0, "final_verdict": "GO"}),
                (f"pb_test.visual_artifact_roundtrip.{TARGET_VERSION}.log", {"ok": True, "status": "smoke_zip_verified"}),
                (f"pb_artifact_adopt.{TARGET_VERSION}.json", {"ok": True, "status": "adopted"}),
                (f"pb_artifact_current.{TARGET_VERSION}.json", {"ok": True}),
            ]:
                (release_dir / name).write_text(json.dumps(payload), encoding="utf-8")
            payload = None
        else:
            proof = {
                "ok": True,
                "status": "mvp_proof_cycle_passed",
                "cycle": 1,
                "version": TARGET_VERSION,
                "baseline_version": BASELINE_VERSION,
                "next_version": NEXT_VERSION,
            }
            (release_dir / f"mvp-proof-cycle-1.{TARGET_VERSION}.json").write_text(json.dumps(proof), encoding="utf-8")
            payload = None
        if stdout_path is not None:
            Path(stdout_path).parent.mkdir(parents=True, exist_ok=True)
            Path(stdout_path).write_text(json.dumps(payload or {}), encoding="utf-8")
        return {
            "ok": True,
            "status": "mvp_lifecycle_command_passed",
            "command": command,
            "returncode": 0,
            "duration_seconds": 0.01,
            "timeout_seconds": timeout_seconds,
            "stdout": json.dumps(payload or {}),
            "stderr": "",
            "parsed_json": payload,
            "stdout_path": str(stdout_path) if stdout_path else None,
            "stderr_path": str(stderr_path) if stderr_path else None,
        }

    monkeypatch.setattr(cli, "_run_mvp_lifecycle_command", fake_run)
    rc = asyncio.run(cli.cmd_ask(object(), _args(profile)))
    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "mvp_proof_cycle_passed"
    assert result["consecutive_proof_count"] == "1/2"
    assert result["accepted_current_version"] == TARGET_VERSION

    assert len(commands) == 4
    ask_command, intake_command, release_command, finalizer_command = commands
    assert "ask-release" in ask_command
    assert "--target-version" in ask_command
    assert TARGET_VERSION in ask_command
    assert "--message-id" in intake_command
    assert intake_command[intake_command.index("--message-id") + 1] == "message-exact"
    assert "--answer-id" in intake_command
    assert intake_command[intake_command.index("--answer-id") + 1] == "answer-exact"
    assert "--task" in intake_command
    assert "--latest" not in intake_command
    assert "--adopt-after-validation" in release_command
    assert "--cycle" in finalizer_command
    assert finalizer_command[finalizer_command.index("--cycle") + 1] == "1"


def test_integrated_mvp_ask_stops_before_intake_when_candidate_ask_is_wrong(monkeypatch, tmp_path, capsys) -> None:
    repo, profile = _prepare_repo(tmp_path)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "_mvp_current_baseline", lambda *a, **k: _baseline())
    monkeypatch.setattr(cli, "_mvp_next_cycle", lambda *a, **k: {"ok": True, "cycle": 1, "status": "mvp_cycle_1_required", "records": []})
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(list(command))
        return {
            "ok": True,
            "status": "mvp_lifecycle_command_passed",
            "command": command,
            "returncode": 0,
            "duration_seconds": 0.01,
            "timeout_seconds": 10,
            "stdout": json.dumps({"ok": False, "status": "no_artifact"}),
            "stderr": "",
            "parsed_json": {"ok": False, "status": "no_artifact", "ask_release_validation": {"ok": False}},
            "stdout_path": None,
            "stderr_path": None,
        }

    monkeypatch.setattr(cli, "_run_mvp_lifecycle_command", fake_run)
    rc = asyncio.run(cli.cmd_ask(object(), _args(profile)))
    assert rc != 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "mvp_release_candidate_ask_failed"
    assert len(commands) == 1
    assert "verified" not in result.get("operator_instruction", "").lower()


def test_integrated_cycle_2_returns_final_mvp_status(monkeypatch, tmp_path, capsys) -> None:
    repo, profile = _prepare_repo(tmp_path)
    monkeypatch.chdir(repo)
    cycle2_baseline = {**_baseline(), "version": "v0.1.124", "artifact": f"{REPO_ID}_v0.1.124.zip"}
    monkeypatch.setattr(cli, "_mvp_current_baseline", lambda *a, **k: cycle2_baseline)
    monkeypatch.setattr(cli, "_mvp_next_cycle", lambda *a, **k: {"ok": True, "cycle": 2, "status": "mvp_cycle_2_required", "records": []})

    target = "v0.1.125"
    artifact = f"{REPO_ID}_{target}.zip"
    candidate_bytes = b"candidate-v0.1.125"
    candidate_sha = hashlib.sha256(candidate_bytes).hexdigest()

    def fake_run(command, *, cwd, timeout_seconds, stdout_path=None, stderr_path=None):
        release_dir = profile / "release_logs" / target
        release_dir.mkdir(parents=True, exist_ok=True)
        if "ask-release" in command:
            payload = {"ok": True, "ask_release_validation": {"ok": True}, "selected_protocol_reply": {"conversation_url": "https://chatgpt.com/g/p/c/t", "message_id": "m", "answer_id": "a"}}
        elif "intake" in command:
            (repo / artifact).write_bytes(candidate_bytes)
            payload = {"ok": True, "status": "migrated_candidate", "download_performed": True, "verification_performed": True, "migration_performed": True, "download": {"sha256": candidate_sha}}
        elif command[0].endswith("chatgpt_claudecode_workflow_release_control.sh"):
            for name in [f"pb_test.all.{target}.summary.json", f"pb_test.visual_artifact_roundtrip.{target}.log", f"pb_artifact_adopt.{target}.json", f"pb_artifact_current.{target}.json"]:
                (release_dir / name).write_text("{}", encoding="utf-8")
            payload = None
        else:
            proof = {"ok": True, "status": "mvp_proof_cycle_passed", "cycle": 2, "version": target}
            (release_dir / f"mvp-proof-cycle-2.{target}.json").write_text(json.dumps(proof), encoding="utf-8")
            payload = None
        return {"ok": True, "returncode": 0, "parsed_json": payload, "stdout": json.dumps(payload or {}), "stderr": "", "command": command, "status": "passed", "duration_seconds": 0.01, "timeout_seconds": timeout_seconds, "stdout_path": str(stdout_path) if stdout_path else None, "stderr_path": str(stderr_path) if stderr_path else None}

    monkeypatch.setattr(cli, "_run_mvp_lifecycle_command", fake_run)
    rc = asyncio.run(cli.cmd_ask(object(), _args(profile, target=target)))
    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "mvp_verified"
    assert result["consecutive_proof_count"] == "2/2"
    assert result["mvp_status"] == "complete"


def test_lifecycle_command_keeps_full_output_on_disk_but_returns_bounded_tails(tmp_path) -> None:
    stdout_path = tmp_path / "full.stdout.log"
    stderr_path = tmp_path / "full.stderr.log"
    large = "x" * 12000
    command = [
        "python3",
        "-c",
        "import sys; print(%r); print(%r, file=sys.stderr)" % (large, large),
    ]
    result = cli._run_mvp_lifecycle_command(
        command,
        cwd=tmp_path,
        timeout_seconds=10,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    assert result["ok"] is True
    assert "stdout" not in result
    assert "stderr" not in result
    assert len(result["stdout_tail"]) <= 4000
    assert len(result["stderr_tail"]) <= 4000
    assert stdout_path.stat().st_size > 12000
    assert stderr_path.stat().st_size > 12000

    public = cli._mvp_stage_record("strict_release_control", result)
    assert "parsed_json" not in public
    assert len(public["stdout_tail"]) <= 4000
    assert public["stdout_path"] == str(stdout_path)
