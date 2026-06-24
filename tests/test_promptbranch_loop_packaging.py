from __future__ import annotations

from pathlib import Path


def test_promptbranch_loop_is_packaged_as_top_level_module() -> None:
    pyproject = Path("pyproject.toml").read_text()
    assert "promptbranch_loop" in pyproject


def test_promptbranch_loop_source_exists() -> None:
    assert Path("promptbranch_loop.py").is_file()
