#!/usr/bin/env bash
set -Eeuo pipefail

cycle=""
version=""
baseline_version=""
next_version=""
repo_id="chatgpt_claudecode_workflow-2"
artifact_intake=""
artifact_path=""
release_log_dir=""
pb_cmd="${PB_CMD:-pb}"
conversation_url=""

usage() {
  cat <<'EOF'
Usage: scripts/finalize-mvp-proof-cycle.sh \
  --cycle N --version VERSION --baseline-version VERSION --next-version VERSION \
  --artifact-intake PATH [--artifact-path PATH] [--repo-id REPO_ID] \
  [--release-log-dir DIR] [--pb-cmd COMMAND] --conversation-url URL

Validates all non-continuation proof evidence first. Only after the intake,
release, visual transport, adoption, accepted/current identity, and SHA-256
bindings pass does it issue one post-adoption continuation ask from the
accepted/current baseline. It does not publish, adopt, overwrite Project
Sources, commit, push, or mutate repository files.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cycle) cycle="$2"; shift 2 ;;
    --version) version="$2"; shift 2 ;;
    --baseline-version) baseline_version="$2"; shift 2 ;;
    --next-version) next_version="$2"; shift 2 ;;
    --repo-id) repo_id="$2"; shift 2 ;;
    --artifact-intake) artifact_intake="$2"; shift 2 ;;
    --artifact-path) artifact_path="$2"; shift 2 ;;
    --release-log-dir) release_log_dir="$2"; shift 2 ;;
    --pb-cmd) pb_cmd="$2"; shift 2 ;;
    --conversation-url) conversation_url="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for name in cycle version baseline_version next_version repo_id artifact_intake conversation_url; do
  [[ -n "${!name}" ]] || { echo "ERROR: --${name//_/-} is required" >&2; exit 2; }
done
command -v "$pb_cmd" >/dev/null 2>&1 || { echo "ERROR: pb command not found: $pb_cmd" >&2; exit 2; }
[[ -f "$artifact_intake" ]] || { echo "ERROR: artifact intake evidence not found: $artifact_intake" >&2; exit 2; }
python3 - "$conversation_url" <<'PY'
import sys
from urllib.parse import urlparse
url = sys.argv[1]
parsed = urlparse(url)
parts = [part for part in parsed.path.split("/") if part]
if parsed.scheme not in {"http", "https"} or not parsed.netloc or len(parts) < 4 or parts[0] != "g" or parts[2] != "c" or not parts[3]:
    raise SystemExit("ERROR: --conversation-url must be a complete ChatGPT Project conversation URL")
PY

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/.." && pwd -P)"
verify_script="${script_dir}/verify-mvp-proof-cycle.py" # scripts/verify-mvp-proof-cycle.py
if [[ -z "$release_log_dir" ]]; then
  release_log_dir="${repo_root}/.pb_profile/release_logs/${version}"
fi
artifact="${repo_id}_${version}.zip"
if [[ -z "$artifact_path" ]]; then
  artifact_path="${repo_root}/${artifact}"
fi
[[ -f "$artifact_path" ]] || { echo "ERROR: candidate artifact not found: $artifact_path" >&2; exit 2; }
artifact_sha256="$(sha256sum "$artifact_path" | awk '{print $1}')"

all_tests="${release_log_dir}/pb_test.all.${version}.summary.json"
visual="${release_log_dir}/pb_test.visual_artifact_roundtrip.${version}.log"
adoption="${release_log_dir}/pb_artifact_adopt.${version}.json"
current="${release_log_dir}/pb_artifact_current.${version}.json"
preflight="${release_log_dir}/mvp-proof-cycle-${cycle}.preflight.${version}.json"
continuation_request="${release_log_dir}/mvp-proof-cycle-${cycle}.continuation-request.${version}.json"
continuation_run="${release_log_dir}/mvp-proof-cycle-${cycle}.continuation-run.${version}.json"
continuation="${release_log_dir}/mvp-proof-cycle-${cycle}.continuation-ask.${version}.json"
proof="${release_log_dir}/mvp-proof-cycle-${cycle}.${version}.json"

for path in "$all_tests" "$visual" "$adoption" "$current"; do
  [[ -f "$path" ]] || { echo "ERROR: required proof evidence missing: $path" >&2; exit 1; }
done

verify_args=(
  --cycle "$cycle"
  --version "$version"
  --baseline-version "$baseline_version"
  --next-version "$next_version"
  --repo-id "$repo_id"
  --artifact "$artifact"
  --artifact-sha256 "$artifact_sha256"
  --artifact-intake "$artifact_intake"
  --all-tests-summary "$all_tests"
  --visual-artifact "$visual"
  --adoption-result "$adoption"
  --current-result "$current"
)

# Fail closed before any ChatGPT continuation action. Invalid intake or identity
# evidence must not create continuation request/run files.
if python3 "$verify_script" \
  "${verify_args[@]}" \
  --preflight-only \
  --output "$preflight" \
  --json; then
  echo "MVP proof preflight passed: ${preflight}"
else
  preflight_rc=$?
  echo "ERROR: MVP proof preflight failed; continuation ask was not issued: ${preflight}" >&2
  exit "$preflight_rc"
fi

continuation_prompt="Continue MVP proof cycle ${cycle} from accepted ${version} toward ${next_version}. Return a valid Promptbranch reply envelope with status no_artifact and result_type no_change; no artifact is required for this continuation proof."

# Capture the exact request envelope before executing the same protocol ask.
"$pb_cmd" ask "$continuation_prompt" \
  --protocol \
  --from-current-baseline \
  --target-version "$next_version" \
  --conversation-url "$conversation_url" \
  --intent-kind mvp_proof_continuation \
  --print-request-json \
  --json | tee "$continuation_request"

# Execute the continuation ask and require a validated reply envelope.
"$pb_cmd" ask "$continuation_prompt" \
  --protocol \
  --from-current-baseline \
  --target-version "$next_version" \
  --conversation-url "$conversation_url" \
  --intent-kind mvp_proof_continuation \
  --parse-reply \
  --json | tee "$continuation_run"

python3 - "$continuation_request" "$continuation_run" "$continuation" "$conversation_url" <<'PY'
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

request_payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
run_payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
expected_url = sys.argv[4]

def conversation_id(value):
    parsed = urlparse(str(value or ""))
    parts = [part for part in parsed.path.split("/") if part]
    return parts[3] if len(parts) >= 4 and parts[0] == "g" and parts[2] == "c" else None

def selected_url(payload):
    selected = payload.get("selected_protocol_reply") if isinstance(payload.get("selected_protocol_reply"), dict) else {}
    return selected.get("conversation_url") or payload.get("conversation_url")

observed_url = selected_url(run_payload)
expected_id = conversation_id(expected_url)
observed_id = conversation_id(observed_url)
conversation_ok = bool(expected_id and observed_id == expected_id)
combined = {
    "ok": run_payload.get("ok") is True and conversation_ok,
    "action": "mvp_proof_continuation_ask",
    "request": request_payload.get("request"),
    "run": run_payload,
    "conversation_selection": {
        "selection": "explicit_cli_argument",
        "conversation_url": expected_url,
        "conversation_id": expected_id,
        "observed_conversation_url": observed_url,
        "observed_conversation_id": observed_id,
        "matches": conversation_ok,
    },
}
Path(sys.argv[3]).write_text(
    json.dumps(combined, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
if not combined["ok"]:
    raise SystemExit(1)
PY

if python3 "$verify_script" \
  "${verify_args[@]}" \
  --continuation-ask "$continuation" \
  --output "$proof" \
  --json; then
  echo "MVP proof cycle ${cycle} verified: ${proof}"
else
  proof_rc=$?
  echo "ERROR: MVP proof cycle ${cycle} failed verification: ${proof}" >&2
  exit "$proof_rc"
fi
