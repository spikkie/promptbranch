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
        "if args == ['artifact', 'candidate-run', '--json']:\n"
        "    print(json.dumps({'ok': True, 'action': 'artifact_candidate_run', 'status': 'candidate_next_inspection_required', 'mode': 'plan_only', 'mutating_actions_executed': False}))\n"
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
    )
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
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
    assert summary["steps"]["artifact_candidate_run_plan"] == {"phase": "pre_adoption", "rc": 0}
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
    assert summary["steps"]["artifact_candidate_run_plan"] == {"phase": "post_adoption", "rc": 0}

    calls_path = tmp_path / "bin" / "calls.jsonl"
    calls = [json.loads(line) for line in calls_path.read_text(encoding="utf-8").splitlines()]
    adopt_index = next(i for i, call in enumerate(calls) if call[:2] == ["artifact", "adopt"])
    ask_index = next(i for i, call in enumerate(calls) if call and call[0] == "ask")
    candidate_run_index = next(i for i, call in enumerate(calls) if call[:2] == ["artifact", "candidate-run"])
    assert adopt_index < ask_index < candidate_run_index
