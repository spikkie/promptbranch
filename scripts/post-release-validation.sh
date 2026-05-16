#!/usr/bin/env bash
set -Euo pipefail

# Run the standard post-release validation sequence for chatgpt_claudecode_workflow.
# This script is intentionally validation-only: it does not adopt artifacts,
# mutate Project Sources, migrate candidates, or advance release state.

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
skip_tests=0
skip_zip_hygiene=0

usage() {
  cat <<USAGE
Usage:
  $(basename "$0") [--version VERSION] [--target-version VERSION] [options]

Runs the standard post-release validation sequence:
  1. promptbranch artifact current --json
  2. protocol smoke ask targeting the next version
  3. artifact intake dry-run from the last validated protocol reply
  4. promptbranch test full/report
  5. release ZIP hygiene check

Options:
  -v, --version VERSION          Release version under validation. Defaults to VERSION file.
      --target-version VERSION   Target version for protocol smoke. Defaults to next normal version.
      --pb-cmd COMMAND           Promptbranch executable. Defaults to promptbranch, then pb.
      --release-log-dir DIR      Release log root. Default: .pb_profile/release_logs.
      --test-timeout SEC         Timeout wrapper for pb test full. Default: ${test_timeout_seconds}.
      --skip-protocol-smoke      Skip pb ask --protocol smoke.
      --skip-artifact-intake     Skip pb artifact intake dry-run.
      --skip-tests               Skip pb test full/report.
      --skip-zip-hygiene         Skip ZIP entry hygiene check.
  -h, --help                     Show this help.

Examples:
  scripts/post-release-validation.sh --version v0.0.222.1 --target-version v0.0.223
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
    --skip-tests) skip_tests=1; shift ;;
    --skip-zip-hygiene) skip_zip_hygiene=1; shift ;;
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
pb_cmd="$(select_pb_cmd)"

release_log_dir="${release_log_root%/}/${version}"
mkdir -p "${release_log_dir}"
session_log="${release_log_dir}/post_release_validation.${version}.session.log"
summary_json="${release_log_dir}/post_release_validation.${version}.summary.json"

# Keep the caller's terminal unaffected: exec is scoped to this script process.
exec > >(tee -a "${session_log}") 2>&1

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
echo "skip_tests:       ${skip_tests}"
echo "skip_zip_hygiene: ${skip_zip_hygiene}"

failures=0
rc_current=0
rc_protocol=0
rc_intake=0
rc_test_full=0
rc_test_report=0
rc_zip_hygiene=0

artifact_current_log="${release_log_dir}/pb_artifact_current.${version}.json"
run_step "artifact current" "${artifact_current_log}" "${pb_cmd}" artifact current --json || { rc_current=$?; failures=$((failures + 1)); }

protocol_log="${release_log_dir}/pb_ask_protocol_smoke.${version}.json"
if [[ "${skip_protocol_smoke}" -eq 0 ]]; then
  run_step "protocol smoke" "${protocol_log}" \
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
  echo '{"ok": true, "status": "skipped"}' > "${protocol_log}"
fi

intake_log="${release_log_dir}/pb_artifact_intake_dry_run.${version}.json"
if [[ "${skip_artifact_intake}" -eq 0 ]]; then
  run_step "artifact intake dry-run" "${intake_log}" \
    "${pb_cmd}" artifact intake --from-last-answer --dry-run --json || { rc_intake=$?; failures=$((failures + 1)); }
else
  echo '{"ok": true, "status": "skipped"}' > "${intake_log}"
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

python3 - \
  "${summary_json}" \
  "${version}" \
  "${target_version}" \
  "${release_log_dir}" \
  "${session_log}" \
  "${failures}" \
  "${rc_current}" \
  "${rc_protocol}" \
  "${rc_intake}" \
  "${rc_test_full}" \
  "${rc_test_report}" \
  "${rc_zip_hygiene}" <<'PY'
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
    rc_protocol,
    rc_intake,
    rc_test_full,
    rc_test_report,
    rc_zip_hygiene,
) = sys.argv[1:]
summary = {
    "ok": int(failures) == 0,
    "action": "post_release_validation",
    "version": version,
    "target_version": target_version,
    "release_log_dir": release_log_dir,
    "session_log": session_log,
    "summary_path": out,
    "failure_count": int(failures),
    "steps": {
        "artifact_current": {"rc": int(rc_current)},
        "protocol_smoke": {"rc": int(rc_protocol)},
        "artifact_intake_dry_run": {"rc": int(rc_intake)},
        "test_full": {"rc": int(rc_test_full)},
        "test_report": {"rc": int(rc_test_report)},
        "zip_hygiene": {"rc": int(rc_zip_hygiene)},
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
