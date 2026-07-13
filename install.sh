#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./install.sh <version> [zip-path] [--diagnostic-project-source-ab|--diagnostic-library-backing-reupload]

Strict all-all Promptbranch release gate for a new ZIP release.

Arguments:
  version   Canonical v-prefixed version, for example v0.1.103.10.69
  zip-path  Optional candidate transport ZIP path. Its basename may be unique
            and must not define the canonical Project Source identity.
            Defaults to:
            $HOME/Downloads/chatgpt_claudecode_workflow-2_<version>.zip

Default mode installs the candidate ZIP, runs product validation, runs explicit
external ChatGPT live validation, requires live validation to pass, adopts only
if all validation is GO, then prints pb artifact current --all --json evidence.

Diagnostic mode imports/installs/starts the candidate without Git commit, Project
Source upload, tests, or adoption, then runs the disposable legacy-vs-current
Project Source A/B diagnostic.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 3 ]]; then
  usage >&2
  exit 64
fi

ver="$1"
shift
diagnostic_project_source_ab=0
diagnostic_library_backing_reupload=0
zip=""
for arg in "$@"; do
  case "$arg" in
    --diagnostic-project-source-ab) diagnostic_project_source_ab=1 ;;
    --diagnostic-library-backing-reupload) diagnostic_library_backing_reupload=1 ;;
    --*) echo "ERROR: unsupported install option: $arg" >&2; exit 64 ;;
    *)
      if [[ -n "$zip" ]]; then
        echo "ERROR: multiple ZIP paths supplied" >&2
        exit 64
      fi
      zip="$arg"
      ;;
  esac
done
case "${ver}" in
  v[0-9]*.[0-9]*.[0-9]*) ;;
  *)
    echo "ERROR: version must be canonical and v-prefixed, got: ${ver}" >&2
    exit 64
    ;;
esac

zip="${zip:-$HOME/Downloads/chatgpt_claudecode_workflow-2_${ver}.zip}"

if [[ ! -f "${zip}" ]]; then
  echo "ERROR: candidate ZIP not found: ${zip}" >&2
  exit 66
fi

# Validate the transport artifact before delegating to any script contained in
# it. The transport basename is intentionally non-canonical; internal VERSION,
# CRC integrity and the release-control entrypoint are authoritative.
python3 - "${zip}" "${ver}" <<'PYVERIFY'
import sys
import zipfile
from pathlib import Path

zip_path = Path(sys.argv[1]).expanduser().resolve()
expected_version = sys.argv[2]
try:
    with zipfile.ZipFile(zip_path) as archive:
        bad_crc = archive.testzip()
        if bad_crc:
            raise SystemExit(f"ERROR: candidate transport ZIP CRC failure at {bad_crc}")
        names = set(archive.namelist())
        required = {"VERSION", "pyproject.toml", ".gitignore", ".not_to_zip", "chatgpt_claudecode_workflow_release_control.sh"}
        missing = sorted(required - names)
        if missing:
            raise SystemExit("ERROR: candidate transport ZIP missing required root entries: " + ", ".join(missing))
        internal_version = archive.read("VERSION").decode("utf-8").strip()
except zipfile.BadZipFile as exc:
    raise SystemExit(f"ERROR: invalid candidate transport ZIP: {exc}") from exc
if internal_version != expected_version:
    raise SystemExit(
        f"ERROR: candidate transport ZIP VERSION mismatch: expected {expected_version}, got {internal_version}"
    )
print(f"Candidate transport ZIP verified: {zip_path}")
PYVERIFY

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${script_dir}"

mkdir -p "${HOME}/tmp"

if [[ ${diagnostic_library_backing_reupload} -eq 1 ]]; then
  timeout --foreground 14400 ./chatgpt_claudecode_workflow_release_control.sh \
    --install-from-zip "${zip}" \
    --version "${ver}" \
    --skip-commit \
    --skip-source-add \
    --skip-tests \
    --skip-docker-logs \
    --prune-release-logs \
    --release-log-keep 12 \
    2>&1 | tee "${HOME}/tmp/release_control.${ver}.diagnostic-install.log"

  ./scripts/pb-library-backing-reupload-diagnostic.sh \
    --service-base-url "${CHATGPT_SERVICE_BASE_URL:-http://localhost:8000}" \
    | tee "${HOME}/tmp/library_backing_reupload.${ver}.json"
  exit ${PIPESTATUS[0]}
fi

if [[ ${diagnostic_project_source_ab} -eq 1 ]]; then
  timeout --foreground 14400 ./chatgpt_claudecode_workflow_release_control.sh \
    --install-from-zip "${zip}" \
    --version "${ver}" \
    --skip-commit \
    --skip-source-add \
    --skip-tests \
    --skip-docker-logs \
    --prune-release-logs \
    --release-log-keep 12 \
    2>&1 | tee "${HOME}/tmp/release_control.${ver}.diagnostic-install.log"

  ./scripts/pb-project-source-ab-diagnostic.sh \
    --service-base-url "${CHATGPT_SERVICE_BASE_URL:-http://localhost:8000}" \
    | tee "${HOME}/tmp/project_source_ab.${ver}.json"
  exit ${PIPESTATUS[0]}
fi

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
