from __future__ import annotations

import os
import sys
from pathlib import Path


def launcher_python() -> str:
    """Return the exact interpreter path that launched Promptbranch.

    The launch path is execution authority. Do not resolve symlinks: a virtualenv
    launcher may point at a system binary while carrying distinct environment
    semantics through its path and prefix.
    """
    value = os.path.abspath(os.path.expanduser(str(sys.executable)))
    if not value:
        raise RuntimeError("python_authority_missing: sys.executable is empty")
    return value


def launcher_python_path() -> Path:
    path = Path(launcher_python())
    if not path.is_file():
        raise RuntimeError(f"python_authority_missing: {path}")
    return path
