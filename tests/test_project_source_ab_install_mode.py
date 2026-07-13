from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_diagnostic_install_mode_skips_release_mutation_and_adoption() -> None:
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "--diagnostic-project-source-ab" in text
    diagnostic = text.split("if [[ ${diagnostic_project_source_ab} -eq 1 ]]; then", 1)[1].split("fi", 1)[0]
    assert "--skip-commit" in diagnostic
    assert "--skip-source-add" in diagnostic
    assert "--skip-tests" in diagnostic
    assert "--adopt-after-validation" not in diagnostic
    assert "pb-project-source-ab-diagnostic.sh" in diagnostic


def test_normal_install_gate_remains_strict_all_all() -> None:
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "--run-all-tests" in text
    assert "--run-external-live-tests" in text
    assert "--require-chatgpt-live-validation" in text
    assert "--adopt-after-validation" in text


def test_library_backing_diagnostic_install_mode_skips_release_mutation_and_adoption() -> None:
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "--diagnostic-library-backing-reupload" in text
    diagnostic = text.split("if [[ ${diagnostic_library_backing_reupload} -eq 1 ]]; then", 1)[1].split("fi", 1)[0]
    assert "--skip-commit" in diagnostic
    assert "--skip-source-add" in diagnostic
    assert "--skip-tests" in diagnostic
    assert "--adopt-after-validation" not in diagnostic
    assert "pb-library-backing-reupload-diagnostic.sh" in diagnostic
