#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from promptbranch_service_client import ChatGPTServiceClient
DEFAULT_CONFIG_PATH = "~/.config/promptbranch/config.json"
LEGACY_CONFIG_PATH = "~/.config/chatgpt-cli/config.json"
DEFAULT_TARGET_FILE_ID = "file_00000000a7cc71f48c35989259e6dc33"
DEFAULT_TARGET_LIBFILE_ID = "libfile_8b26b82651e88191a9e965b267290f5b"
DEFAULT_TARGET_FILENAME = "pb-ab-legacy-28f3d84be7.txt"

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
    parser = argparse.ArgumentParser(description="Run the v0.1.103.10.89 exact Library backing-object reupload diagnostic.")
    parser.add_argument("--config", default=os.getenv("CHATGPT_CLI_CONFIG", DEFAULT_CONFIG_PATH))
    parser.add_argument("--service-base-url")
    parser.add_argument("--service-token")
    parser.add_argument("--project-name-prefix", default="itest-pb-library-backing")
    parser.add_argument("--profile-lock-wait-seconds", type=float)
    parser.add_argument("--timeout-seconds", type=float, default=1800.0)
    parser.add_argument("--keep-open", action="store_true")
    parser.add_argument("--initial-target-processed-file-id", default=DEFAULT_TARGET_FILE_ID)
    parser.add_argument("--initial-target-library-metadata-object-id", default=DEFAULT_TARGET_LIBFILE_ID)
    parser.add_argument("--initial-target-filename", default=DEFAULT_TARGET_FILENAME)
    args = parser.parse_args()
    config = load_config(args.config)
    base_url = args.service_base_url or os.getenv("CHATGPT_SERVICE_BASE_URL") or os.getenv("CHATGPT_API_BASE_URL") or config.get("service_base_url") or "http://localhost:8000"
    token = args.service_token or os.getenv("CHATGPT_SERVICE_TOKEN") or os.getenv("CHATGPT_API_TOKEN") or config.get("service_token")
    with ChatGPTServiceClient(str(base_url), token=str(token) if token else None, timeout=args.timeout_seconds) as client:
        result = client.run_library_backing_reupload_diagnostic(
            project_name_prefix=args.project_name_prefix,
            keep_open=args.keep_open,
            allow_project_source_mutation=True,
            profile_lock_wait_seconds=args.profile_lock_wait_seconds,
            request_timeout_seconds=args.timeout_seconds,
            initial_target_processed_file_id=args.initial_target_processed_file_id,
            initial_target_library_metadata_object_id=args.initial_target_library_metadata_object_id,
            initial_target_filename=args.initial_target_filename,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "diagnostic_completed" else 2

if __name__ == "__main__":
    raise SystemExit(main())
