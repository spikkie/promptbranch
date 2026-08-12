#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
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


def progress(message: str) -> None:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%H:%M:%S")
    print(f"[{stamp}] {message}", file=sys.stderr, flush=True)


def _read_json_if_present(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _progress_snapshot(attempt_path: Path) -> str | None:
    attempt = _read_json_if_present(attempt_path)
    if not attempt:
        return None
    state = str(attempt.get("state") or "unknown")
    timing = attempt.get("publication_timing") if isinstance(attempt.get("publication_timing"), dict) else {}
    subphase = str(timing.get("active_subphase") or "").strip()
    eta = attempt.get("release_eta") if isinstance(attempt.get("release_eta"), dict) else {}
    eta_seconds = eta.get("eta_seconds_approx")
    eta_text = f" eta≈{int(float(eta_seconds))}s" if isinstance(eta_seconds, (int, float)) else ""
    subphase_text = f" subphase={subphase}" if subphase else ""
    return f"state={state}{subphase_text}{eta_text}"


def run_json(
    command: list[str],
    *,
    cwd: Path,
    evidence_dir: Path,
    label: str,
    attempt_path: Path | None = None,
    poll_seconds: float = 0.5,
) -> dict[str, Any]:
    stdout_path = evidence_dir / f"{label}.stdout.json"
    stderr_path = evidence_dir / f"{label}.stderr.txt"
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            text=True,
            stdout=stdout_handle,
            stderr=stderr_handle,
        )
        last_snapshot: str | None = None
        while process.poll() is None:
            if attempt_path is not None:
                snapshot = _progress_snapshot(attempt_path)
                if snapshot and snapshot != last_snapshot:
                    progress(f"{label}: {snapshot}")
                    last_snapshot = snapshot
            time.sleep(max(0.2, poll_seconds))
        returncode = int(process.returncode or 0)
    stdout = stdout_path.read_text(encoding="utf-8")
    stderr = stderr_path.read_text(encoding="utf-8")
    payload = parse_json(stdout, label=label)
    payload["_wrapper_returncode"] = returncode
    if returncode != 0 or payload.get("ok") is not True:
        failure = payload.get("failure") if isinstance(payload.get("failure"), dict) else {}
        code = str(failure.get("code") or payload.get("failure_code") or payload.get("status") or "unknown")
        progress(f"{label}: FAILED code={code} returncode={returncode}; evidence={evidence_dir}")
        raise RuntimeError(f"{label} failed: {code}; see {evidence_dir}")
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


def existing_attempt_path(profile_dir: Path, repo_id: str, version: str, digest: str) -> Path:
    return profile_dir / "release_attempts_v2" / repo_id / version / digest[:16] / "attempt.json"


def resume_start_rank(attempt_path: Path) -> tuple[int, str | None]:
    attempt = _read_json_if_present(attempt_path)
    if not attempt:
        return -1, None
    state = str(attempt.get("state") or "")
    failure_state = str(attempt.get("failure_state") or "").strip() or None
    if failure_state == "FAILED_TERMINAL":
        failure = attempt.get("failure") if isinstance(attempt.get("failure"), dict) else {}
        raise RuntimeError(f"existing release attempt is FAILED_TERMINAL: {failure.get('code') or 'unknown'}")
    return state_rank(state), failure_state



ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from promptbranch_project_control import CONTROL_PROJECTION_PATHS


def _run_text(command: list[str], *, cwd: Path, evidence_dir: Path, label: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    (evidence_dir / f"{label}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (evidence_dir / f"{label}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    return completed


def publish_control_projection(
    *,
    repo: Path,
    version: str,
    evidence_dir: Path,
    skip_publication: bool,
) -> dict[str, Any]:
    if skip_publication:
        return {"ok": True, "status": "skipped", "commit": False, "push": False}
    if not (repo / ".git").exists():
        return {"ok": True, "status": "not_applicable_no_git_checkout", "commit": False, "push": False}
    status = _run_text(["git", "status", "--porcelain"], cwd=repo, evidence_dir=evidence_dir, label="control-projection.git-status")
    if status.returncode != 0:
        return {"ok": False, "status": "git_status_failed", "returncode": status.returncode}
    dirty: list[str] = []
    for raw in status.stdout.splitlines():
        if len(raw) < 4:
            continue
        path = raw[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        dirty.append(path)
    unexpected = sorted(path for path in dirty if path not in CONTROL_PROJECTION_PATHS)
    if unexpected:
        return {
            "ok": False,
            "status": "unexpected_post_adoption_worktree_changes",
            "dirty_paths": dirty,
            "unexpected_paths": unexpected,
        }
    if not dirty:
        return {"ok": True, "status": "already_clean", "commit": False, "push": False, "dirty_paths": []}
    add = _run_text(["git", "add", "--", *CONTROL_PROJECTION_PATHS], cwd=repo, evidence_dir=evidence_dir, label="control-projection.git-add")
    if add.returncode != 0:
        return {"ok": False, "status": "git_add_failed", "returncode": add.returncode, "dirty_paths": dirty}
    commit = _run_text(
        ["git", "commit", "-m", f"chore(promptbranch): project accepted current {version}"],
        cwd=repo, evidence_dir=evidence_dir, label="control-projection.git-commit",
    )
    if commit.returncode != 0:
        return {"ok": False, "status": "git_commit_failed", "returncode": commit.returncode, "dirty_paths": dirty}
    push = _run_text(["git", "push"], cwd=repo, evidence_dir=evidence_dir, label="control-projection.git-push")
    if push.returncode != 0:
        return {"ok": False, "status": "git_push_failed", "returncode": push.returncode, "dirty_paths": dirty}
    head = _run_text(["git", "rev-parse", "HEAD"], cwd=repo, evidence_dir=evidence_dir, label="control-projection.git-head")
    upstream = _run_text(["git", "rev-parse", "@{u}"], cwd=repo, evidence_dir=evidence_dir, label="control-projection.git-upstream")
    head_sha = head.stdout.strip() if head.returncode == 0 else None
    upstream_sha = upstream.stdout.strip() if upstream.returncode == 0 else None
    converged = bool(head_sha and upstream_sha and head_sha == upstream_sha)
    return {
        "ok": converged,
        "status": "committed_pushed_and_converged" if converged else "git_upstream_not_converged",
        "commit": True,
        "push": True,
        "dirty_paths": dirty,
        "head": head_sha,
        "upstream": upstream_sha,
        "upstream_matches_head": converged,
    }

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
    attempt_path = existing_attempt_path(profile_dir, repo_id, str(args.version), digest)
    progress(f"lifecycle proof started version={args.version} baseline={args.baseline_version}")
    progress(f"artifact_sha={digest} repo_id={repo_id} python={sys.executable}")
    progress(f"evidence_dir={evidence_dir}")

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
    initial_rank, initial_failure_state = resume_start_rank(attempt_path)
    deferred_targets: list[str] = []
    if initial_failure_state == "BLOCKED_RETRYABLE":
        current_name = STATE_ORDER[initial_rank] if 0 <= initial_rank < len(STATE_ORDER) else "unknown"
        progress(f"resuming retryable attempt from {current_name}; prior failure marker will be cleared only by the next successful transition")

    for target_cli, target_state, publication_phase in TARGETS:
        if initial_failure_state == "BLOCKED_RETRYABLE" and state_rank(target_state) <= initial_rank:
            progress(f"{target_state}: already reached; verification deferred until retry succeeds")
            deferred_targets.append(target_state)
            steps.append({
                "target": target_state,
                "run_status": "already_reached_retry_resume",
                "current_state": STATE_ORDER[initial_rank] if initial_rank >= 0 else None,
                "all_reached_states_verified": None,
                "failed_invariants": [],
                "verification_deferred": True,
            })
            continue

        progress(f"target {target_state}: transition/resume started")
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
        run_payload = run_json(run_cmd, cwd=repo, evidence_dir=evidence_dir, label=f"{target_cli}.run", attempt_path=attempt_path)
        require_run(run_payload, target_state, label=f"{target_cli}.run")
        progress(f"{target_state}: reached; independent verification started")

        verify_cmd = base + [
            "release", "verify",
            *common,
            "--all-states",
            "--json",
        ]
        verify_payload = run_json(verify_cmd, cwd=repo, evidence_dir=evidence_dir, label=f"{target_cli}.verify", attempt_path=attempt_path)
        require_verify(verify_payload, target_state, label=f"{target_cli}.verify")
        progress(f"{target_state}: verified ✓")
        if deferred_targets:
            for item in steps:
                if item.get("target") in deferred_targets:
                    item["all_reached_states_verified"] = True
                    item["current_state"] = verify_payload.get("current_state")
                    item["verification_deferred"] = False
            deferred_targets.clear()
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
    progress("final artifact current proof started")
    current_payload = run_json(current_cmd, cwd=repo, evidence_dir=evidence_dir, label="artifact-current.final", attempt_path=attempt_path)
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

    progress("publishing tracked post-adoption control projection")
    control_publication = publish_control_projection(
        repo=repo,
        version=str(args.version),
        evidence_dir=evidence_dir,
        skip_publication=bool(args.skip_publication),
    )
    if control_publication.get("ok") is not True:
        raise RuntimeError(f"post-adoption control projection publication failed: {control_publication.get('status')}; see {evidence_dir}")

    control_validation: dict[str, Any] | None = None
    if (repo / "docs" / "project" / "plan-state.json").is_file():
        progress("verifying tracked control projection against authoritative current")
        control_cmd = base + ["project", "validate-control-surface", "--repo-path", str(repo), "--json"]
        control_validation = run_json(
            control_cmd, cwd=repo, evidence_dir=evidence_dir, label="control-projection.final-validate", attempt_path=attempt_path
        )
        if str(control_validation.get("accepted_current_version") or "") != str(args.version):
            raise RuntimeError("tracked control projection accepted/current version does not match release version")
        if control_validation.get("control_projection_matches_authoritative_current") is not True:
            raise RuntimeError("tracked control projection does not match authoritative project current")
        progress("tracked control projection verified ✓")

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
        "control_projection_publication": control_publication,
        "control_projection_validation": control_validation,
        "evidence_dir": str(evidence_dir),
    }
    (evidence_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    progress("FINAL_VERIFIED and artifact current verified ✓")
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
