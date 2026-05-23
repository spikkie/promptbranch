#!/usr/bin/env bash
set -Euo pipefail

# Run the standard post-release validation sequence for chatgpt_claudecode_workflow.
# This script is validation-only by default: it does not adopt artifacts,
# mutate Project Sources, migrate candidates, or advance release state unless
# --adopt-if-accepted is explicitly supplied.

project_name="chatgpt_claudecode_workflow"
version_arg=""
target_version_arg=""
release_log_root=".pb_profile/release_logs"
test_timeout_seconds="${PROMPTBRANCH_TEST_TIMEOUT_SECONDS:-3600}"
protocol_timeout_seconds="${PROMPTBRANCH_PROTOCOL_TIMEOUT_SECONDS:-120}"
fresh_turn_timeout_seconds="${PROMPTBRANCH_PROTOCOL_FRESH_TURN_TIMEOUT_SECONDS:-60}"
fresh_turn_poll_seconds="${PROMPTBRANCH_PROTOCOL_FRESH_TURN_POLL_SECONDS:-2}"
pb_cmd_arg="${PB_CMD:-}"
skip_protocol_smoke=0
skip_artifact_intake=0
skip_candidate_run=0
require_candidate_mvp_complete=0
complete_candidate_mvp=0
require_real_candidate_mvp=0
candidate_mvp_max_steps="${PROMPTBRANCH_CANDIDATE_MVP_MAX_STEPS:-4}"
candidate_run_step_timeout_seconds="${PROMPTBRANCH_CANDIDATE_RUN_STEP_TIMEOUT_SECONDS:-3600}"
skip_tests=0
skip_zip_hygiene=0
adopt_if_accepted=0
require_adopted_baseline=0

usage() {
  cat <<USAGE
Usage:
  $(basename "$0") [--version VERSION] [--target-version VERSION] [options]

Runs the standard post-release validation sequence:
  1. promptbranch artifact current --json
  2. semantic artifact/source baseline check against --version (diagnostic by default)
  3. protocol smoke ask targeting the next version
     - default mode: before local test/report gates
     - --adopt-if-accepted mode: after successful adoption, so --from-current-baseline uses --version
  4. artifact intake dry-run from the last validated protocol reply
  5. artifact candidate-run plan-only smoke for the MVP lifecycle command
     - optionally with --require-complete for artifact-candidate MVP completion proof
  6. promptbranch test full/report
  7. release ZIP hygiene check
  8. optional adoption/recheck when --adopt-if-accepted is supplied

Options:
  -v, --version VERSION          Release version under validation. Defaults to VERSION file.
      --target-version VERSION   Target version for protocol smoke. Defaults to next normal version.
      --pb-cmd COMMAND           Promptbranch executable. Defaults to promptbranch, then pb.
      --release-log-dir DIR      Release log root. Default: .pb_profile/release_logs.
      --test-timeout SEC         Timeout wrapper for pb test full. Default: ${test_timeout_seconds}.
      --skip-protocol-smoke      Skip pb ask --protocol smoke.
      --skip-artifact-intake     Skip pb artifact intake dry-run.
      --skip-candidate-run       Skip pb artifact candidate-run plan-only smoke.
      --require-candidate-mvp-complete
                              Run candidate-run with --require-complete and fail unless the
                              artifact-candidate MVP completion proof is satisfied.
      --complete-candidate-mvp
                              Run candidate-run with --execute-until-blocked --require-complete
                              after protocol/intake gates. This can execute existing allowlisted
                              candidate lifecycle steps and stops fail-closed.
      --require-real-candidate-mvp
                              Add --require-real-candidate to candidate-run. The no_artifact
                              protocol-smoke precondition is then a hard failure, not a
                              normalized terminal state.
      --candidate-mvp-max-steps N
                              Maximum candidate-run lifecycle steps for --complete-candidate-mvp.
                              Default: ${candidate_mvp_max_steps}.
      --candidate-run-step-timeout SEC
                              Per-step timeout for candidate-run lifecycle execution.
                              Default: ${candidate_run_step_timeout_seconds}.
      --skip-tests               Skip pb test full/report.
      --skip-zip-hygiene         Skip ZIP entry hygiene check.
      --adopt-if-accepted        If validation passes, adopt --version as current baseline and re-check semantic state.
      --require-adopted-baseline Fail if artifact/source baseline does not already match --version.
  -h, --help                     Show this help.

Examples:
  scripts/post-release-validation.sh --version v0.0.222.1 --target-version v0.0.223
  scripts/post-release-validation.sh --version v0.0.222.1 --target-version v0.0.223 --adopt-if-accepted
  PB_CMD=pb scripts/post-release-validation.sh --version v0.0.222.1
USAGE
}

normalize_version() {
  local raw="$1"
  raw="${raw##*/}"
  raw="${raw%.zip}"
  raw="${raw#${project_name}_}"
  raw="${raw#${project_name}}"
  raw="${raw#_}"
  if [[ "${raw}" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
    raw="${raw#v}"
    printf 'v%s\n' "${raw}"
    return 0
  fi
  return 1
}

next_normal_version() {
  local normalized="${1#v}"
  IFS='.' read -r major minor patch repair_extra <<<"${normalized}"
  [[ -n "${major:-}" && -n "${minor:-}" && -n "${patch:-}" ]] || return 1
  patch=$((patch + 1))
  printf 'v%s.%s.%s\n' "${major}" "${minor}" "${patch}"
}

select_pb_cmd() {
  if [[ -n "${pb_cmd_arg}" ]]; then
    command -v "${pb_cmd_arg}" >/dev/null 2>&1 || {
      echo "ERROR: --pb-cmd not found: ${pb_cmd_arg}" >&2
      return 1
    }
    printf '%s\n' "${pb_cmd_arg}"
    return 0
  fi
  if command -v promptbranch >/dev/null 2>&1; then
    printf 'promptbranch\n'
    return 0
  fi
  if command -v pb >/dev/null 2>&1; then
    printf 'pb\n'
    return 0
  fi
  echo "ERROR: neither promptbranch nor pb found in PATH" >&2
  return 1
}

run_step() {
  local label="$1"
  local outfile="$2"
  shift 2
  echo
  echo "===== ${label} ====="
  echo "+ $*"
  set +e
  "$@" 2>&1 | tee "${outfile}"
  local rc=${PIPESTATUS[0]}
  set -u
  echo "===== ${label} exit=${rc} ====="
  return "${rc}"
}

run_step_with_stdin() {
  local label="$1"
  local outfile="$2"
  shift 2
  echo
  echo "===== ${label} ====="
  set +e
  "$@" 2>&1 | tee "${outfile}"
  local rc=${PIPESTATUS[0]}
  set -u
  echo "===== ${label} exit=${rc} ====="
  return "${rc}"
}

candidate_run_no_artifact_precondition() {
  local payload_path="$1"
  python3 -c "import json, sys; from pathlib import Path; text=Path(sys.argv[1]).read_text(encoding='utf-8').strip(); payload=json.loads(text[text.find('{'):text.rfind('}')+1] if not text.lstrip().startswith('{') else text); completion=payload.get('mvp_completion') if isinstance(payload.get('mvp_completion'), dict) else {}; checks=[payload.get('status') == 'candidate_run_cycle_precondition_failed', completion.get('status') == 'candidate_mvp_no_artifact_candidate', payload.get('stopped_reason') == 'no_artifact_candidate', payload.get('mutating_actions_executed') is False, payload.get('download_performed') is False, payload.get('verification_performed') is False, payload.get('migration_performed') is False, payload.get('adoption_performed') is False]; raise SystemExit(0 if all(checks) else 1)" "${payload_path}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--version)
      [[ $# -ge 2 ]] || { echo "ERROR: --version requires a value" >&2; exit 2; }
      version_arg="$2"
      shift 2
      ;;
    --version=*) version_arg="${1#*=}"; shift ;;
    --target-version)
      [[ $# -ge 2 ]] || { echo "ERROR: --target-version requires a value" >&2; exit 2; }
      target_version_arg="$2"
      shift 2
      ;;
    --target-version=*) target_version_arg="${1#*=}"; shift ;;
    --pb-cmd)
      [[ $# -ge 2 ]] || { echo "ERROR: --pb-cmd requires a value" >&2; exit 2; }
      pb_cmd_arg="$2"
      shift 2
      ;;
    --pb-cmd=*) pb_cmd_arg="${1#*=}"; shift ;;
    --release-log-dir)
      [[ $# -ge 2 ]] || { echo "ERROR: --release-log-dir requires a value" >&2; exit 2; }
      release_log_root="$2"
      shift 2
      ;;
    --release-log-dir=*) release_log_root="${1#*=}"; shift ;;
    --test-timeout)
      [[ $# -ge 2 ]] || { echo "ERROR: --test-timeout requires seconds" >&2; exit 2; }
      test_timeout_seconds="$2"
      shift 2
      ;;
    --test-timeout=*) test_timeout_seconds="${1#*=}"; shift ;;
    --skip-protocol-smoke) skip_protocol_smoke=1; shift ;;
    --skip-artifact-intake) skip_artifact_intake=1; shift ;;
    --skip-candidate-run) skip_candidate_run=1; shift ;;
    --require-candidate-mvp-complete) require_candidate_mvp_complete=1; shift ;;
    --complete-candidate-mvp) complete_candidate_mvp=1; require_candidate_mvp_complete=1; shift ;;
    --require-real-candidate-mvp) require_real_candidate_mvp=1; shift ;;
    --candidate-mvp-max-steps)
      [[ $# -ge 2 ]] || { echo "ERROR: --candidate-mvp-max-steps requires a value" >&2; exit 2; }
      candidate_mvp_max_steps="$2"
      shift 2
      ;;
    --candidate-mvp-max-steps=*) candidate_mvp_max_steps="${1#*=}"; shift ;;
    --candidate-run-step-timeout)
      [[ $# -ge 2 ]] || { echo "ERROR: --candidate-run-step-timeout requires seconds" >&2; exit 2; }
      candidate_run_step_timeout_seconds="$2"
      shift 2
      ;;
    --candidate-run-step-timeout=*) candidate_run_step_timeout_seconds="${1#*=}"; shift ;;
    --skip-tests) skip_tests=1; shift ;;
    --skip-zip-hygiene) skip_zip_hygiene=1; shift ;;
    --adopt-if-accepted) adopt_if_accepted=1; shift ;;
    --require-adopted-baseline) require_adopted_baseline=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "${version_arg}" ]]; then
  [[ -f VERSION ]] || { echo "ERROR: VERSION file not found and --version not supplied" >&2; exit 2; }
  version_arg="$(<VERSION)"
fi
version="$(normalize_version "${version_arg}")" || { echo "ERROR: invalid version: ${version_arg}" >&2; exit 2; }
target_version="${target_version_arg}"
if [[ -z "${target_version}" ]]; then
  target_version="$(next_normal_version "${version}")" || { echo "ERROR: could not derive next version from ${version}" >&2; exit 2; }
else
  target_version="$(normalize_version "${target_version}")" || { echo "ERROR: invalid target version: ${target_version_arg}" >&2; exit 2; }
fi
pb_cmd="$(select_pb_cmd)" || exit 2

if [[ "${complete_candidate_mvp}" -eq 1 && "${skip_candidate_run}" -eq 1 ]]; then
  echo "ERROR: --complete-candidate-mvp cannot be combined with --skip-candidate-run" >&2
  exit 2
fi
if ! [[ "${candidate_mvp_max_steps}" =~ ^[0-9]+$ ]] || [[ "${candidate_mvp_max_steps}" -lt 1 ]]; then
  echo "ERROR: --candidate-mvp-max-steps must be a positive integer: ${candidate_mvp_max_steps}" >&2
  exit 2
fi
if ! python3 - "${candidate_run_step_timeout_seconds}" <<'PYTIMEOUT'
import sys
try:
    value = float(sys.argv[1])
except ValueError:
    raise SystemExit(1)
raise SystemExit(0 if value > 0 else 1)
PYTIMEOUT
then
  echo "ERROR: --candidate-run-step-timeout must be a positive number: ${candidate_run_step_timeout_seconds}" >&2
  exit 2
fi

release_log_dir="${release_log_root%/}/${version}"
mkdir -p "${release_log_dir}"
session_log="${release_log_dir}/post_release_validation.${version}.session.log"
summary_json="${release_log_dir}/post_release_validation.${version}.summary.json"

# Keep the caller's terminal unaffected: exec is scoped to this script process.
# Tests and other subprocess-capture harnesses can disable process-substitution
# teeing to avoid stdout-pipe lifecycle hangs while still writing step artifacts.
if [[ "${POST_RELEASE_VALIDATION_DISABLE_SESSION_TEE:-0}" == "1" ]]; then
  : > "${session_log}"
else
  exec > >(tee -a "${session_log}") 2>&1
fi

echo "== promptbranch post-release validation =="
echo "repo_root:        $(pwd)"
echo "version:          ${version}"
echo "target_version:   ${target_version}"
echo "release_logs:     ${release_log_dir}"
echo "session_log:      ${session_log}"
echo "pb_cmd:           ${pb_cmd}"
echo "test_timeout:     ${test_timeout_seconds}"
echo "skip_protocol:    ${skip_protocol_smoke}"
echo "skip_intake:      ${skip_artifact_intake}"
echo "skip_candidate_run: ${skip_candidate_run}"
echo "require_candidate_mvp_complete: ${require_candidate_mvp_complete}"
echo "complete_candidate_mvp: ${complete_candidate_mvp}"
echo "candidate_mvp_max_steps: ${candidate_mvp_max_steps}"
echo "candidate_run_step_timeout: ${candidate_run_step_timeout_seconds}"
echo "skip_tests:       ${skip_tests}"
echo "skip_zip_hygiene: ${skip_zip_hygiene}"
echo "adopt_if_accepted: ${adopt_if_accepted}"
echo "require_adopted:   ${require_adopted_baseline}"

failures=0
rc_current=0
rc_current_semantic=0
rc_protocol=0
rc_intake=0
rc_candidate_run=0
rc_test_full=0
rc_test_report=0
rc_zip_hygiene=0
rc_adopt=0
rc_adopt_semantic=0
adopt_performed=0
adopt_semantic_performed=0
protocol_phase="not_run"
intake_phase="not_run"
candidate_run_phase="not_run"

artifact_current_log="${release_log_dir}/pb_artifact_current.${version}.json"
artifact_current_semantic_log="${release_log_dir}/pb_artifact_current.${version}.semantic.json"
run_step "artifact current" "${artifact_current_log}" "${pb_cmd}" artifact current --json || { rc_current=$?; failures=$((failures + 1)); }
if [[ "${rc_current}" -eq 0 ]]; then
  echo
  echo "===== artifact current semantic check ====="
  set +e
  python3 - "${artifact_current_log}" "${version}" > "${artifact_current_semantic_log}" <<'PYSEMANTIC'
import json
import sys
from pathlib import Path

artifact_current_log = Path(sys.argv[1])
expected_version = sys.argv[2]
result = {
    "ok": False,
    "action": "artifact_current_semantic_check",
    "expected_version": expected_version,
    "checked_fields": {
        "runtime.version": None,
        "state.artifact_version": None,
        "state.source_version": None,
        "registry_current.version": None,
    },
    "mismatches": [],
    "missing_fields": [],
}
try:
    payload = json.loads(artifact_current_log.read_text(encoding="utf-8"))
except Exception as exc:  # noqa: BLE001 - shell diagnostic path
    result["error"] = f"artifact_current_json_unreadable: {exc}"
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(1)

field_paths = {
    "runtime.version": ("runtime", "version"),
    "state.artifact_version": ("state", "artifact_version"),
    "state.source_version": ("state", "source_version"),
    "registry_current.version": ("registry_current", "version"),
}
for label, path in field_paths.items():
    current = payload
    for segment in path:
        if not isinstance(current, dict) or segment not in current:
            current = None
            break
        current = current[segment]
    result["checked_fields"][label] = current
    if current is None:
        result["missing_fields"].append(label)
    elif current != expected_version:
        result["mismatches"].append({"field": label, "actual": current, "expected": expected_version})

result["ok"] = not result["missing_fields"] and not result["mismatches"]
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
PYSEMANTIC
  rc_current_semantic=$?
  set -u
  cat "${artifact_current_semantic_log}"
  if [[ "${rc_current_semantic}" -ne 0 && "${require_adopted_baseline}" -eq 0 ]]; then
    echo "artifact current semantic check is diagnostic: baseline does not yet match ${version}; adoption is pending but validation may continue"
  fi
  echo "===== artifact current semantic check exit=${rc_current_semantic} ====="
  if [[ "${rc_current_semantic}" -ne 0 && "${require_adopted_baseline}" -eq 1 ]]; then
    failures=$((failures + 1))
  fi
else
  printf '{"ok": false, "status": "skipped", "reason": "artifact_current_step_failed"}
' > "${artifact_current_semantic_log}"
fi

protocol_log="${release_log_dir}/pb_ask_protocol_smoke.${version}.json"
intake_log="${release_log_dir}/pb_artifact_intake_dry_run.${version}.json"
candidate_run_log="${release_log_dir}/pb_artifact_candidate_run.${version}.json"

run_protocol_smoke_step() {
  local phase="$1"
  protocol_phase="${phase}"
  if [[ "${skip_protocol_smoke}" -eq 0 ]]; then
    run_step "protocol smoke (${phase})" "${protocol_log}" \
      "${pb_cmd}" ask "Protocol smoke only. Return a valid promptbranch.ask.reply envelope with status no_artifact. Do not create a ZIP." \
        --protocol \
        --from-current-baseline \
        --target-version "${target_version}" \
        --parse-reply \
        --protocol-timeout-seconds "${protocol_timeout_seconds}" \
        --protocol-fresh-turn-timeout-seconds "${fresh_turn_timeout_seconds}" \
        --protocol-fresh-turn-poll-seconds "${fresh_turn_poll_seconds}" \
        --json || { rc_protocol=$?; failures=$((failures + 1)); }
  else
    printf '{"ok": true, "status": "skipped", "phase": "%s"}\n' "${phase}" > "${protocol_log}"
  fi
}

run_artifact_intake_step() {
  local phase="$1"
  intake_phase="${phase}"
  if [[ "${skip_artifact_intake}" -eq 0 ]]; then
    if [[ "${skip_protocol_smoke}" -eq 0 && "${rc_protocol}" -ne 0 ]]; then
      printf '{"ok": true, "status": "skipped_due_to_protocol_smoke_failure", "phase": "%s"}\n' "${phase}" > "${intake_log}"
      echo "artifact intake dry-run skipped because protocol smoke failed"
      return 0
    fi
    run_step "artifact intake dry-run (${phase})" "${intake_log}" \
      "${pb_cmd}" artifact intake --from-last-answer --dry-run --json || { rc_intake=$?; failures=$((failures + 1)); }
  else
    printf '{"ok": true, "status": "skipped", "phase": "%s"}\n' "${phase}" > "${intake_log}"
  fi
}

run_artifact_candidate_run_step() {
  local phase="$1"
  candidate_run_phase="${phase}"
  if [[ "${skip_candidate_run}" -eq 0 ]]; then
    if [[ "${skip_protocol_smoke}" -eq 0 && "${rc_protocol}" -ne 0 ]]; then
      printf '{"ok": true, "status": "skipped_due_to_protocol_smoke_failure", "phase": "%s"}\n' "${phase}" > "${candidate_run_log}"
      echo "artifact candidate-run plan skipped because protocol smoke failed"
      return 0
    fi
    if [[ "${skip_artifact_intake}" -eq 0 && "${rc_intake}" -ne 0 ]]; then
      printf '{"ok": true, "status": "skipped_due_to_artifact_intake_failure", "phase": "%s"}\n' "${phase}" > "${candidate_run_log}"
      echo "artifact candidate-run plan skipped because artifact intake dry-run failed"
      return 0
    fi
    local candidate_run_args=(artifact candidate-run --json)
    local candidate_run_label="artifact candidate-run plan (${phase})"
    if [[ "${complete_candidate_mvp}" -eq 1 ]]; then
      candidate_run_args=(artifact candidate-run --execute-until-blocked --max-steps "${candidate_mvp_max_steps}" --step-timeout "${candidate_run_step_timeout_seconds}" --require-complete --json)
      if [[ "${require_real_candidate_mvp}" -eq 1 ]]; then
        candidate_run_args+=(--require-real-candidate)
      fi
      candidate_run_label="artifact candidate-run complete-candidate-mvp (${phase})"
    elif [[ "${require_candidate_mvp_complete}" -eq 1 ]]; then
      candidate_run_args=(artifact candidate-run --require-complete --json)
      if [[ "${require_real_candidate_mvp}" -eq 1 ]]; then
        candidate_run_args+=(--require-real-candidate)
      fi
      candidate_run_label="artifact candidate-run require-complete (${phase})"
    fi
    if [[ "${adopt_if_accepted}" -eq 1 && "${phase}" == post_adoption* && ( "${complete_candidate_mvp}" -eq 1 || "${require_candidate_mvp_complete}" -eq 1 ) ]]; then
      candidate_run_args+=(--version "${version}")
    fi
    set +e
    run_step "${candidate_run_label}" "${candidate_run_log}" \
      "${pb_cmd}" "${candidate_run_args[@]}"
    local candidate_rc=$?
    set -u
    if [[ "${candidate_rc}" -ne 0 ]]; then
      if [[ "${complete_candidate_mvp}" -eq 1 && "${require_real_candidate_mvp}" -eq 0 ]] && candidate_run_no_artifact_precondition "${candidate_run_log}"; then
        echo "artifact candidate-run complete-candidate-mvp stopped at no_artifact precondition; treating this as a valid no-candidate terminal state for post-release validation"
        rc_candidate_run=0
      else
        rc_candidate_run="${candidate_rc}"
        failures=$((failures + 1))
      fi
    else
      rc_candidate_run=0
    fi
  else
    printf '{"ok": true, "status": "skipped", "phase": "%s"}\n' "${phase}" > "${candidate_run_log}"
  fi
}


if [[ "${adopt_if_accepted}" -eq 0 ]]; then
  run_protocol_smoke_step "pre_adoption"
  run_artifact_intake_step "pre_adoption"
  run_artifact_candidate_run_step "pre_adoption"
else
  echo
  echo "===== protocol smoke deferred ====="
  echo "--adopt-if-accepted defers baseline-dependent protocol smoke until after adoption so --from-current-baseline can resolve to ${version}."
  echo '{"ok": true, "status": "deferred_until_after_adopt", "reason": "adopt_if_accepted_requires_post_adoption_baseline"}' > "${protocol_log}"
  echo '{"ok": true, "status": "deferred_until_after_protocol_smoke", "reason": "adopt_if_accepted_requires_post_adoption_protocol_smoke"}' > "${intake_log}"
  echo '{"ok": true, "status": "deferred_until_after_artifact_intake", "reason": "candidate_run_plan_uses_post_adoption_lifecycle_state"}' > "${candidate_run_log}"
fi

test_full_log="${release_log_dir}/pb_test.full.${version}.log"
test_report_log="${release_log_dir}/pb_test.full.${version}.report.json"
if [[ "${skip_tests}" -eq 0 ]]; then
  if command -v timeout >/dev/null 2>&1; then
    run_step "test full" "${test_full_log}" timeout "${test_timeout_seconds}" "${pb_cmd}" test full --json || { rc_test_full=$?; failures=$((failures + 1)); }
  else
    run_step "test full" "${test_full_log}" "${pb_cmd}" test full --json || { rc_test_full=$?; failures=$((failures + 1)); }
  fi
  run_step "test report" "${test_report_log}" "${pb_cmd}" test report "${test_full_log}" --json || { rc_test_report=$?; failures=$((failures + 1)); }
else
  echo '{"ok": true, "status": "skipped"}' > "${test_full_log}"
  echo '{"ok": true, "status": "skipped"}' > "${test_report_log}"
fi

zip_hygiene_log="${release_log_dir}/zip_hygiene.${version}.json"
if [[ "${skip_zip_hygiene}" -eq 0 ]]; then
  artifact_zip="${project_name}_${version}.zip"
  set +e
  python3 - "${artifact_zip}" > "${zip_hygiene_log}" <<'PY'
import json
import sys
import zipfile
from pathlib import Path

zip_path = Path(sys.argv[1])
patterns = (
    ".pb_profile/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
)
suffixes = (".pyc", ".pyo", ".log", ".tar.gz")
prefixes = ("session_", "pb_test", "pb_ask_protocol_smoke")
contains = ("/session_", "/pb_test", "/pb_ask_protocol_smoke")
result = {
    "ok": False,
    "action": "zip_hygiene",
    "zip_path": str(zip_path),
    "exists": zip_path.is_file(),
    "testzip": None,
    "entry_count": 0,
    "bad_entry_count": 0,
    "bad_entries": [],
    "wrapper_folder": None,
}
if zip_path.is_file():
    with zipfile.ZipFile(zip_path) as archive:
        result["testzip"] = archive.testzip()
        names = archive.namelist()
        result["entry_count"] = len(names)
        roots = sorted({name.split("/")[0] for name in names if name.strip("/")})
        result["wrapper_folder"] = len(roots) == 1 and all("/" in name for name in names)
        bad = []
        for name in names:
            stripped = name.strip("/")
            if any(stripped == pattern.strip("/") or stripped.startswith(pattern) for pattern in patterns):
                bad.append(name)
            elif any(stripped.endswith(suffix) for suffix in suffixes):
                bad.append(name)
            elif any(stripped.startswith(prefix) for prefix in prefixes):
                bad.append(name)
            elif any(token in stripped for token in contains):
                bad.append(name)
            elif stripped.endswith(".zip"):
                bad.append(name)
        result["bad_entries"] = sorted(set(bad))
        result["bad_entry_count"] = len(result["bad_entries"])
        result["ok"] = result["testzip"] is None and not result["wrapper_folder"] and result["bad_entry_count"] == 0
print(json.dumps(result, indent=2, sort_keys=True))
PY
  rc_zip_hygiene=$?
  set -u
  cat "${zip_hygiene_log}"
  if [[ "${rc_zip_hygiene}" -ne 0 ]]; then
    failures=$((failures + 1))
  elif ! python3 - "${zip_hygiene_log}" <<'PY'
import json, sys
payload=json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if payload.get("ok") is True else 1)
PY
  then
    rc_zip_hygiene=1
    failures=$((failures + 1))
  fi
else
  echo '{"ok": true, "status": "skipped"}' > "${zip_hygiene_log}"
fi


if [[ "${adopt_if_accepted}" -eq 1 && "${failures}" -eq 0 ]]; then
  echo
  echo "===== adopt if accepted ====="
  artifact_zip="${project_name}_${version}.zip"
  adopt_log="${release_log_dir}/pb_artifact_adopt.${version}.json"
  adopt_current_log="${release_log_dir}/pb_artifact_current_after_adopt.${version}.json"
  adopt_semantic_log="${release_log_dir}/pb_artifact_current_after_adopt.${version}.semantic.json"
  if [[ ! -f "${artifact_zip}" ]]; then
    printf '{"ok": false, "status": "artifact_zip_missing", "artifact_zip": "%s"}
' "${artifact_zip}" > "${adopt_log}"
    cat "${adopt_log}"
    rc_adopt=1
    failures=$((failures + 1))
  else
    adopt_performed=1
    run_step "artifact adopt" "${adopt_log}" \
      "${pb_cmd}" artifact adopt "${artifact_zip}" --from-project-source --json || { rc_adopt=$?; failures=$((failures + 1)); }
  fi
  if [[ "${rc_adopt}" -eq 0 ]]; then
    run_step "artifact current after adopt" "${adopt_current_log}" "${pb_cmd}" artifact current --json || { rc_adopt_semantic=$?; failures=$((failures + 1)); }
    if [[ "${rc_adopt_semantic}" -eq 0 ]]; then
      adopt_semantic_performed=1
      set +e
      python3 - "${adopt_current_log}" "${version}" > "${adopt_semantic_log}" <<'PYSEMANTIC2'
import json
import sys
from pathlib import Path

artifact_current_log = Path(sys.argv[1])
expected_version = sys.argv[2]
result = {
    "ok": False,
    "action": "artifact_current_semantic_check_after_adopt",
    "expected_version": expected_version,
    "checked_fields": {
        "runtime.version": None,
        "state.artifact_version": None,
        "state.source_version": None,
        "registry_current.version": None,
    },
    "mismatches": [],
    "missing_fields": [],
}
try:
    payload = json.loads(artifact_current_log.read_text(encoding="utf-8"))
except Exception as exc:  # noqa: BLE001 - shell diagnostic path
    result["error"] = f"artifact_current_json_unreadable: {exc}"
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(1)
field_paths = {
    "runtime.version": ("runtime", "version"),
    "state.artifact_version": ("state", "artifact_version"),
    "state.source_version": ("state", "source_version"),
    "registry_current.version": ("registry_current", "version"),
}
for label, path in field_paths.items():
    current = payload
    for segment in path:
        if not isinstance(current, dict) or segment not in current:
            current = None
            break
        current = current[segment]
    result["checked_fields"][label] = current
    if current is None:
        result["missing_fields"].append(label)
    elif current != expected_version:
        result["mismatches"].append({"field": label, "actual": current, "expected": expected_version})
result["ok"] = not result["missing_fields"] and not result["mismatches"]
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["ok"] else 1)
PYSEMANTIC2
      rc_adopt_semantic=$?
      set -u
      cat "${adopt_semantic_log}"
      echo "===== artifact current after adopt semantic check exit=${rc_adopt_semantic} ====="
      if [[ "${rc_adopt_semantic}" -ne 0 ]]; then
        failures=$((failures + 1))
      fi
    fi
  fi
  if [[ "${failures}" -eq 0 ]]; then
    run_protocol_smoke_step "post_adoption"
    run_artifact_intake_step "post_adoption"
    run_artifact_candidate_run_step "post_adoption"
  else
    echo
    echo "===== post-adoption protocol smoke skipped ====="
    echo "failures_before_post_adoption_protocol=${failures}"
    if [[ "${skip_protocol_smoke}" -eq 0 && "${protocol_phase}" == "not_run" ]]; then
      echo '{"ok": true, "status": "skipped_due_to_pre_protocol_failure", "phase": "post_adoption"}' > "${protocol_log}"
    fi
    if [[ "${skip_artifact_intake}" -eq 0 && "${intake_phase}" == "not_run" ]]; then
      echo '{"ok": true, "status": "skipped_due_to_pre_protocol_failure", "phase": "post_adoption"}' > "${intake_log}"
    fi
    if [[ "${skip_candidate_run}" -eq 0 && "${candidate_run_phase}" == "not_run" ]]; then
      echo '{"ok": true, "status": "skipped_due_to_pre_protocol_failure", "phase": "post_adoption"}' > "${candidate_run_log}"
    fi
  fi
else
  echo
  echo "===== adopt if accepted skipped ====="
  echo "adopt_if_accepted=${adopt_if_accepted} failures_before_adopt=${failures}"
fi

python3 - \
  "${summary_json}" \
  "${version}" \
  "${target_version}" \
  "${release_log_dir}" \
  "${session_log}" \
  "${failures}" \
  "${rc_current}" \
  "${rc_current_semantic}" \
  "${rc_protocol}" \
  "${rc_intake}" \
  "${rc_candidate_run}" \
  "${rc_test_full}" \
  "${rc_test_report}" \
  "${rc_zip_hygiene}" \
  "${rc_adopt}" \
  "${rc_adopt_semantic}" \
  "${adopt_if_accepted}" \
  "${require_adopted_baseline}" \
  "${require_candidate_mvp_complete}" \
  "${complete_candidate_mvp}" \
  "${require_real_candidate_mvp}" \
  "${candidate_mvp_max_steps}" \
  "${candidate_run_step_timeout_seconds}" \
  "${adopt_performed}" \
  "${adopt_semantic_performed}" \
  "${protocol_phase}" \
  "${intake_phase}" \
  "${candidate_run_phase}" \
  "${candidate_run_log}" <<'PY'
import json
import sys
from pathlib import Path

(
    out,
    version,
    target_version,
    release_log_dir,
    session_log,
    failures,
    rc_current,
    rc_current_semantic,
    rc_protocol,
    rc_intake,
    rc_candidate_run,
    rc_test_full,
    rc_test_report,
    rc_zip_hygiene,
    rc_adopt,
    rc_adopt_semantic,
    adopt_if_accepted,
    require_adopted_baseline,
    require_candidate_mvp_complete,
    complete_candidate_mvp,
    require_real_candidate_mvp,
    candidate_mvp_max_steps,
    candidate_run_step_timeout_seconds,
    adopt_performed,
    adopt_semantic_performed,
    protocol_phase,
    intake_phase,
    candidate_run_phase,
    candidate_run_log,
) = sys.argv[1:]
def _load_candidate_run_summary(path: str) -> dict:
    payload: dict = {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return {}
    text = text.strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                payload = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                payload = {}
    if not isinstance(payload, dict):
        return {}
    completion = payload.get("mvp_completion") if isinstance(payload.get("mvp_completion"), dict) else {}
    return {
        "status": payload.get("status"),
        "mode": payload.get("mode"),
        "mvp_complete": payload.get("mvp_complete"),
        "mvp_completion_status": completion.get("status"),
        "mvp_completion_ok": completion.get("ok"),
        "recommended_next_kind": (payload.get("recommended_next_command") or {}).get("kind") if isinstance(payload.get("recommended_next_command"), dict) else None,
        "mutating_actions_executed": payload.get("mutating_actions_executed"),
        "execute_until_blocked": payload.get("execute_until_blocked"),
        "cycle_step_count": payload.get("cycle_step_count"),
        "stopped_reason": payload.get("stopped_reason"),
        "download_performed": payload.get("download_performed"),
        "verification_performed": payload.get("verification_performed"),
        "migration_performed": payload.get("migration_performed"),
        "candidate_test_performed": payload.get("candidate_test_performed"),
        "adoption_performed": payload.get("adoption_performed"),
    }

candidate_run_summary = _load_candidate_run_summary(candidate_run_log)

summary = {
    "ok": int(failures) == 0,
    "action": "post_release_validation",
    "version": version,
    "target_version": target_version,
    "release_log_dir": release_log_dir,
    "session_log": session_log,
    "summary_path": out,
    "failure_count": int(failures),
    "adopt_if_accepted": bool(int(adopt_if_accepted)),
    "require_adopted_baseline": bool(int(require_adopted_baseline)),
    "require_candidate_mvp_complete": bool(int(require_candidate_mvp_complete)),
    "complete_candidate_mvp": bool(int(complete_candidate_mvp)),
    "require_real_candidate_mvp": bool(int(require_real_candidate_mvp)),
    "candidate_mvp_max_steps": int(candidate_mvp_max_steps),
    "candidate_run_step_timeout_seconds": float(candidate_run_step_timeout_seconds),
    "steps": {
        "artifact_current": {"rc": int(rc_current)},
        "artifact_current_semantic": {"rc": int(rc_current_semantic)},
        "protocol_smoke": {"rc": int(rc_protocol), "phase": protocol_phase},
        "artifact_intake_dry_run": {"rc": int(rc_intake), "phase": intake_phase},
        "artifact_candidate_run_plan": {
            "rc": int(rc_candidate_run),
            "phase": candidate_run_phase,
            "require_complete": bool(int(require_candidate_mvp_complete)),
            "require_real_candidate": bool(int(require_real_candidate_mvp)),
            **candidate_run_summary,
        },
        "test_full": {"rc": int(rc_test_full)},
        "test_report": {"rc": int(rc_test_report)},
        "zip_hygiene": {"rc": int(rc_zip_hygiene)},
        "artifact_adopt": {"rc": int(rc_adopt), "enabled": bool(int(adopt_if_accepted)), "performed": bool(int(adopt_performed))},
        "artifact_current_after_adopt_semantic": {"rc": int(rc_adopt_semantic), "enabled": bool(int(adopt_if_accepted)), "performed": bool(int(adopt_semantic_performed))},
    },
}
Path(out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2, sort_keys=True))
PY

if [[ "${failures}" -ne 0 ]]; then
  echo "post-release validation failed: ${failures} failing step(s)" >&2
  exit 1
fi

echo "post-release validation passed"
