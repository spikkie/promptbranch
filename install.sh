#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./install.sh <version> [zip-path]

Strict all-all Promptbranch release gate for a new ZIP release.

Arguments:
  version   Canonical v-prefixed version, for example v0.1.103.10.69
  zip-path  Optional candidate ZIP path. Defaults to:
            $HOME/Downloads/chatgpt_claudecode_workflow-2_<version>.zip

This command installs the candidate ZIP, runs product validation, runs explicit
external ChatGPT live validation, requires live validation to pass, adopts only
if all validation is GO, then prints pb artifact current --all --json evidence.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 64
fi

ver="$1"
case "${ver}" in
  v[0-9]*.[0-9]*.[0-9]*) ;;
  *)
    echo "ERROR: version must be canonical and v-prefixed, got: ${ver}" >&2
    exit 64
    ;;
esac

zip="${2:-$HOME/Downloads/chatgpt_claudecode_workflow-2_${ver}.zip}"

if [[ ! -f "${zip}" ]]; then
  echo "ERROR: candidate ZIP not found: ${zip}" >&2
  exit 66
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${script_dir}"

mkdir -p "${HOME}/tmp"

timeout --foreground 14400 ./chatgpt_claudecode_workflow_release_control.sh \
  --install-from-zip "${zip}" \
  --version "${ver}" \
  --run-all-tests \
  --run-external-live-tests \
  --require-chatgpt-live-validation \
  --adopt-after-validation \
  --skip-docker-logs \
  --prune-release-logs \
  --release-log-keep 12 \
  2>&1 | tee "${HOME}/tmp/release_control.${ver}.full.all-all.adopt.log"

pb artifact current --all --json | tee "${HOME}/tmp/pb_current_after_${ver}.json"
