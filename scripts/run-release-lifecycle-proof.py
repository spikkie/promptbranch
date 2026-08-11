#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

STATE_ORDER = [
    "DECLARED",
    "ARTIFACT_BOUND",
    "ARTIFACT_VERIFIED",
    "CANDIDATE_REGISTERED",
    "RUNTIME_PREPARED",
    "TESTED_GREEN",
    "ACCEPTED",
    "ADOPTED_CURRENT",
    "FINAL_VERIFIED",
]
TARGETS = [
    ("runtime-prepared", "RUNTIME_PREPARED", True),
    ("tested-green", "TESTED_GREEN", True),
    ("accepted", "ACCEPTED", False),
    ("adopted-current", "ADOPTED_CURRENT", False),
    ("final-verified", "FINAL_VERIFIED", False),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()




def authoritative_repo_id(repo: Path) -> str:
    identity_path = repo / ".promptbranch-repo.json"
    if not identity_path.is_file():
        raise RuntimeError(f"tracked repository identity not found: {identity_path}")
    try:
        payload = json.loads(identity_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"tracked repository identity is unreadable: {identity_path}: {exc}") from exc
    repo_id = str(payload.get("repo_id") or "").strip() if isinstance(payload, dict) else ""
    if not repo_id:
        raise RuntimeError(f"tracked repository identity has no repo_id: {identity_path}")
    return repo_id

def parse_json(stdout: str, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} did not emit one JSON object: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} JSON result is not an object")
    return value


def run_json(command: list[str], *, cwd: Path, evidence_dir: Path, label: str) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    (evidence_dir / f"{label}.stdout.json").write_text(completed.stdout, encoding="utf-8")
    (evidence_dir / f"{label}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}; see {evidence_dir}")
    payload = parse_json(completed.stdout, label=label)
    if payload.get("ok") is not True:
        raise RuntimeError(f"{label} returned ok!=true; see {evidence_dir}")
    return payload


def state_rank(value: str | None) -> int:
    try:
        return STATE_ORDER.index(str(value or ""))
    except ValueError:
        return -1


def require_run(payload: dict[str, Any], target_state: str, *, label: str) -> None:
    current = str(payload.get("current_state") or "")
    if state_rank(current) < state_rank(target_state):
        raise RuntimeError(f"{label} stopped at {current!r}, before required {target_state}")
    if payload.get("failure_state") not in (None, ""):
        raise RuntimeError(f"{label} has failure_state={payload.get('failure_state')!r}")


def require_verify(payload: dict[str, Any], target_state: str, *, label: str) -> None:
    current = str(payload.get("current_state") or "")
    if state_rank(current) < state_rank(target_state):
        raise RuntimeError(f"{label} verifies only {current!r}, before required {target_state}")
    if payload.get("failure_state") not in (None, ""):
        raise RuntimeError(f"{label} has failure_state={payload.get('failure_state')!r}")
    if payload.get("all_reached_states_verified") is not True:
        raise RuntimeError(f"{label} did not verify all reached states")
    if payload.get("failed_invariants") not in ([], None):
        raise RuntimeError(f"{label} reports failed invariants: {payload.get('failed_invariants')!r}")
    if payload.get("mutation_performed") is not False:
        raise RuntimeError(f"{label} verifier mutated state")
    states = payload.get("states") if isinstance(payload.get("states"), list) else []
    reached_target = next((item for item in states if isinstance(item, dict) and item.get("state") == target_state), None)
    if not reached_target or reached_target.get("reached") is not True or reached_target.get("verified") is not True:
        raise RuntimeError(f"{label} did not independently verify {target_state}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run and independently verify the canonical Promptbranch release lifecycle with one launcher Python.")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--baseline-version", required=True)
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--profile-dir", required=True)
    parser.add_argument("--artifact-conversation-url", required=True)
    parser.add_argument("--release-type", default="repair")
    parser.add_argument("--profile", default="full")
    parser.add_argument("--test-timeout", type=float, default=3600.0)
    parser.add_argument("--cli", help="Candidate promptbranch_cli.py. Defaults to the file beside this script's parent directory.")
    parser.add_argument("--evidence-dir")
    parser.add_argument("--skip-publication", action="store_true", help="Do not request Git commit/push/Project Source publication during TESTED_GREEN.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo_path).expanduser().resolve()
    artifact = Path(args.artifact).expanduser().resolve()
    profile_dir = Path(args.profile_dir).expanduser().resolve()
    cli = Path(args.cli).expanduser().resolve() if args.cli else Path(__file__).resolve().parents[1] / "promptbranch_cli.py"
    if not artifact.is_file():
        raise SystemExit(f"artifact not found: {artifact}")
    if not cli.is_file():
        raise SystemExit(f"candidate CLI not found: {cli}")
    digest = sha256_file(artifact)
    repo_id = authoritative_repo_id(repo)
    evidence_dir = Path(args.evidence_dir).expanduser().resolve() if args.evidence_dir else profile_dir / "release_lifecycle_proofs" / str(args.version) / digest[:16]
    evidence_dir.mkdir(parents=True, exist_ok=True)

    base = [
        sys.executable,
        str(cli),
        "--profile-dir", str(profile_dir),
    ]
    common = [
        "--artifact", str(artifact),
        "--version", str(args.version),
        "--baseline-version", str(args.baseline_version),
        "--repo-path", str(repo),
        "--profile", str(args.profile),
        "--test-timeout", str(args.test_timeout),
        "--artifact-conversation-url", str(args.artifact_conversation_url),
    ]

    steps: list[dict[str, Any]] = []
    for target_cli, target_state, publication_phase in TARGETS:
        run_cmd = base + [
            "release", "run",
            *common,
            "--release-type", str(args.release_type),
            "--until", target_cli,
            "--adopt",
        ]
        if publication_phase and not args.skip_publication:
            run_cmd += ["--commit", "--push", "--upload-project-source"]
        run_cmd.append("--json")
        run_payload = run_json(run_cmd, cwd=repo, evidence_dir=evidence_dir, label=f"{target_cli}.run")
        require_run(run_payload, target_state, label=f"{target_cli}.run")

        verify_cmd = base + [
            "release", "verify",
            *common,
            "--all-states",
            "--json",
        ]
        verify_payload = run_json(verify_cmd, cwd=repo, evidence_dir=evidence_dir, label=f"{target_cli}.verify")
        require_verify(verify_payload, target_state, label=f"{target_cli}.verify")
        steps.append({
            "target": target_state,
            "run_status": run_payload.get("status"),
            "current_state": verify_payload.get("current_state"),
            "all_reached_states_verified": verify_payload.get("all_reached_states_verified"),
            "failed_invariants": verify_payload.get("failed_invariants"),
        })

    current_cmd = base + [
        "artifact", "current",
        "--repo", repo_id,
        "--json",
    ]
    current_payload = run_json(current_cmd, cwd=repo, evidence_dir=evidence_dir, label="artifact-current.final")
    repos = current_payload.get("repos") if isinstance(current_payload.get("repos"), dict) else {}
    current_repo = repos.get(repo_id) if isinstance(repos.get(repo_id), dict) else current_payload
    registry_current = current_repo.get("registry_current") if isinstance(current_repo, dict) and isinstance(current_repo.get("registry_current"), dict) else {}
    state = current_repo.get("state") if isinstance(current_repo, dict) and isinstance(current_repo.get("state"), dict) else {}
    consistency = current_repo.get("consistency") if isinstance(current_repo, dict) and isinstance(current_repo.get("consistency"), dict) else {}
    if str(registry_current.get("version") or "") != str(args.version):
        raise RuntimeError("final artifact current version does not match release version")
    if str(registry_current.get("sha256") or "") != digest:
        raise RuntimeError("final artifact current SHA does not match the immutable input artifact")
    if registry_current.get("kind") != "adopted_release":
        raise RuntimeError("final artifact current kind is not adopted_release")
    if str(state.get("artifact_version") or "") != str(args.version) or str(state.get("source_version") or "") != str(args.version):
        raise RuntimeError("final state projection does not match release version")
    if current_repo.get("fallback_used") is not False:
        raise RuntimeError("final artifact current used fallback authority")
    if consistency.get("registry_current_matches_state_artifact") is not True or consistency.get("state_source_matches_state_artifact") is not True:
        raise RuntimeError("final artifact current state/registry projections do not converge")

    summary = {
        "ok": True,
        "action": "canonical_release_lifecycle_proof",
        "status": "final_verified_and_current",
        "python": sys.executable,
        "cli": str(cli),
        "repo_path": str(repo),
        "repo_id": repo_id,
        "artifact": str(artifact),
        "version": str(args.version),
        "baseline_version": str(args.baseline_version),
        "sha256": digest,
        "steps": steps,
        "final_current": {
            "version": registry_current.get("version"),
            "sha256": registry_current.get("sha256"),
            "kind": registry_current.get("kind"),
            "path": registry_current.get("path"),
            "fallback_used": current_repo.get("fallback_used"),
        },
        "evidence_dir": str(evidence_dir),
    }
    (evidence_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print("status=final_verified_and_current")
        print(f"version={args.version}")
        print(f"sha256={digest}")
        print(f"evidence_dir={evidence_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
