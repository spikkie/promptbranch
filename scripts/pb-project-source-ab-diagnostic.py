#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

from promptbranch_service_client import ChatGPTServiceClient


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the v0.1.103.10.85 Project Source legacy-vs-current A/B diagnostic."
    )
    parser.add_argument(
        "--service-base-url",
        default=os.getenv("CHATGPT_SERVICE_BASE_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--service-token",
        default=os.getenv("CHATGPT_SERVICE_TOKEN") or os.getenv("CHATGPT_API_TOKEN"),
    )
    parser.add_argument("--project-name-prefix", default="itest-pb-source-ab")
    parser.add_argument("--profile-lock-wait-seconds", type=float)
    parser.add_argument("--timeout-seconds", type=float, default=1800.0)
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()

    with ChatGPTServiceClient(
        args.service_base_url,
        token=args.service_token,
        timeout=args.timeout_seconds,
    ) as client:
        result = client.run_project_source_ab_diagnostic(
            project_name_prefix=args.project_name_prefix,
            keep_open=args.keep_open,
            allow_project_source_mutation=True,
            profile_lock_wait_seconds=args.profile_lock_wait_seconds,
            request_timeout_seconds=args.timeout_seconds,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "diagnostic_completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
