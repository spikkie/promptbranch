#!/usr/bin/env bash
set -uo pipefail

trace_enabled="${PROMPTBRANCH_SMOKE_TRACE:-1}"
if [[ "$trace_enabled" != "0" && "$trace_enabled" != "false" ]]; then
  set -x
fi

tmp_prompt="$(mktemp)"
out_json="${TMPDIR:-/tmp}/pb-ask-prompt-file-smoke.$$.json"
keep_json=1
cleanup() {
  rm -f "$tmp_prompt"
  if [[ "$keep_json" == "0" ]]; then
    rm -f "$out_json"
  fi
}
trap cleanup EXIT

cat > "$tmp_prompt" <<'PROMPT'
Return exactly the single token CV_LIVE_PROMPT_FILE_OK and nothing else.
PROMPT

set +e
pb ask "Use the prompt file." --prompt-file "$tmp_prompt" --json > "$out_json"
pb_rc=$?
set -e

set +e
python3 - "$out_json" "$pb_rc" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
pb_rc = int(sys.argv[2])
raw_text = path.read_text(encoding="utf-8") if path.exists() else ""
try:
    payload = json.loads(raw_text) if raw_text.strip() else {}
except json.JSONDecodeError as exc:
    print(json.dumps({
        "ok": False,
        "failures": [f"pb ask did not emit valid JSON: {exc}"],
        "pb_ask_exit_code": pb_rc,
        "output_json": str(path),
        "raw_output_preview": raw_text[:2000],
    }, indent=2, sort_keys=True), file=sys.stderr)
    sys.exit(1)

EXPECTED_TOKEN = "CV_LIVE_PROMPT_FILE_OK"
answer_obj = payload.get("answer")
answer_text = str(payload.get("answer_text") or "").strip()
if isinstance(answer_obj, dict):
    answer = str(answer_obj.get("token") or answer_obj.get("answer") or answer_obj.get("text") or answer_text).strip()
else:
    answer = str(answer_obj or answer_text or "").strip()
submit_evidence = payload.get("submit_evidence") if isinstance(payload.get("submit_evidence"), dict) else {}
ask_phase_timings = payload.get("ask_phase_timings") if isinstance(payload.get("ask_phase_timings"), dict) else {}
prefer_button_submit = payload.get("prefer_button_submit")
if prefer_button_submit is None:
    prefer_button_submit = submit_evidence.get("prefer_button_submit")
if prefer_button_submit is None:
    prefer_button_submit = ask_phase_timings.get("prefer_button_submit")
submit_method = payload.get("submit_method") or submit_evidence.get("submit_method") or ask_phase_timings.get("submit_method")
submit_message_observed = payload.get("submit_message_request_observed")
if submit_message_observed is None:
    submit_message_observed = submit_evidence.get("submit_message_request_observed")
if submit_message_observed is None:
    submit_message_observed = ask_phase_timings.get("submit_message_request_observed")
backend_commit = payload.get("submit_backend_commit_confirmed")
if backend_commit is None:
    backend_commit = bool(
        submit_evidence.get("submit_backend_commit_after_prepare_found")
        or submit_evidence.get("submit_backend_task_message_found")
        or submit_evidence.get("submit_confirmed")
        or ask_phase_timings.get("submit_backend_commit_after_prepare_found")
        or ask_phase_timings.get("submit_backend_task_message_found")
        or ask_phase_timings.get("submit_confirmed")
    )

failures = []
if pb_rc != 0:
    failures.append(f"pb ask exited non-zero: {pb_rc}")
if payload.get("ok") is not True:
    failures.append(f"ok is not true: {payload.get('ok')!r}")
if answer != EXPECTED_TOKEN:
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
    print(json.dumps({
        "ok": False,
        "failures": failures,
        "pb_ask_exit_code": pb_rc,
        "output_json": str(path),
        "payload": payload,
    }, indent=2, sort_keys=True), file=sys.stderr)
    sys.exit(1)
print(json.dumps({
    "ok": True,
    "answer": answer,
    "expected_token": EXPECTED_TOKEN,
    "submit_method": submit_method,
    "prefer_button_submit": prefer_button_submit,
    "pb_ask_exit_code": pb_rc,
}, indent=2, sort_keys=True))
PY
py_rc=$?
set -e
if [[ "$py_rc" -eq 0 ]]; then
  keep_json=0
else
  echo "Prompt-file smoke failed; diagnostic JSON kept at: $out_json" >&2
fi
exit "$py_rc"
