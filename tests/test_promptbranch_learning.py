from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import promptbranch_learning as learning
from promptbranch_mcp import skill_validate

ROOT = Path(__file__).resolve().parents[1]


def test_learning_and_operator_skills_are_tracked_read_only() -> None:
    learn = skill_validate("promptbranch-learning", repo_path=ROOT)
    operator = skill_validate("promptbranch-operator", repo_path=ROOT)
    assert learn["ok"] is True, learn
    assert operator["ok"] is True, operator
    assert learn["skill"]["risk"] == "read"
    assert operator["skill"]["risk"] == "read"
    assert learn["process_tools"] == []
    assert operator["process_tools"] == []


def test_learning_source_covers_all_audiences_and_core_domains() -> None:
    payload = learning.validate_learning_source(ROOT)
    assert payload["ok"] is True, payload
    assert payload["version"] == "v0.1.128.2.6"
    assert payload["audiences"] == sorted(learning.AUDIENCE_MATRIX)
    assert payload["coverage_domains"] == list(learning.COVERAGE_DOMAINS)
    assert payload["authority"] == learning.NO_AUTHORITY


def test_operator_source_is_read_only_and_registered() -> None:
    payload = learning.validate_operator_source(ROOT)
    assert payload["ok"] is True, payload
    assert payload["version"] == "v0.1.128.2.6"
    assert payload["authority"] == learning.NO_AUTHORITY


def test_learning_bundle_is_byte_deterministic_and_self_contained(tmp_path: Path) -> None:
    first = tmp_path / "learning-1.zip"
    second = tmp_path / "learning-2.zip"
    one = learning.export_learning_bundle("promptbranch-learning", ROOT, first)
    two = learning.export_learning_bundle("promptbranch-learning", ROOT, second)
    assert one["ok"] is True
    assert two["ok"] is True
    assert first.read_bytes() == second.read_bytes()
    assert hashlib.sha256(first.read_bytes()).hexdigest() == one["sha256"] == two["sha256"]
    manifest = one["verification"]["manifest"]
    assert manifest["audiences"] == learning.AUDIENCE_MATRIX
    assert manifest["coverage_domains"] == list(learning.COVERAGE_DOMAINS)
    assert manifest["authority"] == learning.NO_AUTHORITY
    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        for entrypoint in ("SKILL.md", "PROJECT_SOURCE.md", "AGENTS.md", "CLAUDE.md", "LEARNING_PATH.md", "EXERCISES.md"):
            assert f"promptbranch-learning/{entrypoint}" in names
        assert "promptbranch-learning/related-skills/promptbranch-operator/SKILL.md" in names
        assert "promptbranch-learning/related-skills/promptbranch-tool-authoring/SKILL.md" in names
        project_source = archive.read("promptbranch-learning/PROJECT_SOURCE.md").decode("utf-8")
        agents = archive.read("promptbranch-learning/AGENTS.md").decode("utf-8")
        claude = archive.read("promptbranch-learning/CLAUDE.md").decode("utf-8")
    assert "canonical self-contained learning source" in project_source
    assert "does not grant execution or mutation authority" in agents
    assert "separation between reasoning and deterministic authority" in claude


def test_operator_bundle_is_portable_deterministic_and_no_authority(tmp_path: Path) -> None:
    first = tmp_path / "operator-1.zip"
    second = tmp_path / "operator-2.zip"
    one = learning.export_learning_bundle("promptbranch-operator", ROOT, first)
    two = learning.export_learning_bundle("promptbranch-operator", ROOT, second)
    assert first.read_bytes() == second.read_bytes()
    assert one["verification"]["ok"] is True
    assert two["verification"]["ok"] is True
    assert one["authority"] == learning.NO_AUTHORITY
    with zipfile.ZipFile(first) as archive:
        assert "promptbranch-operator/OPERATOR_RUNBOOK.md" in archive.namelist()
        assert "promptbranch-operator/FAILURE_CLASSIFICATION.md" in archive.namelist()


def test_learning_bundle_verifier_rejects_tampering(tmp_path: Path) -> None:
    original = tmp_path / "source.zip"
    tampered = tmp_path / "tampered.zip"
    learning.export_learning_bundle("promptbranch-learning", ROOT, original)
    with zipfile.ZipFile(original, "r") as inp, zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_STORED) as out:
        for info in inp.infolist():
            body = inp.read(info.filename)
            if info.filename.endswith("AUTHORITY_MODEL.md"):
                body += b"\nmutation authority granted\n"
            out.writestr(info, body)
    payload = learning.verify_learning_bundle(tampered)
    assert payload["ok"] is False
    assert any(item.startswith("digest_mismatch:") for item in payload["errors"])


def test_learning_bundle_manifest_cannot_escalate_authority(tmp_path: Path) -> None:
    original = tmp_path / "source.zip"
    tampered = tmp_path / "tampered-manifest.zip"
    learning.export_learning_bundle("promptbranch-learning", ROOT, original)
    with zipfile.ZipFile(original, "r") as inp, zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_STORED) as out:
        for info in inp.infolist():
            body = inp.read(info.filename)
            if info.filename.endswith("manifest.json"):
                manifest = json.loads(body.decode("utf-8"))
                manifest["authority"]["mutation_authority_granted"] = True
                body = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
            out.writestr(info, body)
    payload = learning.verify_learning_bundle(tampered)
    assert payload["ok"] is False
    assert "manifest_authority_escalation" in payload["errors"]
