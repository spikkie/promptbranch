#!/usr/bin/env bash
set -Euo pipefail

cycle=""
version=""
baseline_version=""
next_version=""
artifact_intake=""
release_log_dir=""
pb_cmd="${PB_CMD:-pb}"

usage() {
  cat <<'EOF'
Usage: scripts/finalize-mvp-proof-cycle.sh \
  --cycle N --version VERSION --baseline-version VERSION --next-version VERSION \
  --artifact-intake PATH [--release-log-dir DIR] [--pb-cmd COMMAND]

Runs one real post-adoption continuation ask from the accepted/current baseline,
then verifies the complete canonical MVP proof-cycle evidence set. It does not
publish, adopt, overwrite Project Sources, commit, push, or mutate repository files.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cycle) cycle="$2"; shift 2 ;;
    --version) version="$2"; shift 2 ;;
    --baseline-version) baseline_version="$2"; shift 2 ;;
    --next-version) next_version="$2"; shift 2 ;;
    --artifact-intake) artifact_intake="$2"; shift 2 ;;
    --release-log-dir) release_log_dir="$2"; shift 2 ;;
    --pb-cmd) pb_cmd="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for name in cycle version baseline_version next_version artifact_intake; do
  [[ -n "${!name}" ]] || { echo "ERROR: --${name//_/-} is required" >&2; exit 2; }
done
command -v "$pb_cmd" >/dev/null 2>&1 || { echo "ERROR: pb command not found: $pb_cmd" >&2; exit 2; }
[[ -f "$artifact_intake" ]] || { echo "ERROR: artifact intake evidence not found: $artifact_intake" >&2; exit 2; }

if [[ -z "$release_log_dir" ]]; then
  release_log_dir=".pb_profile/release_logs/${version}"
fi
artifact="chatgpt_claudecode_workflow-2_${version}.zip"
all_tests="${release_log_dir}/pb_test.all.${version}.summary.json"
visual="${release_log_dir}/pb_test.visual_artifact_roundtrip.${version}.log"
adoption="${release_log_dir}/pb_artifact_adopt.${version}.json"
current="${release_log_dir}/pb_artifact_current.${version}.json"
continuation_request="${release_log_dir}/mvp-proof-cycle-${cycle}.continuation-request.${version}.json"
continuation_run="${release_log_dir}/mvp-proof-cycle-${cycle}.continuation-run.${version}.json"
continuation="${release_log_dir}/mvp-proof-cycle-${cycle}.continuation-ask.${version}.json"
proof="${release_log_dir}/mvp-proof-cycle-${cycle}.${version}.json"

for path in "$all_tests" "$visual" "$adoption" "$current"; do
  [[ -f "$path" ]] || { echo "ERROR: required proof evidence missing: $path" >&2; exit 1; }
done

continuation_prompt="Continue MVP proof cycle ${cycle} from accepted ${version} toward ${next_version}. Return a valid Promptbranch reply envelope with status no_artifact and result_type no_change; no artifact is required for this continuation proof."

# Capture the exact request envelope before executing the same protocol ask.
"$pb_cmd" ask "$continuation_prompt" \
  --protocol \
  --from-current-baseline \
  --target-version "$next_version" \
  --intent-kind mvp_proof_continuation \
  --print-request-json \
  --json | tee "$continuation_request"

# Execute the continuation ask and require a validated reply envelope.
"$pb_cmd" ask "$continuation_prompt" \
  --protocol \
  --from-current-baseline \
  --target-version "$next_version" \
  --intent-kind mvp_proof_continuation \
  --parse-reply \
  --json | tee "$continuation_run"

python3 - "$continuation_request" "$continuation_run" "$continuation" <<'PY'
import json
import sys
from pathlib import Path

request_payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
run_payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
combined = {
    "ok": run_payload.get("ok") is True,
    "action": "mvp_proof_continuation_ask",
    "request": request_payload.get("request"),
    "run": run_payload,
}
Path(sys.argv[3]).write_text(
    json.dumps(combined, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

python3 scripts/verify-mvp-proof-cycle.py \
  --cycle "$cycle" \
  --version "$version" \
  --baseline-version "$baseline_version" \
  --next-version "$next_version" \
  --artifact "$artifact" \
  --artifact-intake "$artifact_intake" \
  --all-tests-summary "$all_tests" \
  --visual-artifact "$visual" \
  --adoption-result "$adoption" \
  --current-result "$current" \
  --continuation-ask "$continuation" \
  --output "$proof" \
  --json

echo "MVP proof cycle ${cycle} verified: ${proof}"
