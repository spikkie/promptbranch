#!/usr/bin/env bash
set -euo pipefail

prompt_file="${1:-docs/rag/generated/cv_chatgpt_prompt_package_devops-automation-en_v0.6.23.md}"
if [[ ! -f "$prompt_file" ]]; then
  echo "large prompt-file smoke requires an existing prompt file: $prompt_file" >&2
  exit 2
fi

out_json="${TMPDIR:-/tmp}/pb-ask-large-prompt-file-smoke.$$.json"
keep_json=1
cleanup() {
  if [[ "$keep_json" == "0" ]]; then
    rm -f "$out_json"
  fi
}
trap cleanup EXIT

set +e
pb ask "Use the prompt file as the full instruction. Return exactly the requested CV_MARKDOWN and EVIDENCE_SIDECAR_JSON sections." \
  --prompt-file "$prompt_file" \
  --prompt-file-mode auto \
  > "$out_json"
pb_rc=$?
set -e

set +e
python3 - "$out_json" "$pb_rc" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
pb_rc = int(sys.argv[2])
payload = json.loads(path.read_text(encoding="utf-8"))
answer_text = str(payload.get("answer_text") or payload.get("answer") or "")
phase = payload.get("ask_phase_timings") if isinstance(payload.get("ask_phase_timings"), dict) else {}
transport = payload.get("prompt_file_transport") if isinstance(payload.get("prompt_file_transport"), dict) else {}
submit = payload.get("submit_evidence") if isinstance(payload.get("submit_evidence"), dict) else {}

failures = []
if pb_rc != 0:
    failures.append(f"pb ask exited non-zero: {pb_rc}")
if payload.get("ok") is False:
    failures.append(f"ok is false: status={payload.get('status')!r} error_type={payload.get('error_type')!r}")
if transport.get("mode_effective") != "attachment":
    failures.append(f"prompt_file_transport.mode_effective is not attachment: {transport.get('mode_effective')!r}")
if "CV_MARKDOWN" not in answer_text:
    failures.append("answer missing CV_MARKDOWN")
if "EVIDENCE_SIDECAR_JSON" not in answer_text:
    failures.append("answer missing EVIDENCE_SIDECAR_JSON")
if payload.get("attachment_mode") is not True:
    failures.append(f"attachment_mode is not true: {payload.get('attachment_mode')!r}")
if payload.get("attachment_upload_completed") is not True:
    failures.append(f"attachment_upload_completed is not true: {payload.get('attachment_upload_completed')!r}")
if payload.get("attachment_visible") is not True:
    failures.append(f"attachment_visible is not true: {payload.get('attachment_visible')!r}")
if payload.get("attachment_filename_expected") != payload.get("attachment_filename_visible"):
    failures.append(f"attachment filename mismatch: expected={payload.get('attachment_filename_expected')!r} visible={payload.get('attachment_filename_visible')!r}")
if payload.get("attachment_ready_for_submit") is not True:
    failures.append(f"attachment_ready_for_submit is not true: {payload.get('attachment_ready_for_submit')!r}")
if payload.get("submit_method") not in {"button_click", "button_after_focus_retry", "send_button_click"}:
    failures.append(f"submit_method is not button-first: {payload.get('submit_method')!r}")
if payload.get("prefer_button_submit") is not True:
    failures.append(f"prefer_button_submit is not true: {payload.get('prefer_button_submit')!r}")
if payload.get("submit_causality_confirmed") is not True:
    failures.append(f"submit_causality_confirmed is not true: {payload.get('submit_causality_confirmed')!r}")
if payload.get("response_causality_confirmed") is not True:
    failures.append(f"response_causality_confirmed is not true: {payload.get('response_causality_confirmed')!r}")
if payload.get("response_wait_skipped") is True or phase.get("response_wait_skipped") is True:
    failures.append(f"response wait was skipped: {payload.get('response_wait_skipped_reason') or phase.get('response_wait_skipped_reason')!r}")
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
    "pb_ask_exit_code": pb_rc,
    "answer_text_length": payload.get("answer_text_length"),
    "prompt_file_transport": transport,
    "attachment_mode": payload.get("attachment_mode"),
    "attachment_upload_completed": payload.get("attachment_upload_completed"),
    "attachment_visible": payload.get("attachment_visible"),
    "attachment_filename_expected": payload.get("attachment_filename_expected"),
    "attachment_filename_visible": payload.get("attachment_filename_visible"),
    "attachment_ready_for_submit": payload.get("attachment_ready_for_submit"),
    "submit_method": payload.get("submit_method"),
    "prefer_button_submit": payload.get("prefer_button_submit"),
    "submit_causality_confirmed": payload.get("submit_causality_confirmed"),
    "response_causality_confirmed": payload.get("response_causality_confirmed"),
    "response_accepted_source": payload.get("response_accepted_source") or phase.get("response_accepted_source"),
}, indent=2, sort_keys=True))
PY
py_rc=$?
set -e

if [[ "$py_rc" -eq 0 ]]; then
  keep_json=0
  exit 0
fi

echo "Large prompt-file smoke failed; diagnostic JSON kept at: $out_json" >&2
exit "$py_rc"
