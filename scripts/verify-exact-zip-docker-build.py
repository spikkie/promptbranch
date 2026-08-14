#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from promptbranch_release_state_machine import _safe_extract
from promptbranch_source_fingerprint import source_fingerprint
from promptbranch_version import normalize_version


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> dict[str, Any]:
    proc = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def verify_exact_zip_docker_build(package_zip: Path, *, keep_image: bool = False) -> dict[str, Any]:
    archive = package_zip.expanduser().resolve()
    if not archive.is_file():
        return {"ok": False, "status": "package_zip_missing", "package_zip": str(archive)}
    docker = shutil.which("docker")
    if docker is None:
        return {"ok": False, "status": "docker_unavailable", "package_zip": str(archive)}

    artifact_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="pb-exact-zip-docker-build-") as td:
        root = Path(td) / "extracted"
        _safe_extract(archive, root)
        version_tag = (root / "VERSION").read_text(encoding="utf-8").strip()
        version = normalize_version(version_tag)
        if not version:
            return {"ok": False, "status": "version_authority_invalid", "package_zip": str(archive)}
        fingerprint = source_fingerprint(root)
        sha_prefix = artifact_sha[:12]
        project = f"pb-build-gate-{version.replace('.', '-')}-{sha_prefix}"
        image = f"promptbranch-build-gate:{version}-{sha_prefix}"
        attempt_id = f"exact-final-zip-docker-build:{artifact_sha}"
        compose_file = root / "docker-compose.chatgpt-service.yml"
        env = os.environ.copy()
        env.update(
            {
                "COMPOSE_PROJECT_NAME": project,
                "PROMPTBRANCH_VERSION": version,
                "PROMPTBRANCH_ARTIFACT_SHA256": artifact_sha,
                "PROMPTBRANCH_SOURCE_FINGERPRINT": fingerprint,
                "PROMPTBRANCH_RELEASE_ATTEMPT_ID": attempt_id,
                "PROMPTBRANCH_SERVICE_IMAGE": image,
                "PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE": "1",
                "BUILDKIT_PROGRESS": "plain",
                "BUILDX_GIT_INFO": "0",
                "BUILDX_GIT_LABELS": "0",
                "BUILDX_GIT_CHECK_DIRTY": "0",
            }
        )
        build_command = [docker, "compose", "-p", project, "-f", str(compose_file), "build", "chatgpt-service"]
        build = _run(build_command, cwd=root, env=env)
        inspect: dict[str, Any] = {"returncode": None, "stdout": "", "stderr": "", "labels": {}}
        checks = {"build_returncode_zero": build["returncode"] == 0}
        if build["returncode"] == 0:
            inspect_command = [docker, "image", "inspect", image, "--format", "{{json .Config.Labels}}"]
            inspect = _run(inspect_command, cwd=root, env=env)
            try:
                labels = json.loads(str(inspect.get("stdout") or "{}").strip() or "{}")
            except json.JSONDecodeError:
                labels = {}
            inspect["labels"] = labels
            checks.update(
                {
                    "image_inspect_returncode_zero": inspect["returncode"] == 0,
                    "version_label_exact": str(labels.get("promptbranch.version") or "") == version,
                    "artifact_sha_label_exact": str(labels.get("promptbranch.artifact_sha256") or "") == artifact_sha,
                    "source_fingerprint_label_exact": str(labels.get("promptbranch.source_fingerprint") or "") == fingerprint,
                    "attempt_id_label_exact": str(labels.get("promptbranch.release_attempt_id") or "") == attempt_id,
                }
            )
        ok = all(checks.values())
        cleanup: dict[str, Any] | None = None
        if build["returncode"] == 0 and not keep_image:
            cleanup = _run([docker, "image", "rm", "-f", image], cwd=root, env=env)
        return {
            "ok": ok,
            "status": "exact_zip_docker_build_verified" if ok else "exact_zip_docker_build_failed",
            "package_zip": str(archive),
            "artifact_sha256": artifact_sha,
            "version": version_tag,
            "source_fingerprint": fingerprint,
            "compose_project": project,
            "image": image,
            "checks": checks,
            "build": build,
            "inspect": inspect,
            "cleanup": cleanup,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and inspect the Docker image from one exact final Promptbranch ZIP.")
    parser.add_argument("--package-zip", required=True)
    parser.add_argument("--keep-image", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = verify_exact_zip_docker_build(Path(args.package_zip), keep_image=bool(args.keep_image))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"status={payload.get('status')}")
        print(f"ok={str(bool(payload.get('ok'))).lower()}")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
