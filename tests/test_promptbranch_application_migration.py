from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from promptbranch_application_architecture import validate_application_architecture
from promptbranch_application_migration import (
    ApplicationMigrationError,
    build_application_migration_report,
    build_application_template,
    differential_validate_application,
    write_application_template,
    write_migration_report,
)

ROOT = Path(__file__).resolve().parents[1]
METHOD_PRE = ROOT / "fixtures/pbai/promptbranch-method-pre-migration"
METHOD_PROOF = ROOT / "fixtures/pbai/promptbranch-method-domain-module"


def _copy_tree(source: Path, target: Path) -> None:
    import shutil

    shutil.copytree(source, target)


def test_domain_template_plan_is_complete_and_read_only() -> None:
    result = build_application_template(
        kind="domain_module",
        application_id="example-domain",
        runtime_provider="promptbranch",
    )
    assert result["ok"] is True
    assert result["status"] == "template_plan_ready"
    assert result["safety"] == {
        "plan_only": True,
        "state_mutated": False,
        "explicit_write_required": True,
    }
    files = result["files"]
    assert ".promptbranch-ai.json" in files
    assert ".promptbranch/ai-registry.json" in files
    assert "PROJECT_SETTINGS.md" in files
    assert "AGENTS.md" in files
    assert "PBAI-001" in files["PROJECT_SETTINGS.md"]
    declaration = json.loads(files[".promptbranch-ai.json"])
    assert declaration["application"]["kind"] == "domain_module"
    assert set(declaration["delegation"]["delegated_capabilities"])
    assert declaration["authority"]["self_grant_allowed"] is False


def test_tracked_template_snapshots_match_renderer() -> None:
    pairs = [
        ("runtime_application", "example-runtime", "example-runtime"),
        ("domain_module", "example-domain", "promptbranch"),
    ]
    for kind, application_id, runtime_provider in pairs:
        plan = build_application_template(
            kind=kind,
            application_id=application_id,
            runtime_provider=runtime_provider,
        )
        snapshot = ROOT / "templates/pbai" / kind
        expected = plan["files"]
        visible_files = {
            path.relative_to(snapshot).as_posix()
            for path in snapshot.rglob("*")
            if (
                path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix not in {".pyc", ".pyo"}
            )
        }
        actual = {
            relative_path: (snapshot / relative_path).read_text(encoding="utf-8")
            for relative_path in expected
        }
        assert visible_files == set(expected)
        assert actual == expected


def test_template_write_requires_explicit_nonconflicting_target(tmp_path: Path) -> None:
    target = tmp_path / "module"
    first = write_application_template(
        target,
        kind="domain_module",
        application_id="demo-module",
        runtime_provider="promptbranch",
    )
    assert first["ok"] is True
    assert first["status"] == "template_written"
    second = write_application_template(
        target,
        kind="domain_module",
        application_id="demo-module",
        runtime_provider="promptbranch",
    )
    assert second["ok"] is False
    assert second["status"] == "template_write_conflict"
    assert second["safety"]["state_mutated"] is False


def test_written_domain_template_validates_through_executable(tmp_path: Path) -> None:
    target = tmp_path / "module"
    result = write_application_template(
        target,
        kind="domain_module",
        application_id="demo-module",
        runtime_provider="promptbranch",
    )
    assert result["ok"] is True
    validation = validate_application_architecture(target, level="executable")
    assert validation["ok"] is True
    assert validation["proven_level"] == "executable"
    assert validation["status"] == "executable_validated"


def test_cross_repository_executable_launcher_uses_promptbranch_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "module"
    write_application_template(
        target,
        kind="domain_module",
        application_id="cross-repo-module",
        runtime_provider="promptbranch",
    )
    import promptbranch_application_architecture as architecture

    monkeypatch.setenv("PATH", "/definitely-not-a-promptbranch-path")
    result = architecture.validate_application_architecture(target, level="executable")
    assert result["ok"] is True
    assert result["executable"]["run"]["ok"] is True


def test_promptbranch_method_pre_migration_report_is_explicit_and_read_only(tmp_path: Path) -> None:
    target = tmp_path / "pre"
    _copy_tree(METHOD_PRE, target)
    before = sorted(path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file())
    report = build_application_migration_report(
        target,
        kind="domain_module",
        application_id="promptbranch-method",
        runtime_provider="promptbranch",
    )
    after = sorted(path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file())
    assert before == after
    assert report["status"] == "migration_required"
    assert report["declaration"] == {"path": ".promptbranch-ai.json", "exists": False}
    assert any(item["code"] == "declaration_missing" for item in report["gaps"])
    assert report["safety"] == {"read_only": True, "state_mutated": False, "silent_migration": False}
    assert "declaration_write" in report["not_performed"]


def test_checked_promptbranch_method_migration_report_matches_builder() -> None:
    expected = json.loads((ROOT / "fixtures/pbai/promptbranch-method-migration-report.json").read_text(encoding="utf-8"))
    actual = build_application_migration_report(
        METHOD_PRE,
        kind="domain_module",
        application_id="promptbranch-method",
        runtime_provider="promptbranch",
    )
    # Absolute repo paths differ between build/extraction environments; all policy content must match.
    for payload in (expected, actual):
        payload.pop("repo_path", None)
    assert expected == actual


def test_migration_report_output_writes_only_the_report(tmp_path: Path) -> None:
    report = build_application_migration_report(
        METHOD_PRE,
        kind="domain_module",
        application_id="promptbranch-method",
    )
    output = tmp_path / "reports/promptbranch-method.json"
    written = write_migration_report(report, output)
    assert written == output.resolve()
    assert json.loads(output.read_text(encoding="utf-8"))["schema"] == "promptbranch.ai.migration.report"


def test_promptbranch_method_domain_module_passes_all_nonoperational_levels() -> None:
    for level in ("declaration", "structural", "registry", "executable"):
        result = validate_application_architecture(METHOD_PROOF, level=level)
        assert result["ok"] is True, result
        assert result["proven_level"] == level


def test_promptbranch_method_domain_module_does_not_overclaim_operational() -> None:
    result = validate_application_architecture(METHOD_PROOF, level="operational")
    assert result["ok"] is False
    assert result["proven_level"] == "executable"
    assert result["status"] == "operational_evidence_required"


def test_promptbranch_method_differential_validation_is_equivalent_or_stronger() -> None:
    result = differential_validate_application(METHOD_PROOF)
    assert result["ok"] is True, result
    assert result["status"] == "equivalent_or_stronger"
    assert result["case_count"] == 6
    assert result["passed_case_count"] == 6
    assert result["weaker_cases"] == []
    assert {item["id"] for item in result["results"]} == {
        "clean",
        "missing-agents-policy",
        "empty-knowledge",
        "unknown-declaration-field",
        "self-grant-authority",
        "missing-proof-skill",
    }


def test_differential_validation_fails_closed_on_expected_outcome_drift(tmp_path: Path) -> None:
    target = tmp_path / "method"
    _copy_tree(METHOD_PROOF, target)
    config_path = target / ".promptbranch/ai-differential.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["cases"][1]["expect_promptbranch"] = "pass"
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = differential_validate_application(target)
    assert result["ok"] is False
    assert result["status"] == "differential_validation_failed"
    assert result["errors"]


def test_differential_config_rejects_shell_execution(tmp_path: Path) -> None:
    target = tmp_path / "method"
    _copy_tree(METHOD_PROOF, target)
    config_path = target / ".promptbranch/ai-differential.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["reference"]["argv"] = ["bash", "-lc", "true"]
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(ApplicationMigrationError, match="may not invoke a shell"):
        differential_validate_application(target)


def test_application_architecture_cli_template_migration_and_differential(tmp_path: Path) -> None:
    cli = [sys.executable, str(ROOT / "promptbranch_cli.py")]
    template = subprocess.run(
        cli
        + [
            "application",
            "architecture",
            "template",
            "--kind",
            "domain_module",
            "--application-id",
            "cli-domain",
            "--output-dir",
            str(tmp_path / "out"),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert template.returncode == 0, template.stderr
    assert json.loads(template.stdout)["status"] == "template_plan_ready"
    assert not (tmp_path / "out/.promptbranch-ai.json").exists()

    migration = subprocess.run(
        cli
        + [
            "application",
            "architecture",
            "migration-report",
            "--repo-path",
            str(METHOD_PRE),
            "--kind",
            "domain_module",
            "--application-id",
            "promptbranch-method",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert migration.returncode == 0, migration.stderr
    assert json.loads(migration.stdout)["status"] == "migration_required"

    differential = subprocess.run(
        cli
        + [
            "application",
            "architecture",
            "differential-validate",
            "--repo-path",
            str(METHOD_PROOF),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert differential.returncode == 0, differential.stderr
    assert json.loads(differential.stdout)["status"] == "equivalent_or_stronger"
