from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import venv

from promptbranch_python_authority import launcher_python, launcher_python_path


def test_launcher_python_preserves_symlink_path(monkeypatch, tmp_path: Path) -> None:
    target = Path(sys.executable)
    link = tmp_path / "venv" / "bin" / "python"
    link.parent.mkdir(parents=True)
    link.symlink_to(target)
    monkeypatch.setattr(sys, "executable", str(link))
    assert launcher_python() == str(link.absolute())
    assert launcher_python_path() == link.absolute()
    assert launcher_python() != str(link.resolve())


def test_virtualenv_launcher_keeps_environment_identity(tmp_path: Path) -> None:
    env_dir = tmp_path / "authority-venv"
    venv.EnvBuilder(with_pip=False, symlinks=True).create(env_dir)
    python = env_dir / "bin" / "python"
    repo = Path(__file__).resolve().parents[1]
    script = (
        "import json,sys; "
        "from promptbranch_python_authority import launcher_python; "
        "print(json.dumps({'launcher': launcher_python(), 'sys_executable': sys.executable, 'prefix': sys.prefix}))"
    )
    env = os.environ.copy(); env["PYTHONPATH"] = str(repo)
    result = subprocess.run([str(python), "-c", script], env=env, text=True, capture_output=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["launcher"] == str(python.absolute())
    assert payload["sys_executable"] == str(python.absolute())
    assert Path(payload["prefix"]) == env_dir.absolute()
