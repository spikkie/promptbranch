from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OBSOLETE = "chatgpt_claudecode_workflow_" + "release_control.sh"


def test_obsolete_release_control_script_is_absent() -> None:
    assert not (ROOT / OBSOLETE).exists()


def test_artifact_guardian_no_longer_requires_obsolete_release_control() -> None:
    policy = (ROOT / ".artifact-guardian.yml").read_text(encoding="utf-8")
    assert OBSOLETE not in policy


def test_current_runtime_surfaces_do_not_route_to_obsolete_release_control() -> None:
    current_surfaces = [
        ROOT / "promptbranch_cli.py",
        ROOT / "promptbranch_release_state_machine.py",
        ROOT / "promptbranch_test_suite.py",
        ROOT / "install.sh",
        ROOT / "scripts" / "run-release-lifecycle-proof.py",
        ROOT / "scripts" / "pb-docker-live-profile-bootstrap.sh",
        ROOT / ".promptbranch" / "test-impact-map.json",
        ROOT / "docs" / "project" / "promptbranch-behavioral-surface-v0.1.109.1.json",
    ]
    for path in current_surfaces:
        assert path.is_file(), path
        assert OBSOLETE not in path.read_text(encoding="utf-8"), path


def test_install_is_thin_bootstrap_to_canonical_lifecycle() -> None:
    install = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "scripts/run-release-lifecycle-proof.py" in install
    assert "--artifact-conversation-url" in install
    assert "--profile" in install
    assert "full" in install
    assert OBSOLETE not in install


def test_candidate_full_profile_binds_exact_package_zip() -> None:
    cli = (ROOT / "promptbranch_cli.py").read_text(encoding="utf-8")
    assert "def _candidate_test_command_for_profile" in cli
    assert '"test", "full"' in cli
    assert '"--package-zip", str(artifact_path)' in cli
