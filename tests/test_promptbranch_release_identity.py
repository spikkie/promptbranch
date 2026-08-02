from __future__ import annotations

from promptbranch_release_identity import evaluate_current_release_identity


def _payload(sha: str):
    return {
        "ok": True,
        "repos": {
            "demo": {
                "ok": True,
                "state": {"artifact_ref": "demo_v1.2.3.zip", "artifact_version": "v1.2.3", "source_ref": "demo_v1.2.3(1).zip", "source_version": "v1.2.3"},
                "registry_current": {"filename": "demo_v1.2.3.zip", "version": "v1.2.3", "sha256": sha},
                "consistency": {"registry_current_matches_state_artifact": True, "state_source_matches_state_artifact": True},
            }
        },
    }


def test_same_version_same_hash_is_idempotent():
    result = evaluate_current_release_identity(_payload("a" * 64), repo_id="demo", version="v1.2.3", artifact_filename="demo_v1.2.3.zip", artifact_sha256="a" * 64)
    assert result["ok"] is True
    assert result["status"] == "release_identity_already_current"
    assert result["already_current"] is True


def test_same_version_different_hash_fails_closed():
    result = evaluate_current_release_identity(_payload("a" * 64), repo_id="demo", version="v1.2.3", artifact_filename="demo_v1.2.3.zip", artifact_sha256="b" * 64)
    assert result["ok"] is False
    assert result["status"] == "immutable_release_identity_conflict"
    assert result["conflict"] is True


def test_same_version_missing_hash_fails_closed():
    result = evaluate_current_release_identity(_payload(""), repo_id="demo", version="v1.2.3", artifact_filename="demo_v1.2.3.zip", artifact_sha256="b" * 64)
    assert result["ok"] is False
    assert result["status"] == "immutable_release_identity_hash_missing"


def test_unavailable_current_state_fails_closed():
    result = evaluate_current_release_identity(None, repo_id="demo", version="v1.2.4", artifact_filename="demo_v1.2.4.zip", artifact_sha256="c" * 64)
    assert result["ok"] is False
    assert result["status"] == "release_identity_current_unavailable"
    assert result["conflict"] is True


def test_known_empty_current_state_allows_new_version_identity():
    result = evaluate_current_release_identity({"ok": True, "repos": {}}, repo_id="demo", version="v1.2.4", artifact_filename="demo_v1.2.4.zip", artifact_sha256="c" * 64)
    assert result["ok"] is True
    assert result["status"] == "new_release_identity"
