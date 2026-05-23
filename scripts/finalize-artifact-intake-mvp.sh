#!/usr/bin/env bash
set -Euo pipefail

# Final Artifact Intake MVP gate for chatgpt_claudecode_workflow.
#
# This is an explicit, operator-controlled wrapper around post-release-validation.
# Unlike the normal post-release validation path, this command intentionally asks
# the candidate lifecycle runner to execute existing allowlisted steps until the
# Artifact Intake MVP completion proof is satisfied or a fail-closed blocker is
# reached.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
post_release_validation_script="${POST_RELEASE_VALIDATION_SCRIPT:-${script_dir}/post-release-validation.sh}"

args=()

usage() {
  cat <<USAGE
Usage:
  $(basename "$0") --version VERSION --target-version VERSION [options]

Runs the final Artifact Intake MVP validation gate by delegating to:

  scripts/post-release-validation.sh \
    --adopt-if-accepted \
    --complete-candidate-mvp

This command may execute the existing allowlisted artifact candidate lifecycle
steps through pb artifact candidate-run --execute-until-blocked. It does not add
new mutation behavior; it makes the explicit MVP-finalization mode discoverable
and repeatable.

Options forwarded to post-release-validation.sh:
  -v, --version VERSION
      --target-version VERSION
      --pb-cmd COMMAND
      --release-log-dir DIR
      --test-timeout SEC
      --candidate-mvp-max-steps N
      --candidate-run-step-timeout SEC
      --skip-protocol-smoke
      --skip-artifact-intake
      --skip-tests
      --skip-zip-hygiene
      --require-real-candidate-mvp
  -h, --help

Environment:
  POST_RELEASE_VALIDATION_SCRIPT  Override the post-release-validation script, mainly for tests.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -v|--version|--target-version|--pb-cmd|--release-log-dir|--test-timeout|--candidate-mvp-max-steps|--candidate-run-step-timeout)
      [[ $# -ge 2 ]] || { echo "ERROR: $1 requires a value" >&2; exit 2; }
      args+=("$1" "$2")
      shift 2
      ;;
    --version=*|--target-version=*|--pb-cmd=*|--release-log-dir=*|--test-timeout=*|--candidate-mvp-max-steps=*|--candidate-run-step-timeout=*)
      args+=("$1")
      shift
      ;;
    --skip-protocol-smoke|--skip-artifact-intake|--skip-tests|--skip-zip-hygiene|--require-real-candidate-mvp)
      args+=("$1")
      shift
      ;;
    --adopt-if-accepted|--complete-candidate-mvp|--require-candidate-mvp-complete)
      echo "ERROR: $(basename "$0") adds $1 semantics itself; do not pass $1 explicitly" >&2
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

if [[ ! -x "${post_release_validation_script}" ]]; then
  echo "ERROR: post-release validation script is not executable: ${post_release_validation_script}" >&2
  exit 2
fi

echo "final Artifact Intake MVP validation starting"
echo "post_release_validation_script: ${post_release_validation_script}"

"${post_release_validation_script}" \
  "${args[@]}" \
  --adopt-if-accepted \
  --complete-candidate-mvp

rc=$?
if [[ ${rc} -eq 0 ]]; then
  echo "final Artifact Intake MVP validation passed"
else
  echo "final Artifact Intake MVP validation failed: exit=${rc}" >&2
fi
exit "${rc}"
