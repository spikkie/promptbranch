from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "post-release-validation.sh"


def _write_fake_promptbranch(
    bin_dir: Path,
    initial_artifact_version: str,
    adopted_version: str | None = None,
    fail_protocol_until_adopted: bool = False,
    candidate_mvp_complete: bool = False,
    candidate_no_artifact_precondition: bool = False,
) -> Path:
    exe = bin_dir / "promptbranch"
    adopted_version = adopted_version or initial_artifact_version
    exe.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        f"initial = {initial_artifact_version!r}\n"
        f"adopted = {adopted_version!r}\n"
        f"fail_protocol_until_adopted = {fail_protocol_until_adopted!r}\n"
        f"candidate_mvp_complete = {candidate_mvp_complete!r}\n"
        f"candidate_no_artifact_precondition = {candidate_no_artifact_precondition!r}\n"
        "state_file = Path(__file__).with_name('adopted_state.txt')\n"
        "calls_file = Path(__file__).with_name('calls.jsonl')\n"
        "def record(args):\n"
        "    calls_file.write_text(calls_file.read_text() + json.dumps(args) + '\\n' if calls_file.exists() else json.dumps(args) + '\\n')\n"
        "def current_version():\n"
        "    return state_file.read_text().strip() if state_file.exists() else initial\n"
        "def current_payload():\n"
        "    version = current_version()\n"
        "    return {\n"
        "        'ok': True,\n"
        "        'action': 'artifact_current',\n"
        "        'runtime': {'version': adopted, 'package_version': adopted.removeprefix('v')},\n"
        "        'state': {\n"
        "            'artifact_version': version,\n"
        "            'source_version': version,\n"
        "            'artifact_ref': f'chatgpt_claudecode_workflow_{version}.zip',\n"
        "            'source_ref': f'chatgpt_claudecode_workflow_{version}.zip',\n"
        "        },\n"
        "        'registry_current': {'version': version, 'filename': f'chatgpt_claudecode_workflow_{version}.zip'},\n"
        "    }\n"
        "args = sys.argv[1:]\n"
        "record(args)\n"
        "if args == ['artifact', 'current', '--json']:\n"
        "    print(json.dumps(current_payload()))\n"
        "    raise SystemExit(0)\n"
        "if len(args) == 5 and args[:2] == ['artifact', 'adopt'] and args[3:] == ['--from-project-source', '--json']:\n"
        "    state_file.write_text(adopted)\n"
        "    print(json.dumps({'ok': True, 'action': 'artifact_adopt', 'artifact_ref': args[2], 'artifact_version': adopted}))\n"
        "    raise SystemExit(0)\n"
        "if args and args[0] == 'ask':\n"
        "    if fail_protocol_until_adopted and current_version() != adopted:\n"
        "        print(json.dumps({'ok': False, 'action': 'ask_protocol_run', 'error': 'wrong_baseline', 'current_version': current_version(), 'expected': adopted}))\n"
        "        raise SystemExit(7)\n"
        "    print(json.dumps({'ok': True, 'action': 'ask_protocol_run', 'status': 'reply_validated', 'reply_validation_ok': True, 'baseline': {'input_version': current_version()}}))\n"
        "    raise SystemExit(0)\n"
        "if args == ['artifact', 'intake', '--from-last-answer', '--dry-run', '--json']:\n"
        "    print(json.dumps({'ok': True, 'action': 'artifact_intake', 'status': 'no_artifact'}))\n"
        "    raise SystemExit(0)\n"
        "if args[:2] == ['artifact', 'candidate-run']:\n"
        "    require_complete = '--require-complete' in args\n"
        "    execute_until_blocked = '--execute-until-blocked' in args\n"
        "    scoped_adopted_current = False\n"
        "    if '--version' in args:\n"
        "        try:\n"
        "            scoped_adopted_current = args[args.index('--version') + 1] == current_version() == adopted\n"
        "        except Exception:\n"
        "            scoped_adopted_current = False\n"
        "    effective_mvp_complete = bool(candidate_mvp_complete or scoped_adopted_current)\n"
        "    mode = 'execute_until_blocked' if execute_until_blocked else 'plan_only'\n"
        "    mvp_status = 'candidate_mvp_complete' if effective_mvp_complete else ('candidate_mvp_no_artifact_candidate' if candidate_no_artifact_precondition else 'candidate_mvp_intake_pending')\n"
        "    payload = {\n"
        "        'ok': True,\n"
        "        'action': 'artifact_candidate_run',\n"
        "        'status': 'candidate_mvp_complete' if effective_mvp_complete else ('candidate_run_cycle_precondition_failed' if candidate_no_artifact_precondition and execute_until_blocked else 'candidate_next_inspection_required'),\n"
        "        'mode': mode,\n"
        "        'execute_until_blocked': execute_until_blocked,\n"
        "        'mutating_actions_executed': bool(execute_until_blocked and effective_mvp_complete and not scoped_adopted_current),\n"
        "        'download_performed': bool(execute_until_blocked and effective_mvp_complete and not scoped_adopted_current),\n"
        "        'verification_performed': bool(execute_until_blocked and effective_mvp_complete and not scoped_adopted_current),\n"
        "        'migration_performed': bool(execute_until_blocked and effective_mvp_complete and not scoped_adopted_current),\n"
        "        'candidate_test_performed': bool(execute_until_blocked and effective_mvp_complete and not scoped_adopted_current),\n"
        "        'adoption_performed': bool(execute_until_blocked and effective_mvp_complete and not scoped_adopted_current),\n"
        "        'cycle_step_count': 0 if scoped_adopted_current else (1 if candidate_no_artifact_precondition and execute_until_blocked else (4 if execute_until_blocked and effective_mvp_complete else 0)),\n"
        "        'stopped_reason': 'candidate_already_accepted' if scoped_adopted_current else ('no_artifact_candidate' if candidate_no_artifact_precondition and execute_until_blocked else ('accepted_candidate' if execute_until_blocked and effective_mvp_complete else None)),\n"
        "        'recommended_next_command': {'kind': 'continue_from_adopted_baseline' if effective_mvp_complete else ('no_artifact_candidate' if candidate_no_artifact_precondition else 'intake_candidate')},\n"
        "        'mvp_complete': effective_mvp_complete,\n"
        "        'mvp_completion': {'ok': effective_mvp_complete, 'status': mvp_status, 'proof_source': 'adopted_current' if scoped_adopted_current else 'candidate_registry'},\n"
        "    }\n"
        "    if require_complete and not effective_mvp_complete:\n"
        "        payload['ok'] = False\n"
        "        payload['error'] = 'artifact candidate MVP completion proof is required but not satisfied'\n"
        "        print(json.dumps(payload))\n"
        "        raise SystemExit(1)\n"
        "    print(json.dumps(payload))\n"
        "    raise SystemExit(0)\n"
        "if args == ['test', 'full', '--json']:\n"
        "    print(json.dumps({'ok': True, 'action': 'test_suite'}))\n"
        "    raise SystemExit(0)\n"
        "if len(args) == 4 and args[:2] == ['test', 'report'] and args[3] == '--json':\n"
        "    print(json.dumps({'ok': True, 'action': 'test_report', 'status': 'verified'}))\n"
        "    raise SystemExit(0)\n"
        "print(json.dumps({'ok': False, 'error': 'unexpected_args', 'argv': args}))\n"
        "raise SystemExit(2)\n",
        encoding="utf-8",
    )
    exe.chmod(0o755)
    return exe

def _run_validation(
    tmp_path: Path,
    artifact_version: str,
    requested_version: str,
    *extra_args: str,
    adopted_version: str | None = None,
    fail_protocol_until_adopted: bool = False,
    skip_protocol: bool = True,
    skip_artifact_intake: bool = True,
    skip_tests: bool = True,
    candidate_mvp_complete: bool = False,
    candidate_no_artifact_precondition: bool = False,
) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    bin_dir = tmp_path / "bin"
    repo.mkdir()
    bin_dir.mkdir()
    (repo / "VERSION").write_text(requested_version + "\n", encoding="utf-8")
    (repo / f"chatgpt_claudecode_workflow_{requested_version}.zip").write_text("fake zip for adopt command selection\n", encoding="utf-8")
    _write_fake_promptbranch(
        bin_dir,
        artifact_version,
        adopted_version=adopted_version or requested_version,
        fail_protocol_until_adopted=fail_protocol_until_adopted,
        candidate_mvp_complete=candidate_mvp_complete,
        candidate_no_artifact_precondition=candidate_no_artifact_precondition,
    )
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["POST_RELEASE_VALIDATION_DISABLE_SESSION_TEE"] = "1"
    return subprocess.run(
        [
            str(SCRIPT),
            "--version",
            requested_version,
            *( ["--skip-protocol-smoke"] if skip_protocol else [] ),
            *( ["--skip-artifact-intake"] if skip_artifact_intake else [] ),
            *( ["--skip-tests"] if skip_tests else [] ),
            "--skip-zip-hygiene",
            *extra_args,
        ],
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
        check=False,
    )


def _summary(repo: Path, version: str) -> dict:
    summary_path = repo / ".pb_profile" / "release_logs" / version / f"post_release_validation.{version}.summary.json"
    return json.loads(summary_path.read_text(encoding="utf-8"))


def _semantic(repo: Path, version: str) -> dict:
    semantic_path = repo / ".pb_profile" / "release_logs" / version / f"pb_artifact_current.{version}.semantic.json"
    return json.loads(semantic_path.read_text(encoding="utf-8"))


def test_post_release_validation_treats_unadopted_baseline_as_diagnostic_by_default(tmp_path: Path) -> None:
    result = _run_validation(tmp_path, artifact_version="v0.0.225", requested_version="v0.0.225.2")

    assert result.returncode == 0, result.stdout
    repo = tmp_path / "repo"
    summary = _summary(repo, "v0.0.225.2")
    assert summary["ok"] is True
    assert summary["steps"]["artifact_current"]["rc"] == 0
    assert summary["steps"]["artifact_current_semantic"]["rc"] == 1
    assert summary["steps"]["artifact_candidate_run_plan"]["phase"] == "pre_adoption"
    assert summary["steps"]["artifact_candidate_run_plan"]["rc"] == 0
    assert summary["steps"]["artifact_candidate_run_plan"]["require_complete"] is False
    assert summary["steps"]["artifact_candidate_run_plan"]["mvp_complete"] is False
    assert summary["steps"]["artifact_adopt"] == {"enabled": False, "performed": False, "rc": 0}

    semantic = _semantic(repo, "v0.0.225.2")
    assert semantic["ok"] is False
    assert {item["field"] for item in semantic["mismatches"]} == {
        "state.artifact_version",
        "state.source_version",
        "registry_current.version",
    }


def test_post_release_validation_can_require_already_adopted_baseline(tmp_path: Path) -> None:
    result = _run_validation(
        tmp_path,
        "v0.0.225",
        "v0.0.225.2",
        "--require-adopted-baseline",
    )

    assert result.returncode == 1
    summary = _summary(tmp_path / "repo", "v0.0.225.2")
    assert summary["ok"] is False
    assert summary["require_adopted_baseline"] is True
    assert summary["steps"]["artifact_current_semantic"]["rc"] == 1


def test_post_release_validation_adopts_after_success_when_requested(tmp_path: Path) -> None:
    result = _run_validation(
        tmp_path,
        "v0.0.225",
        "v0.0.225.2",
        "--adopt-if-accepted",
        adopted_version="v0.0.225.2",
    )

    assert result.returncode == 0, result.stdout
    repo = tmp_path / "repo"
    summary = _summary(repo, "v0.0.225.2")
    assert summary["ok"] is True
    assert summary["adopt_if_accepted"] is True
    assert summary["steps"]["artifact_current_semantic"]["rc"] == 1
    assert summary["steps"]["artifact_adopt"] == {"enabled": True, "performed": True, "rc": 0}
    assert summary["steps"]["artifact_current_after_adopt_semantic"] == {"enabled": True, "performed": True, "rc": 0}

    after_adopt = json.loads(
        (repo / ".pb_profile" / "release_logs" / "v0.0.225.2" / "pb_artifact_current_after_adopt.v0.0.225.2.semantic.json").read_text(encoding="utf-8")
    )
    assert after_adopt["ok"] is True



def test_post_release_validation_can_require_candidate_mvp_completion_success(tmp_path: Path) -> None:
    result = _run_validation(
        tmp_path,
        "v0.0.236",
        "v0.0.236",
        "--require-candidate-mvp-complete",
        skip_protocol=True,
        skip_artifact_intake=True,
        skip_tests=True,
        candidate_mvp_complete=True,
    )

    assert result.returncode == 0, result.stdout
    summary = _summary(tmp_path / "repo", "v0.0.236")
    step = summary["steps"]["artifact_candidate_run_plan"]
    assert summary["require_candidate_mvp_complete"] is True
    assert step["require_complete"] is True
    assert step["rc"] == 0
    assert step["mvp_complete"] is True
    assert step["mvp_completion_status"] == "candidate_mvp_complete"


def test_post_release_validation_can_require_candidate_mvp_completion_failure(tmp_path: Path) -> None:
    result = _run_validation(
        tmp_path,
        "v0.0.236",
        "v0.0.236",
        "--require-candidate-mvp-complete",
        skip_protocol=True,
        skip_artifact_intake=True,
        skip_tests=True,
        candidate_mvp_complete=False,
    )

    assert result.returncode == 1
    summary = _summary(tmp_path / "repo", "v0.0.236")
    step = summary["steps"]["artifact_candidate_run_plan"]
    assert summary["ok"] is False
    assert summary["require_candidate_mvp_complete"] is True
    assert step["require_complete"] is True
    assert step["rc"] == 1
    assert step["mvp_complete"] is False
    assert step["mvp_completion_status"] == "candidate_mvp_intake_pending"




def test_post_release_validation_can_complete_candidate_mvp_cycle_success(tmp_path: Path) -> None:
    result = _run_validation(
        tmp_path,
        "v0.0.236",
        "v0.0.236",
        "--complete-candidate-mvp",
        "--candidate-mvp-max-steps",
        "6",
        "--candidate-run-step-timeout",
        "42",
        skip_protocol=True,
        skip_artifact_intake=True,
        skip_tests=True,
        candidate_mvp_complete=True,
    )

    assert result.returncode == 0, result.stdout
    summary = _summary(tmp_path / "repo", "v0.0.236")
    step = summary["steps"]["artifact_candidate_run_plan"]
    assert summary["complete_candidate_mvp"] is True
    assert summary["require_candidate_mvp_complete"] is True
    assert summary["candidate_mvp_max_steps"] == 6
    assert summary["candidate_run_step_timeout_seconds"] == 42.0
    assert step["mode"] == "execute_until_blocked"
    assert step["require_complete"] is True
    assert step["execute_until_blocked"] is True
    assert step["mutating_actions_executed"] is True
    assert step["mvp_complete"] is True
    assert step["mvp_completion_status"] == "candidate_mvp_complete"
    assert step["adoption_performed"] is True


def test_post_release_validation_complete_candidate_mvp_cycle_reports_no_artifact_precondition(tmp_path: Path) -> None:
    result = _run_validation(
        tmp_path,
        "v0.0.236",
        "v0.0.236",
        "--complete-candidate-mvp",
        skip_protocol=True,
        skip_artifact_intake=False,
        skip_tests=True,
        candidate_mvp_complete=False,
        candidate_no_artifact_precondition=True,
    )

    assert result.returncode == 0, result.stdout
    summary = _summary(tmp_path / "repo", "v0.0.236")
    step = summary["steps"]["artifact_candidate_run_plan"]
    assert summary["ok"] is True
    assert summary["failure_count"] == 0
    assert summary["complete_candidate_mvp"] is True
    assert step["mode"] == "execute_until_blocked"
    assert step["rc"] == 0
    assert step["status"] == "candidate_run_cycle_precondition_failed"
    assert step["mvp_complete"] is False
    assert step["mvp_completion_status"] == "candidate_mvp_no_artifact_candidate"
    assert step["recommended_next_kind"] == "no_artifact_candidate"
    assert step["stopped_reason"] == "no_artifact_candidate"
    assert step["mutating_actions_executed"] is False
    assert step["download_performed"] is False
    assert step["verification_performed"] is False
    assert step["migration_performed"] is False
    assert step["adoption_performed"] is False


def test_post_release_validation_complete_candidate_mvp_cycle_fails_closed_when_incomplete(tmp_path: Path) -> None:
    result = _run_validation(
        tmp_path,
        "v0.0.236",
        "v0.0.236",
        "--complete-candidate-mvp",
        skip_protocol=True,
        skip_artifact_intake=True,
        skip_tests=True,
        candidate_mvp_complete=False,
    )

    assert result.returncode == 1
    summary = _summary(tmp_path / "repo", "v0.0.236")
    step = summary["steps"]["artifact_candidate_run_plan"]
    assert summary["ok"] is False
    assert summary["complete_candidate_mvp"] is True
    assert step["mode"] == "execute_until_blocked"
    assert step["rc"] == 1
    assert step["mvp_complete"] is False
    assert step["mvp_completion_status"] == "candidate_mvp_intake_pending"

def test_post_release_validation_adopt_if_accepted_runs_protocol_after_adoption(tmp_path: Path) -> None:
    result = _run_validation(
        tmp_path,
        "v0.0.225.2",
        "v0.0.226",
        "--adopt-if-accepted",
        adopted_version="v0.0.226",
        fail_protocol_until_adopted=True,
        skip_protocol=False,
        skip_artifact_intake=False,
        skip_tests=True,
    )

    assert result.returncode == 0, result.stdout
    repo = tmp_path / "repo"
    summary = _summary(repo, "v0.0.226")
    assert summary["ok"] is True
    assert summary["steps"]["artifact_current_semantic"]["rc"] == 1
    assert summary["steps"]["artifact_adopt"] == {"enabled": True, "performed": True, "rc": 0}
    assert summary["steps"]["artifact_current_after_adopt_semantic"] == {"enabled": True, "performed": True, "rc": 0}
    assert summary["steps"]["protocol_smoke"] == {"phase": "post_adoption", "rc": 0}
    assert summary["steps"]["artifact_intake_dry_run"] == {"phase": "post_adoption", "rc": 0}
    assert summary["steps"]["artifact_candidate_run_plan"]["phase"] == "post_adoption"
    assert summary["steps"]["artifact_candidate_run_plan"]["rc"] == 0
    assert summary["steps"]["artifact_candidate_run_plan"]["require_complete"] is False

    calls_path = tmp_path / "bin" / "calls.jsonl"
    calls = [json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines()]
    adopt_index = next(i for i, call in enumerate(calls) if call[:2] == ["artifact", "adopt"])
    ask_index = next(i for i, call in enumerate(calls) if call and call[0] == "ask")
    candidate_run_index = next(i for i, call in enumerate(calls) if call[:2] == ["artifact", "candidate-run"])
    assert adopt_index < ask_index < candidate_run_index


def test_post_release_validation_classifies_strict_no_artifact_as_operator_precondition(tmp_path: Path) -> None:
    result = _run_validation(
        tmp_path,
        "v0.0.266",
        "v0.0.266",
        "--complete-candidate-mvp",
        "--require-real-candidate-mvp",
        skip_protocol=True,
        skip_artifact_intake=True,
        skip_tests=True,
        candidate_mvp_complete=False,
        candidate_no_artifact_precondition=True,
    )

    assert result.returncode == 1
    summary = _summary(tmp_path / "repo", "v0.0.266")
    classification = summary["validation_classification"]
    assert classification["status"] == "failed"
    assert classification["primary_category"] == "operator_precondition_failure"
    assert classification["blocking_categories"] == ["operator_precondition_failure"]
    assert classification["blocking_failures"] == [
        {
            "blocking": True,
            "category": "operator_precondition_failure",
            "phase": "pre_adoption",
            "rc": 1,
            "reason": "strict real-candidate validation was requested but no real artifact candidate was selected",
            "severity": "blocking",
            "step": "artifact_candidate_run_plan",
        }
    ]
    assert summary["primary_failure_category"] == "operator_precondition_failure"
    assert summary["blocking_failure_categories"] == ["operator_precondition_failure"]


def test_post_release_validation_classifies_unadopted_baseline_as_diagnostic(tmp_path: Path) -> None:
    result = _run_validation(
        tmp_path,
        artifact_version="v0.0.265",
        requested_version="v0.0.266",
        skip_protocol=True,
        skip_artifact_intake=True,
        skip_tests=True,
    )

    assert result.returncode == 0, result.stdout
    summary = _summary(tmp_path / "repo", "v0.0.266")
    classification = summary["validation_classification"]
    assert classification["status"] == "passed"
    assert classification["blocking_failure_count"] == 0
    assert classification["primary_category"] == "none"
    assert classification["diagnostics"] == [
        {
            "blocking": False,
            "category": "artifact_state_diagnostic",
            "phase": None,
            "rc": 1,
            "reason": "pre-adoption artifact current mismatch is diagnostic unless --require-adopted-baseline is set",
            "severity": "diagnostic",
            "step": "artifact_current_semantic",
        }
    ]
