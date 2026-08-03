#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from promptbranch_artifacts import ArtifactRegistry, canonical_artifact_filename, canonical_version_tag
from promptbranch_project import load_repo_identity, project_registry_dir


def emit(payload: dict, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"status={payload.get('status')}")
        print(f"ok={str(bool(payload.get('ok'))).lower()}")
        if payload.get("error"):
            print(f"error={payload.get('error')}", file=sys.stderr)
    return 0 if payload.get("ok") else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore the exact pre-rollout accepted/current artifact using release-set rollback environment evidence.")
    parser.add_argument("--repo", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    identity = load_repo_identity(repo)
    if identity is None:
        return emit({"ok": False, "status": "rollback_repo_identity_missing", "error": "repository is not joined"}, as_json=args.json)

    version = canonical_version_tag(os.environ.get("PROMPTBRANCH_ROLLBACK_VERSION"))
    artifact = Path(os.environ.get("PROMPTBRANCH_ROLLBACK_ARTIFACT", "")).name
    expected_sha = os.environ.get("PROMPTBRANCH_ROLLBACK_SHA256", "").strip().lower()
    source_ref = Path(os.environ.get("PROMPTBRANCH_ROLLBACK_SOURCE_REF", "")).name
    processed_file_id = os.environ.get("PROMPTBRANCH_ROLLBACK_PROCESSED_FILE_ID", "").strip()
    library_id = os.environ.get("PROMPTBRANCH_ROLLBACK_LIBRARY_METADATA_ID", "").strip()
    project_id = os.environ.get("PROMPTBRANCH_ROLLBACK_PROJECT_ID", "").strip()
    expected_artifact = canonical_artifact_filename(identity.repo_id, version) if version else None
    errors: list[str] = []
    if project_id != identity.project_id:
        errors.append("rollback project id does not match tracked identity")
    if not version or artifact != expected_artifact:
        errors.append("rollback version/artifact identity is not canonical")
    if len(expected_sha) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha):
        errors.append("rollback SHA-256 is invalid")
    if not source_ref or not processed_file_id.startswith("file_") or not library_id.startswith("libfile_"):
        errors.append("rollback Project Source identity is incomplete")
    if errors:
        return emit({"ok": False, "status": "rollback_identity_invalid", "errors": errors}, as_json=args.json)

    registry = ArtifactRegistry(project_registry_dir(identity.project_id))
    candidates = [
        item for item in registry.list()
        if item.get("repo_id") == identity.repo_id
        and canonical_version_tag(item.get("version")) == version
        and item.get("filename") == artifact
        and item.get("sha256") == expected_sha
    ]
    if len(candidates) != 1:
        return emit({"ok": False, "status": "rollback_registry_identity_not_unique", "match_count": len(candidates)}, as_json=args.json)
    local_path = Path(str(candidates[0].get("path") or "")).expanduser()
    if not local_path.is_file():
        fallback = repo / artifact
        local_path = fallback if fallback.is_file() else local_path
    if not local_path.is_file():
        return emit({"ok": False, "status": "rollback_local_artifact_missing", "local_path": str(local_path)}, as_json=args.json)

    evidence = {
        "ok": True,
        "requested_filename": artifact,
        "assigned_filename": source_ref,
        "processed_file_id": processed_file_id,
        "library_metadata_object_id": library_id,
        "project_url": identity.project_home_url,
        "local_sha256": expected_sha,
    }
    with tempfile.TemporaryDirectory(prefix="promptbranch-release-set-rollback-") as temporary:
        evidence_path = Path(temporary) / "source-evidence.json"
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        command = [
            sys.executable,
            "-m",
            "promptbranch.cli",
            "artifact",
            "adopt",
            artifact,
            "--from-project-source",
            "--local-path",
            str(local_path),
            "--source-evidence-json",
            str(evidence_path),
            "--repo",
            identity.repo_id,
            "--json",
        ]
        completed = subprocess.run(command, cwd=str(repo), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    try:
        nested = json.loads(completed.stdout) if completed.stdout.strip() else None
    except json.JSONDecodeError:
        nested = None
    ok = completed.returncode == 0 and isinstance(nested, dict) and nested.get("ok") is True
    return emit({
        "ok": ok,
        "status": "rollback_artifact_restored" if ok else "rollback_artifact_restore_failed",
        "repo_id": identity.repo_id,
        "version": version,
        "artifact": artifact,
        "sha256": expected_sha,
        "source_ref": source_ref,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": nested,
    }, as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
