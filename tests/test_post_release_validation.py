from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "post-release-validation.sh"


def _write_fake_promptbranch(bin_dir: Path, artifact_version: str) -> Path:
    exe = bin_dir / "promptbranch"
    payload = {
        "ok": True,
        "action": "artifact_current",
        "runtime": {"version": artifact_version, "package_version": artifact_version.removeprefix("v")},
        "state": {
            "artifact_version": artifact_version,
            "source_version": artifact_version,
            "artifact_ref": f"chatgpt_claudecode_workflow_{artifact_version}.zip",
            "source_ref": f"chatgpt_claudecode_workflow_{artifact_version}.zip",
        },
        "registry_current": {"version": artifact_version, "filename": f"chatgpt_claudecode_workflow_{artifact_version}.zip"},
    }
    exe.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"payload = {payload!r}\n"
        "if sys.argv[1:4] == ['artifact', 'current', '--json']:\n"
        "    print(json.dumps(payload))\n"
        "    raise SystemExit(0)\n"
        "print(json.dumps({'ok': False, 'error': 'unexpected_args', 'argv': sys.argv[1:]}))\n"
        "raise SystemExit(2)\n",
        encoding="utf-8",
    )
    exe.chmod(0o755)
    return exe


def _run_validation(tmp_path: Path, artifact_version: str, requested_version: str) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    bin_dir = tmp_path / "bin"
    repo.mkdir()
    bin_dir.mkdir()
    (repo / "VERSION").write_text(requested_version + "\n", encoding="utf-8")
    _write_fake_promptbranch(bin_dir, artifact_version)
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
        ],
        cwd=repo,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
        check=False,
    )


def test_post_release_validation_fails_when_artifact_current_version_does_not_match(tmp_path: Path) -> None:
    result = _run_validation(tmp_path, artifact_version="v0.0.221", requested_version="v0.0.225.1")

    assert result.returncode == 1
    summary_path = tmp_path / "repo" / ".pb_profile" / "release_logs" / "v0.0.225.1" / "post_release_validation.v0.0.225.1.summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["ok"] is False
    assert summary["steps"]["artifact_current"]["rc"] == 0
    assert summary["steps"]["artifact_current_semantic"]["rc"] == 1

    semantic_path = tmp_path / "repo" / ".pb_profile" / "release_logs" / "v0.0.225.1" / "pb_artifact_current.v0.0.225.1.semantic.json"
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    assert semantic["ok"] is False
    assert {item["field"] for item in semantic["mismatches"]} == {
        "runtime.version",
        "state.artifact_version",
        "state.source_version",
        "registry_current.version",
    }


def test_post_release_validation_passes_when_artifact_current_matches_requested_version(tmp_path: Path) -> None:
    result = _run_validation(tmp_path, artifact_version="v0.0.225.1", requested_version="v0.0.225.1")

    assert result.returncode == 0
    summary_path = tmp_path / "repo" / ".pb_profile" / "release_logs" / "v0.0.225.1" / "post_release_validation.v0.0.225.1.summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["steps"]["artifact_current"]["rc"] == 0
    assert summary["steps"]["artifact_current_semantic"]["rc"] == 0
