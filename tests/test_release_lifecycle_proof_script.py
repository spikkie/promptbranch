from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import textwrap
import zipfile


def test_release_lifecycle_proof_runs_and_independently_verifies_each_state(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run-release-lifecycle-proof.py"
    repo = tmp_path / "checkout-name-is-not-authority"
    repo.mkdir()
    repo_id = "authority-demo"
    (repo / ".promptbranch-repo.json").write_text(
        json.dumps({
            "schema": "promptbranch.repo.identity",
            "schema_version": "1.0",
            "project_id": "g-p-00000000000000000000000000000000-demo",
            "project_home_url": "https://chatgpt.com/g/g-p-00000000000000000000000000000000-demo/project",
            "repo_id": repo_id,
            "artifact_pattern": f"{repo_id}_<version>.zip",
            "role": "member",
        }) + "\n",
        encoding="utf-8",
    )
    artifact = tmp_path / f"{repo_id}_v1.2.3.zip"
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("VERSION", "v1.2.3\n")
        archive.writestr("README.md", "proof\n")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    profile = tmp_path / "profile"
    profile.mkdir()
    fake_cli = tmp_path / "fake_cli.py"
    fake_cli.write_text(textwrap.dedent(f'''\
        import hashlib, json, sys
        from pathlib import Path

        ORDER = ["DECLARED", "ARTIFACT_BOUND", "ARTIFACT_VERIFIED", "CANDIDATE_REGISTERED", "RUNTIME_PREPARED", "TESTED_GREEN", "ACCEPTED", "ADOPTED_CURRENT", "FINAL_VERIFIED"]
        TARGETS = {{"runtime-prepared": "RUNTIME_PREPARED", "tested-green": "TESTED_GREEN", "accepted": "ACCEPTED", "adopted-current": "ADOPTED_CURRENT", "final-verified": "FINAL_VERIFIED"}}
        argv = sys.argv[1:]
        profile = Path(argv[argv.index("--profile-dir") + 1])
        profile.mkdir(parents=True, exist_ok=True)
        state_path = profile / "fake-proof-state.json"
        calls_path = profile / "fake-proof-calls.jsonl"
        with calls_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(argv) + "\\n")
        state = json.loads(state_path.read_text()) if state_path.exists() else {{"current_state": "CANDIDATE_REGISTERED"}}
        if "release" in argv and "run" in argv:
            target = TARGETS[argv[argv.index("--until") + 1]]
            version = argv[argv.index("--version") + 1]
            artifact = Path(argv[argv.index("--artifact") + 1])
            state = {{"current_state": target, "version": version, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}}
            state_path.write_text(json.dumps(state))
            print(json.dumps({{"ok": True, "status": "target_state_reached", "current_state": target, "failure_state": None}}))
        elif "release" in argv and "verify" in argv:
            current = state["current_state"]
            rank = ORDER.index(current)
            states = [{{"state": name, "reached": i <= rank, "verified": i <= rank}} for i, name in enumerate(ORDER)]
            print(json.dumps({{"ok": True, "current_state": current, "failure_state": None, "states": states, "all_reached_states_verified": True, "failed_invariants": [], "mutation_performed": False, "lifecycle_complete": current == "FINAL_VERIFIED", "next_transition": None if current == "FINAL_VERIFIED" else "NEXT"}}))
        elif "artifact" in argv and "current" in argv:
            requested_repo = argv[argv.index("--repo") + 1]
            assert requested_repo == {repo_id!r}, (requested_repo, {repo_id!r})
            version = state["version"]
            sha = state["sha256"]
            filename = f"{repo_id}_{{version}}.zip"
            print(json.dumps({{"ok": True, "repos": {{{repo_id!r}: {{"ok": True, "state": {{"artifact_version": version, "source_version": version}}, "registry_current": {{"version": version, "sha256": sha, "kind": "adopted_release", "filename": filename, "path": str(profile / "objects" / sha / filename)}}, "consistency": {{"registry_current_matches_state_artifact": True, "state_source_matches_state_artifact": True}}, "fallback_used": False}}}}}}))
        else:
            raise SystemExit(3)
    '''), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable, str(script),
            "--cli", str(fake_cli),
            "--artifact", str(artifact),
            "--version", "v1.2.3",
            "--baseline-version", "v1.2.2",
            "--release-type", "repair",
            "--repo-path", str(repo),
            "--profile-dir", str(profile),
            "--artifact-conversation-url", "https://chatgpt.com/g/g-p-00000000000000000000000000000000-demo/c/00000000-0000-0000-0000-000000000000",
            "--skip-publication",
            "--json",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "final_verified_and_current"
    assert payload["repo_id"] == repo_id
    assert payload["sha256"] == digest
    assert [item["target"] for item in payload["steps"]] == [
        "RUNTIME_PREPARED", "TESTED_GREEN", "ACCEPTED", "ADOPTED_CURRENT", "FINAL_VERIFIED"
    ]
    assert payload["final_current"]["version"] == "v1.2.3"
    assert payload["final_current"]["sha256"] == digest
    calls = [json.loads(line) for line in (profile / "fake-proof-calls.jsonl").read_text().splitlines()]
    assert len(calls) == 11
    assert sum(1 for call in calls if "release" in call and "run" in call) == 5
    assert sum(1 for call in calls if "release" in call and "verify" in call) == 5
    assert calls[-1][calls[-1].index("--repo") + 1] == repo_id


def test_release_lifecycle_proof_resumes_blocked_retryable_and_keeps_json_stdout(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run-release-lifecycle-proof.py"
    repo = tmp_path / "repo"
    repo.mkdir()
    repo_id = "authority-demo"
    (repo / ".promptbranch-repo.json").write_text(json.dumps({
        "schema_version": 1,
        "project_id": "g-p-00000000000000000000000000000000-demo",
        "project_home_url": "https://chatgpt.com/g/g-p-00000000000000000000000000000000-demo/project",
        "repo_id": repo_id,
        "artifact_pattern": f"{repo_id}_<version>.zip",
        "role": "member",
    }) + "\n")
    artifact = tmp_path / f"{repo_id}_v1.2.3.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("VERSION", "v1.2.3\n")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    profile = tmp_path / "profile"
    attempt = profile / "release_attempts_v2" / repo_id / "v1.2.3" / digest[:16] / "attempt.json"
    attempt.parent.mkdir(parents=True)
    attempt.write_text(json.dumps({
        "state": "RUNTIME_PREPARED",
        "failure_state": "BLOCKED_RETRYABLE",
        "failure": {"code": "candidate_test_ask_timeout"},
        "release_eta": {"eta_seconds_approx": 10},
    }))
    fake_cli = tmp_path / "fake_cli.py"
    fake_cli.write_text(textwrap.dedent(f'''\
        import hashlib, json, sys
        from pathlib import Path
        ORDER = ["DECLARED", "ARTIFACT_BOUND", "ARTIFACT_VERIFIED", "CANDIDATE_REGISTERED", "RUNTIME_PREPARED", "TESTED_GREEN", "ACCEPTED", "ADOPTED_CURRENT", "FINAL_VERIFIED"]
        TARGETS = {{"runtime-prepared": "RUNTIME_PREPARED", "tested-green": "TESTED_GREEN", "accepted": "ACCEPTED", "adopted-current": "ADOPTED_CURRENT", "final-verified": "FINAL_VERIFIED"}}
        argv = sys.argv[1:]
        profile = Path(argv[argv.index("--profile-dir") + 1])
        calls = profile / "calls.jsonl"
        with calls.open("a", encoding="utf-8") as h: h.write(json.dumps(argv) + "\\n")
        attempt = profile / "release_attempts_v2" / {repo_id!r} / "v1.2.3" / {digest[:16]!r} / "attempt.json"
        state = json.loads(attempt.read_text())
        if "release" in argv and "run" in argv:
            target = TARGETS[argv[argv.index("--until") + 1]]
            state["state"] = target; state["failure_state"] = None; state["failure"] = None
            attempt.write_text(json.dumps(state))
            print(json.dumps({{"ok": True, "status": "target_state_reached", "current_state": target, "failure_state": None}}))
        elif "release" in argv and "verify" in argv:
            current = state["state"]; rank = ORDER.index(current)
            states = [{{"state": name, "reached": i <= rank, "verified": i <= rank}} for i, name in enumerate(ORDER)]
            print(json.dumps({{"ok": True, "current_state": current, "failure_state": None, "states": states, "all_reached_states_verified": True, "failed_invariants": [], "mutation_performed": False}}))
        elif "artifact" in argv and "current" in argv:
            filename = f"{repo_id}_v1.2.3.zip"
            print(json.dumps({{"ok": True, "repos": {{{repo_id!r}: {{"ok": True, "state": {{"artifact_version": "v1.2.3", "source_version": "v1.2.3"}}, "registry_current": {{"version": "v1.2.3", "sha256": {digest!r}, "kind": "adopted_release", "filename": filename, "path": str(profile / "objects" / {digest!r} / filename)}}, "consistency": {{"registry_current_matches_state_artifact": True, "state_source_matches_state_artifact": True}}, "fallback_used": False}}}}}}))
        else:
            raise SystemExit(3)
    '''))
    result = subprocess.run([
        sys.executable, str(script), "--cli", str(fake_cli), "--artifact", str(artifact),
        "--version", "v1.2.3", "--baseline-version", "v1.2.2", "--repo-path", str(repo),
        "--profile-dir", str(profile), "--artifact-conversation-url",
        "https://chatgpt.com/g/g-p-00000000000000000000000000000000-demo/c/00000000-0000-0000-0000-000000000000",
        "--skip-publication", "--json",
    ], cwd=root, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "final_verified_and_current"
    assert "resuming retryable attempt from RUNTIME_PREPARED" in result.stderr
    calls = [json.loads(line) for line in (profile / "calls.jsonl").read_text().splitlines()]
    first_run = next(call for call in calls if "release" in call and "run" in call)
    assert first_run[first_run.index("--until") + 1] == "tested-green"
    runtime_step = next(item for item in payload["steps"] if item["target"] == "RUNTIME_PREPARED")
    assert runtime_step["run_status"] == "already_reached_retry_resume"
    assert runtime_step["all_reached_states_verified"] is True


def _load_release_lifecycle_proof_module():
    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts" / "run-release-lifecycle-proof.py"
    spec = importlib.util.spec_from_file_location("run_release_lifecycle_proof", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)


def test_publish_control_projection_commits_pushes_and_verifies_upstream(tmp_path: Path) -> None:
    module = _load_release_lifecycle_proof_module()
    remote = tmp_path / "remote.git"
    assert _git("init", "--bare", str(remote), cwd=tmp_path).returncode == 0
    repo = tmp_path / "repo"
    clone = _git("clone", str(remote), str(repo), cwd=tmp_path)
    assert clone.returncode == 0, clone.stderr
    assert _git("config", "user.email", "promptbranch-test@example.invalid", cwd=repo).returncode == 0
    assert _git("config", "user.name", "Promptbranch Test", cwd=repo).returncode == 0

    for rel in module.CONTROL_PROJECTION_PATHS:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"baseline {rel}\n", encoding="utf-8")
    assert _git("add", "--", *module.CONTROL_PROJECTION_PATHS, cwd=repo).returncode == 0
    commit = _git("commit", "-m", "baseline", cwd=repo)
    assert commit.returncode == 0, commit.stderr
    push = _git("push", "-u", "origin", "HEAD", cwd=repo)
    assert push.returncode == 0, push.stderr

    changed = repo / module.CONTROL_PROJECTION_PATHS[0]
    changed.write_text("accepted current v1.2.3\n", encoding="utf-8")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    payload = module.publish_control_projection(
        repo=repo,
        version="v1.2.3",
        evidence_dir=evidence,
        skip_publication=False,
    )
    assert payload["ok"] is True
    assert payload["status"] == "committed_pushed_and_converged"
    assert payload["commit"] is True
    assert payload["push"] is True
    assert payload["upstream_matches_head"] is True
    assert payload["head"] == payload["upstream"]
    assert _git("status", "--porcelain", cwd=repo).stdout == ""


def test_publish_control_projection_fails_closed_on_unexpected_dirty_path(tmp_path: Path) -> None:
    module = _load_release_lifecycle_proof_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git("init", cwd=repo).returncode == 0
    assert _git("config", "user.email", "promptbranch-test@example.invalid", cwd=repo).returncode == 0
    assert _git("config", "user.name", "Promptbranch Test", cwd=repo).returncode == 0
    baseline = repo / "README.md"
    baseline.write_text("baseline\n", encoding="utf-8")
    assert _git("add", "README.md", cwd=repo).returncode == 0
    commit = _git("commit", "-m", "baseline", cwd=repo)
    assert commit.returncode == 0, commit.stderr

    allowed = repo / module.CONTROL_PROJECTION_PATHS[0]
    allowed.parent.mkdir(parents=True, exist_ok=True)
    allowed.write_text("projected\n", encoding="utf-8")
    unexpected = repo / "UNEXPECTED.txt"
    unexpected.write_text("must block\n", encoding="utf-8")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    payload = module.publish_control_projection(
        repo=repo,
        version="v1.2.3",
        evidence_dir=evidence,
        skip_publication=False,
    )
    assert payload["ok"] is False
    assert payload["status"] == "unexpected_post_adoption_worktree_changes"
    assert "UNEXPECTED.txt" in payload["unexpected_paths"]
