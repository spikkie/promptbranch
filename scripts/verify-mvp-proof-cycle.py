#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from promptbranch_mvp_proof import evaluate_mvp_proof_cycle_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify one Promptbranch canonical MVP proof cycle from explicit evidence files.")
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--baseline-version", required=True)
    parser.add_argument("--next-version", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--artifact-intake", required=True)
    parser.add_argument("--all-tests-summary", required=True)
    parser.add_argument("--visual-artifact", required=True)
    parser.add_argument("--adoption-result", required=True)
    parser.add_argument("--current-result", required=True)
    parser.add_argument("--continuation-ask", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = evaluate_mvp_proof_cycle_files(
        cycle=args.cycle,
        version=args.version,
        baseline_version=args.baseline_version,
        next_version=args.next_version,
        artifact_name=args.artifact,
        artifact_intake_path=args.artifact_intake,
        all_tests_path=args.all_tests_summary,
        visual_artifact_path=args.visual_artifact,
        adoption_path=args.adoption_result,
        current_path=args.current_result,
        continuation_ask_path=args.continuation_ask,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"status: {result['status']}")
        print(f"proof_sha256: {result['proof_sha256']}")
        if result["failed_checks"]:
            print("failed_checks:")
            for check in result["failed_checks"]:
                print(f"  - {check}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
