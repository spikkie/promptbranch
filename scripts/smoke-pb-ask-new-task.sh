#!/usr/bin/env bash
set -euo pipefail

state_file="${PROMPTBRANCH_STATE_FILE:-.pb_profile/.promptbranch_state.json}"
log_file="${PROMPTBRANCH_NEW_TASK_SMOKE_LOG:-$HOME/tmp/pb_new_task_smoke.log}"
mkdir -p "$(dirname "$log_file")"

if [[ ! -f "$state_file" ]]; then
  echo "error: state file not found: $state_file" >&2
  exit 2
fi

before="$(jq -r '.current.conversation_url // empty' "$state_file")"
sentinel="NEW_TASK_OK_$(date -u +%Y%m%dT%H%M%SZ)"

pb ask --new-task --text "Return exactly the single token ${sentinel} and nothing else." \
  2>&1 | tee "$log_file"

after="$(jq -r '.current.conversation_url // empty' "$state_file")"

echo "before=$before"
echo "after=$after"
if grep -F "$sentinel" "$log_file" >/dev/null; then
  echo "sentinel_ok=1"
else
  echo "sentinel_ok=0"
fi

if [[ -n "$after" && "$before" != "$after" ]]; then
  echo "new_task_state_ok=1"
else
  echo "new_task_state_ok=0"
fi

if grep -F "$sentinel" "$log_file" >/dev/null && [[ -n "$after" && "$before" != "$after" ]]; then
  exit 0
fi
exit 1
