#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile repository Python sources without writing bytecode into the repository.")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        print(f"repository not found: {repo}", file=sys.stderr)
        return 2

    cache_root = Path(tempfile.mkdtemp(prefix="promptbranch-compileall-pycache-"))
    env = os.environ.copy()
    env["PYTHONPYCACHEPREFIX"] = str(cache_root)
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", "."],
            cwd=repo,
            env=env,
            check=False,
        )
        return int(completed.returncode)
    finally:
        shutil.rmtree(cache_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
