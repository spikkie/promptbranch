#!/usr/bin/env bash
set -euo pipefail

tmp_prompt="$(mktemp)"
out_json="${TMPDIR:-/tmp}/pb-ask-prompt-file-smoke.$$.json"
cleanup() {
  rm -f "$tmp_prompt" "$out_json"
}
trap cleanup EXIT

cat > "$tmp_prompt" <<'PROMPT'
Return exactly the single token CV_LIVE_PROMPT_FILE_OK and nothing else.
PROMPT

pb ask "Use the prompt file." --prompt-file "$tmp_prompt" --json > "$out_json"

python3 - "$out_json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
answer = str(payload.get("answer") or payload.get("answer_text") or "").strip()
submit_evidence = payload.get("submit_evidence") if isinstance(payload.get("submit_evidence"), dict) else {}
prefer_button_submit = payload.get("prefer_button_submit")
if prefer_button_submit is None:
    prefer_button_submit = submit_evidence.get("prefer_button_submit")
submit_method = payload.get("submit_method") or submit_evidence.get("submit_method")
submit_message_observed = payload.get("submit_message_request_observed")
if submit_message_observed is None:
    submit_message_observed = submit_evidence.get("submit_message_request_observed")
backend_commit = payload.get("submit_backend_commit_confirmed")
if backend_commit is None:
    backend_commit = bool(
        submit_evidence.get("submit_backend_commit_after_prepare_found")
        or submit_evidence.get("submit_backend_task_message_found")
        or submit_evidence.get("submit_confirmed")
    )

failures = []
if payload.get("ok") is not True:
    failures.append(f"ok is not true: {payload.get('ok')!r}")
if answer != "CV_LIVE_PROMPT_FILE_OK":
    failures.append(f"unexpected answer: {answer!r}")
if prefer_button_submit is not True:
    failures.append(f"prefer_button_submit is not true: {prefer_button_submit!r}")
if submit_method not in {"button_click", "button_after_focus_retry", "send_button_click"}:
    failures.append(f"submit_method is not button-first: {submit_method!r}")
if submit_message_observed is False and not backend_commit:
    failures.append("submit causality was not confirmed")
if payload.get("status") == "prepare_token_set_not_consumed":
    failures.append("prepare_token_set_not_consumed remained unresolved")
if payload.get("answer_text_length") == 0:
    failures.append("answer_text_length is zero")

if failures:
    print(json.dumps({"ok": False, "failures": failures, "payload": payload}, indent=2, sort_keys=True), file=sys.stderr)
    sys.exit(1)
print(json.dumps({"ok": True, "answer": answer, "submit_method": submit_method, "prefer_button_submit": prefer_button_submit}, indent=2, sort_keys=True))
PY
