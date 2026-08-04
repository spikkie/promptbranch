#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from promptbranch_mvp_proof import (
    DEFAULT_REPO_ID,
    evaluate_mvp_proof_cycle_files,
    evaluate_mvp_proof_preflight_files,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify one Promptbranch canonical MVP proof cycle from explicit evidence files.")
    parser.add_argument("--cycle", type=int, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--baseline-version", required=True)
    parser.add_argument("--next-version", required=True)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--artifact-sha256", required=True)
    parser.add_argument("--artifact-intake", required=True)
    parser.add_argument("--all-tests-summary", required=True)
    parser.add_argument("--visual-artifact", required=True)
    parser.add_argument("--adoption-result", required=True)
    parser.add_argument("--current-result", required=True)
    parser.add_argument("--continuation-ask")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    common = {
        "cycle": args.cycle,
        "version": args.version,
        "baseline_version": args.baseline_version,
        "next_version": args.next_version,
        "repo_id": args.repo_id,
        "artifact_name": args.artifact,
        "artifact_sha256": args.artifact_sha256,
        "artifact_intake_path": args.artifact_intake,
        "all_tests_path": args.all_tests_summary,
        "visual_artifact_path": args.visual_artifact,
        "adoption_path": args.adoption_result,
        "current_path": args.current_result,
    }
    if args.preflight_only:
        result = evaluate_mvp_proof_preflight_files(**common)
        digest_field = "preflight_sha256"
    else:
        if not args.continuation_ask:
            raise SystemExit("--continuation-ask is required unless --preflight-only is used")
        result = evaluate_mvp_proof_cycle_files(
            **common,
            continuation_ask_path=args.continuation_ask,
        )
        digest_field = "proof_sha256"

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"status: {result['status']}")
        print(f"{digest_field}: {result[digest_field]}")
        if result["failed_checks"]:
            print("failed_checks:")
            for check in result["failed_checks"]:
                print(f"  - {check}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
