from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "post-release-validation.sh"


def _write_fake_promptbranch(bin_dir: Path, initial_artifact_version: str, adopted_version: str | None = None) -> Path:
    exe = bin_dir / "promptbranch"
    adopted_version = adopted_version or initial_artifact_version
    exe.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        f"initial = {initial_artifact_version!r}\n"
        f"adopted = {adopted_version!r}\n"
        "state_file = Path(__file__).with_name('adopted_state.txt')\n"
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
        "if args == ['artifact', 'current', '--json']:\n"
        "    print(json.dumps(current_payload()))\n"
        "    raise SystemExit(0)\n"
        "if len(args) == 5 and args[:2] == ['artifact', 'adopt'] and args[3:] == ['--from-project-source', '--json']:\n"
        "    state_file.write_text(adopted)\n"
        "    print(json.dumps({'ok': True, 'action': 'artifact_adopt', 'artifact_ref': args[2], 'artifact_version': adopted}))\n"
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
) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    bin_dir = tmp_path / "bin"
    repo.mkdir()
    bin_dir.mkdir()
    (repo / "VERSION").write_text(requested_version + "\n", encoding="utf-8")
    (repo / f"chatgpt_claudecode_workflow_{requested_version}.zip").write_text("fake zip for adopt command selection\n", encoding="utf-8")
    _write_fake_promptbranch(bin_dir, artifact_version, adopted_version=adopted_version or requested_version)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    return subprocess.run(
        [
            str(SCRIPT),
            "--version",
            requested_version,
            "--skip-protocol-smoke",
            "--skip-artifact-intake",
            "--skip-tests",
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
    assert summary["steps"]["artifact_adopt"] == {"enabled": False, "rc": 0}

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
    assert summary["steps"]["artifact_adopt"] == {"enabled": True, "rc": 0}
    assert summary["steps"]["artifact_current_after_adopt_semantic"] == {"enabled": True, "rc": 0}

    after_adopt = json.loads(
        (repo / ".pb_profile" / "release_logs" / "v0.0.225.2" / "pb_artifact_current_after_adopt.v0.0.225.2.semantic.json").read_text(encoding="utf-8")
    )
    assert after_adopt["ok"] is True
