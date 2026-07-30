from __future__ import annotations

import json
from pathlib import Path

import promptbranch_impact_testing as impact

ROOT = Path(__file__).resolve().parents[1]


def test_checked_in_impact_map_is_strict_and_loadable() -> None:
    mapping = impact.load_impact_map(ROOT)
    assert mapping["schema"] == "promptbranch.test.impact_map"
    assert mapping["_sha256"]
    assert "impact_planner" in mapping["groups"]


def test_impact_plan_selects_direct_and_transitive_groups() -> None:
    result = impact.build_impact_plan(
        ROOT,
        base="v0.1.114.2",
        mode="component",
        explicit_changed_files=["promptbranch_operational_evidence.py"],
    )
    assert result["ok"] is True
    assert "operational_lifecycle" in result["selected_groups"]
    assert "application_architecture" in result["selected_groups"]
    assert "project_control_surface" in result["selected_groups"]
    assert "compile" in result["selected_groups"]
    assert result["full_release_validation_required"] is True
    assert result["strict_adoption_gate_unchanged"] is True
    assert "full_direct" in result["deferred_strict_release_steps"]


def test_impact_plan_fails_closed_for_unmapped_changed_file() -> None:
    result = impact.build_impact_plan(
        ROOT,
        mode="edit",
        explicit_changed_files=["unmapped.binary"],
    )
    assert result["ok"] is False
    assert result["status"] == "impact_plan_blocked"
    assert result["unmapped_changed_files"] == ["unmapped.binary"]


def test_impact_evidence_cache_is_exact_keyed(tmp_path: Path, monkeypatch) -> None:
    plan = {
        "ok": True,
        "repo_path": str(ROOT),
        "commands": [{"group": "probe", "argv": ["python3", "-c", "print('ok')"], "transport_independent": True}],
        "evidence_key": "a" * 64,
        "selected_groups": ["probe"],
        "changed_files": ["x.py"],
        "mode": "edit",
        "full_release_validation_required": True,
        "strict_adoption_gate_unchanged": True,
    }
    first = impact.execute_impact_plan(plan, evidence_dir=tmp_path)
    assert first["ok"] is True
    assert first["evidence_reused"] is False
    second = impact.execute_impact_plan(plan, evidence_dir=tmp_path)
    assert second["ok"] is True
    assert second["status"] == "reused_impact_evidence"
    assert second["evidence_reused"] is True


def test_map_rejects_unknown_group_reference(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".promptbranch").mkdir(parents=True)
    payload = json.loads((ROOT / ".promptbranch/test-impact-map.json").read_text())
    payload["rules"][0]["groups"] = ["missing"]
    (repo / ".promptbranch/test-impact-map.json").write_text(json.dumps(payload))
    try:
        impact.load_impact_map(repo)
    except impact.ImpactTestingError as exc:
        assert "unknown groups" in str(exc)
    else:
        raise AssertionError("invalid impact map was accepted")


def _minimal_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".promptbranch").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "VERSION").write_text("v0.1.115\n", encoding="utf-8")
    (repo / ".promptbranch/test-impact-map.json").write_bytes(
        (ROOT / ".promptbranch/test-impact-map.json").read_bytes()
    )
    (repo / "promptbranch_operational_evidence.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "tests/test_promptbranch_operational_evidence.py").write_text("def test_probe(): assert True\n", encoding="utf-8")
    (repo / "tests/test_release_adoption_verification.py").write_text("def test_probe2(): assert True\n", encoding="utf-8")
    (repo / "tests/test_promptbranch_application_architecture.py").write_text("def test_probe3(): assert True\n", encoding="utf-8")
    return repo


def test_evidence_key_changes_when_changed_file_content_changes(tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path)
    first = impact.build_impact_plan(repo, mode="edit", explicit_changed_files=["promptbranch_operational_evidence.py"])
    (repo / "promptbranch_operational_evidence.py").write_text("VALUE = 2\n", encoding="utf-8")
    second = impact.build_impact_plan(repo, mode="edit", explicit_changed_files=["promptbranch_operational_evidence.py"])
    assert first["evidence_key"] != second["evidence_key"]
    assert first["changed_file_fingerprints"] != second["changed_file_fingerprints"]


def test_evidence_key_changes_when_selected_test_definition_changes(tmp_path: Path) -> None:
    repo = _minimal_repo(tmp_path)
    first = impact.build_impact_plan(repo, mode="edit", explicit_changed_files=["promptbranch_operational_evidence.py"])
    test_file = repo / "tests/test_promptbranch_operational_evidence.py"
    test_file.write_text("def test_probe(): assert False\n", encoding="utf-8")
    second = impact.build_impact_plan(repo, mode="edit", explicit_changed_files=["promptbranch_operational_evidence.py"])
    assert first["evidence_key"] != second["evidence_key"]
    assert first["test_definition_fingerprints"] != second["test_definition_fingerprints"]


def test_impact_plan_records_runtime_and_dependency_identity() -> None:
    result = impact.build_impact_plan(
        ROOT,
        mode="edit",
        explicit_changed_files=["promptbranch_impact_testing.py"],
    )
    identity = result["runtime_identity"]
    assert identity["python_executable"]
    assert identity["python_prefix"]
    assert identity["python_version"]
    assert set(identity["dependencies"]) == {"pytest", "fastapi", "starlette"}
