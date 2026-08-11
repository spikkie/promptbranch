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
