#!/usr/bin/env bash
set -Euo pipefail

# Final Artifact Intake MVP gate for chatgpt_claudecode_workflow.
#
# This is a thin operator wrapper around the native Promptbranch artifact
# candidate runner. The native command is the sole lifecycle implementation:
#
#   pb artifact candidate-run --execute-until-blocked ...
#
# The script intentionally does not auto-adopt unless --accept-if-green is
# passed explicitly.

version=""
target_version=""
repo_root="$(pwd -P)"
pb_python="${PB_PYTHON:-}"
pb_cli="${repo_root}/promptbranch_cli.py"
release_log_dir=""
candidate_mvp_max_steps="6"
candidate_run_step_timeout="600"
require_real_candidate_mvp=0
accept_if_green=0
profile="smoke"

usage() {
  cat <<USAGE
Usage:
  $(basename "$0") --version VERSION --target-version VERSION [options]

Runs the final Artifact Intake MVP validation gate by delegating to the native
Promptbranch candidate lifecycle command:

  pb artifact candidate-run \
    --execute-until-blocked \
    --require-complete \
    --profile smoke \
    --json

Required proof when --require-real-candidate-mvp is used:
  - download_performed=true
  - verification_performed=true
  - migration_performed=true
  - candidate_test_performed=true

Options:
  -v, --version VERSION
      --target-version VERSION
      PB_PYTHON must name the exact Promptbranch launcher Python.
      --release-log-dir DIR
      --candidate-mvp-max-steps N
      --candidate-run-step-timeout SEC
      --profile smoke|full
      --require-real-candidate-mvp
          Require candidate-run to prove a real downloaded, verified, migrated,
          and tested release candidate.
      --accept-if-green
          Explicitly allow candidate-run to adopt after the candidate test gate
          passes. Without this flag adoption is forbidden.
  -h, --help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -v|--version)
      [[ $# -ge 2 ]] || { echo "ERROR: $1 requires a value" >&2; exit 2; }
      version="$2"
      shift 2
      ;;
    --version=*) version="${1#*=}"; shift ;;
    --target-version)
      [[ $# -ge 2 ]] || { echo "ERROR: --target-version requires a value" >&2; exit 2; }
      target_version="$2"
      shift 2
      ;;
    --target-version=*) target_version="${1#*=}"; shift ;;
    --release-log-dir)
      [[ $# -ge 2 ]] || { echo "ERROR: --release-log-dir requires a value" >&2; exit 2; }
      release_log_dir="$2"
      shift 2
      ;;
    --release-log-dir=*) release_log_dir="${1#*=}"; shift ;;
    --candidate-mvp-max-steps)
      [[ $# -ge 2 ]] || { echo "ERROR: --candidate-mvp-max-steps requires a value" >&2; exit 2; }
      candidate_mvp_max_steps="$2"
      shift 2
      ;;
    --candidate-mvp-max-steps=*) candidate_mvp_max_steps="${1#*=}"; shift ;;
    --candidate-run-step-timeout|--step-timeout)
      [[ $# -ge 2 ]] || { echo "ERROR: $1 requires a value" >&2; exit 2; }
      candidate_run_step_timeout="$2"
      shift 2
      ;;
    --candidate-run-step-timeout=*|--step-timeout=*) candidate_run_step_timeout="${1#*=}"; shift ;;
    --profile)
      [[ $# -ge 2 ]] || { echo "ERROR: --profile requires a value" >&2; exit 2; }
      profile="$2"
      shift 2
      ;;
    --profile=*) profile="${1#*=}"; shift ;;
    --require-real-candidate-mvp)
      require_real_candidate_mvp=1
      shift
      ;;
    --accept-if-green)
      accept_if_green=1
      shift
      ;;
    --adopt-if-accepted|--complete-candidate-mvp|--require-candidate-mvp-complete)
      echo "ERROR: $(basename "$0") delegates to candidate-run directly; do not pass $1 explicitly" >&2
      exit 2
      ;;
    --skip-candidate-run|--require-adopted-baseline)
      echo "ERROR: $1 conflicts with final Artifact Intake MVP completion validation" >&2
      exit 2
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${pb_python}" || "${pb_python}" != /* || ! -x "${pb_python}" ]]; then
  echo "ERROR: PB_PYTHON must be the absolute executable Promptbranch launcher Python" >&2
  exit 2
fi
if [[ ! -f "${pb_cli}" ]]; then
  echo "ERROR: canonical Promptbranch CLI not found: ${pb_cli}" >&2
  exit 2
fi

if [[ -z "${version}" ]]; then
  echo "ERROR: --version is required" >&2
  exit 2
fi
if [[ -z "${target_version}" ]]; then
  echo "ERROR: --target-version is required" >&2
  exit 2
fi
if [[ "${profile}" != "smoke" && "${profile}" != "full" ]]; then
  echo "ERROR: --profile must be smoke or full: ${profile}" >&2
  exit 2
fi
case "${candidate_mvp_max_steps}" in
  ''|*[!0-9]*) echo "ERROR: --candidate-mvp-max-steps must be a positive integer: ${candidate_mvp_max_steps}" >&2; exit 2 ;;
esac
if [[ "${candidate_mvp_max_steps}" -lt 1 ]]; then
  echo "ERROR: --candidate-mvp-max-steps must be >= 1" >&2
  exit 2
fi
"${pb_python}" - <<'PY' "${candidate_run_step_timeout}"
import sys
try:
    value = float(sys.argv[1])
except Exception:
    raise SystemExit(2)
if value <= 0:
    raise SystemExit(2)
PY
if [[ $? -ne 0 ]]; then
  echo "ERROR: --candidate-run-step-timeout must be a positive number: ${candidate_run_step_timeout}" >&2
  exit 2
fi

if [[ -z "${release_log_dir}" ]]; then
  release_log_dir=".pb_profile/release_logs/${version}"
fi
mkdir -p "${release_log_dir}"

candidate_run_log="${release_log_dir}/finalize_artifact_intake_mvp.${version}.candidate_run.json"
summary_log="${release_log_dir}/finalize_artifact_intake_mvp.${version}.summary.json"

candidate_run_args=(
  artifact candidate-run
  --execute-until-blocked
  --max-steps "${candidate_mvp_max_steps}"
  --step-timeout "${candidate_run_step_timeout}"
  --require-complete
  --profile "${profile}"
  --json
)
if [[ "${require_real_candidate_mvp}" -eq 1 ]]; then
  candidate_run_args+=(--require-real-candidate)
fi
if [[ "${accept_if_green}" -eq 1 ]]; then
  candidate_run_args+=(--accept-if-green)
fi

echo "final Artifact Intake MVP validation starting"
echo "version: ${version}"
echo "target_version: ${target_version}"
echo "pb_python: ${pb_python}"
echo "pb_cli: ${pb_cli}"
echo "candidate_run_log: ${candidate_run_log}"
echo "delegated_command: ${pb_python} ${pb_cli} ${candidate_run_args[*]}"

set +e
"${pb_python}" "${pb_cli}" "${candidate_run_args[@]}" > "${candidate_run_log}"
candidate_rc=$?
set -e

"${pb_python}" - <<'PY' "${candidate_run_log}" "${summary_log}" "${version}" "${target_version}" "${require_real_candidate_mvp}" "${accept_if_green}" "${candidate_rc}"
import json
import sys
from pathlib import Path

candidate_run_log = Path(sys.argv[1])
summary_log = Path(sys.argv[2])
version = sys.argv[3]
target_version = sys.argv[4]
require_real = sys.argv[5] == "1"
accept_if_green = sys.argv[6] == "1"
candidate_rc = int(sys.argv[7])

summary = {
    "ok": False,
    "action": "finalize_artifact_intake_mvp",
    "version": version,
    "target_version": target_version,
    "candidate_run_log": str(candidate_run_log),
    "candidate_run_rc": candidate_rc,
    "require_real_candidate_mvp": require_real,
    "accept_if_green": accept_if_green,
    "checks": {},
    "failures": [],
}
try:
    payload = json.loads(candidate_run_log.read_text(encoding="utf-8"))
except Exception as exc:
    summary["status"] = "candidate_run_json_invalid"
    summary["error"] = str(exc)
    summary["failures"].append("candidate_run_json_invalid")
    summary_log.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(1)

summary["candidate_run_status"] = payload.get("status")
summary["candidate_run_ok"] = bool(payload.get("ok"))
summary["candidate_run_mvp_complete"] = bool(payload.get("mvp_complete"))
summary["candidate_run_stopped_reason"] = payload.get("stopped_reason")

checks = {
    "candidate_run_exit_zero": candidate_rc == 0,
    "candidate_run_ok": bool(payload.get("ok")),
    "mvp_complete": bool(payload.get("mvp_complete")),
    "download_performed": bool(payload.get("download_performed")),
    "verification_performed": bool(payload.get("verification_performed")),
    "migration_performed": bool(payload.get("migration_performed")),
    "candidate_test_passed": bool(payload.get("candidate_test_performed")) or bool((payload.get("mvp_completion") or {}).get("candidate_test_passed")),
    "adoption_not_performed_without_explicit_flag": accept_if_green or not bool(payload.get("adoption_performed")),
}
summary["checks"] = checks

for name, ok in checks.items():
    if not ok:
        if name in {"download_performed", "verification_performed", "migration_performed", "candidate_test_passed"} and not require_real:
            continue
        summary["failures"].append(name)

if require_real:
    for name in ["download_performed", "verification_performed", "migration_performed", "candidate_test_passed"]:
        if not checks[name] and name not in summary["failures"]:
            summary["failures"].append(name)

summary["ok"] = not summary["failures"]
summary["status"] = "final_artifact_intake_mvp_passed" if summary["ok"] else "final_artifact_intake_mvp_failed"
summary_log.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary["ok"] else 1)
PY
validation_rc=$?

if [[ ${validation_rc} -eq 0 ]]; then
  echo "final Artifact Intake MVP validation passed"
else
  echo "final Artifact Intake MVP validation failed: see ${summary_log}" >&2
fi
exit "${validation_rc}"
