#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from promptbranch_service_client import ChatGPTServiceClient

DEFAULT_CONFIG_PATH = "~/.config/promptbranch/config.json"
LEGACY_CONFIG_PATH = "~/.config/chatgpt-cli/config.json"


def load_config(path: str | None) -> dict:
    candidates = [Path(path).expanduser()] if path else []
    if candidates and candidates[0] == Path(DEFAULT_CONFIG_PATH).expanduser():
        candidates.append(Path(LEGACY_CONFIG_PATH).expanduser())
    for candidate in candidates:
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the v0.1.103.10.92 authenticated backing-file backend protocol discovery and canonical reupload diagnostic."
    )
    parser.add_argument("--config", default=os.getenv("CHATGPT_CLI_CONFIG", DEFAULT_CONFIG_PATH))
    parser.add_argument("--service-base-url")
    parser.add_argument("--service-token")
    parser.add_argument("--project-name-prefix", default="itest-pb-library-backend")
    parser.add_argument("--profile-lock-wait-seconds", type=float)
    parser.add_argument("--timeout-seconds", type=float, default=3600.0)
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    base_url = (
        args.service_base_url
        or os.getenv("CHATGPT_SERVICE_BASE_URL")
        or os.getenv("CHATGPT_API_BASE_URL")
        or config.get("service_base_url")
        or "http://localhost:8000"
    )
    token = (
        args.service_token
        or os.getenv("CHATGPT_SERVICE_TOKEN")
        or os.getenv("CHATGPT_API_TOKEN")
        or config.get("service_token")
    )
    with ChatGPTServiceClient(str(base_url), token=str(token) if token else None, timeout=args.timeout_seconds) as client:
        result = client.run_library_backend_protocol_reupload_diagnostic(
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
