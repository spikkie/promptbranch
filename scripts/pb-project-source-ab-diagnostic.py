#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# This diagnostic is intentionally runnable directly from the source tree.
# Python sets sys.path[0] to scripts/ for a file-path invocation, so add the
# repository root before importing the repository-level service client module.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from promptbranch_service_client import ChatGPTServiceClient


DEFAULT_CONFIG_PATH = "~/.config/promptbranch/config.json"
LEGACY_CONFIG_PATH = "~/.config/chatgpt-cli/config.json"


def _load_service_config(path: str | None) -> dict[str, object]:
    if not path:
        return {}
    primary = Path(path).expanduser()
    candidates = [primary]
    if primary == Path(DEFAULT_CONFIG_PATH).expanduser():
        candidates.append(Path(LEGACY_CONFIG_PATH).expanduser())
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _resolve_service_settings(args: argparse.Namespace) -> tuple[str, str | None]:
    config = _load_service_config(args.config)
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
    return str(base_url), str(token) if token not in (None, "") else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the v0.1.103.10.85 Project Source legacy-vs-current A/B diagnostic."
    )
    parser.add_argument(
        "--config",
        default=os.getenv("CHATGPT_CLI_CONFIG", DEFAULT_CONFIG_PATH),
        help=(
            "Promptbranch JSON config. Defaults to ~/.config/promptbranch/config.json "
            "and falls back to ~/.config/chatgpt-cli/config.json."
        ),
    )
    parser.add_argument("--service-base-url", default=None)
    parser.add_argument("--service-token", default=None)
    parser.add_argument("--project-name-prefix", default="itest-pb-source-ab")
    parser.add_argument("--profile-lock-wait-seconds", type=float)
    parser.add_argument("--timeout-seconds", type=float, default=1800.0)
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()

    service_base_url, service_token = _resolve_service_settings(args)

    with ChatGPTServiceClient(
        service_base_url,
        token=service_token,
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
