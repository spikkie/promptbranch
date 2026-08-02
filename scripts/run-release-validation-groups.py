#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from promptbranch_test_suite import run_release_validation_groups


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the repository's required deterministic release-validation groups without live browser mutation."
    )
    parser.add_argument("--repo", default=".", help="Repository root. Defaults to the current directory.")
    parser.add_argument("--fail-fast", action="store_true", help="Skip later groups after the first required failure.")
    parser.add_argument("--json", action="store_true", help="Emit the complete result as JSON.")
    args = parser.parse_args()

    payload = run_release_validation_groups(
        repo_path=Path(args.repo).expanduser().resolve(),
        fail_fast=bool(args.fail_fast),
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"status={payload.get('status')}")
        print(f"ok={str(bool(payload.get('ok'))).lower()}")
        for name in payload.get("missing_required_groups") or []:
            print(f"failed_group={name}")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
