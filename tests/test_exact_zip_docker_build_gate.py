from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-exact-zip-docker-build.py"


def _candidate_zip(path: Path) -> Path:
    archive = path / "candidate.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for source in ROOT.rglob("*"):
            if not source.is_file():
                continue
            rel = source.relative_to(ROOT)
            if any(part in {".git", ".pb_profile", "__pycache__", ".pytest_cache", "build", "dist"} or part.endswith(".egg-info") for part in rel.parts):
                continue
            if source.suffix in {".pyc", ".pyo", ".zip"}:
                continue
            zf.write(source, rel.as_posix())
    return archive


def test_exact_zip_docker_build_gate_requires_and_verifies_exact_image_identity(tmp_path: Path) -> None:
    archive = _candidate_zip(tmp_path)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        """#!/usr/bin/env python3
import json, os, pathlib, sys
assert not (pathlib.Path.cwd() / '.git').exists()
assert os.environ.get('BUILDX_GIT_INFO') == '0'
assert os.environ.get('BUILDX_GIT_LABELS') == '0'
assert os.environ.get('BUILDX_GIT_CHECK_DIRTY') == '0'
args=sys.argv[1:]
if args[:2] == ['image','inspect']:
    print(json.dumps({
      'promptbranch.version': os.environ['PROMPTBRANCH_VERSION'],
      'promptbranch.artifact_sha256': os.environ['PROMPTBRANCH_ARTIFACT_SHA256'],
      'promptbranch.source_fingerprint': os.environ['PROMPTBRANCH_SOURCE_FINGERPRINT'],
      'promptbranch.release_attempt_id': os.environ['PROMPTBRANCH_RELEASE_ATTEMPT_ID'],
    }))
sys.exit(0)
""",
        encoding="utf-8",
    )
    fake_docker.chmod(0o755)
    git_marker = tmp_path / "git-called"
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "#!/bin/sh\nprintf '%s\\n' called > \"$PROMPTBRANCH_GIT_MARKER\"\nexit 99\n",
        encoding="utf-8",
    )
    fake_git.chmod(0o755)
    env = os.environ.copy()
    env["PROMPTBRANCH_GIT_MARKER"] = str(git_marker)
    env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--package-zip", str(archive), "--json"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "exact_zip_docker_build_verified"
    assert payload["checks"]["build_returncode_zero"] is True
    assert payload["checks"]["version_label_exact"] is True
    assert payload["checks"]["artifact_sha_label_exact"] is True
    assert payload["checks"]["source_fingerprint_label_exact"] is True
    assert payload["checks"]["attempt_id_label_exact"] is True
    assert not git_marker.exists(), "exact-ZIP Docker gate must not invoke git from extracted non-Git context"


def test_exact_zip_docker_build_gate_fails_closed_without_docker(tmp_path: Path) -> None:
    archive = _candidate_zip(tmp_path)
    env = os.environ.copy()
    env["PATH"] = str(tmp_path / "empty-bin")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--package-zip", str(archive), "--json"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["status"] == "docker_unavailable"
