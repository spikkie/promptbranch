#!/usr/bin/env python3
"""Compatibility wrapper for installed accepted-event validation.

The implementation lives in ``promptbranch_orchestration`` so the installed
``pb orchestration validate-accepted-event`` command does not depend on a
repo-local ``scripts/`` file being present under site-packages.  This wrapper is
kept for source-tree operators and historical evidence references.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from promptbranch_orchestration import (  # noqa: F401 - re-exported for tests/operators.
    ACCEPTED_EVENT_SCHEMA_ID,
    ACCEPTED_EVENT_SCHEMA_VERSION,
    accepted_event_example_paths,
    display_path_for_root,
    read_json,
    render_accepted_event_validation_text,
    sha256_file,
    validate_accepted_event,
    validate_accepted_event_paths,
)


def display_path(path: Path) -> str:
    return display_path_for_root(path)


def example_paths() -> list[Path]:
    return accepted_event_example_paths()


def validate_paths(paths: list[Path]) -> list[str]:
    payload = validate_accepted_event_paths(paths)
    return list(payload.get("errors") or [])


def validate_paths_payload(paths: list[Path]) -> dict[str, Any]:
    return validate_accepted_event_paths(paths)


def render_text(payload: dict[str, Any]) -> str:
    return render_accepted_event_validation_text(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate read-only orchestration accepted-event fixtures.")
    parser.add_argument("paths", nargs="*", help="Optional accepted-event JSON files. Defaults to committed examples.")
    parser.add_argument("--json", action="store_true", help="Emit structured validation result as JSON.")
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.paths] if args.paths else example_paths()
    payload = validate_paths_payload(paths)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text(payload))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
