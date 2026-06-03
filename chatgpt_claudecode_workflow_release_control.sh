#!/usr/bin/env bash
set -Eeuo pipefail

# ChatGPT Claude Code Workflow release ZIP / automatic import / commit / install / source-control workflow.
# Run from the repository root: /home/spikkie/git/chatgpt_claudecode_workflow
#
# Version precedence, highest first:
#   1. --version / -v / first positional argument
#   2. PB_RELEASE_VERSION environment variable
#   3. VERSION file in the repo root
#
# This script uses real commands instead of shell aliases:
#   downloaded ZIP -> automatic overwrite import, no Beyond Compare/manual merge
#   ga .    -> git add .
#   gcm ... -> git commit -m ...
#   gp      -> git push
#   zip_it  -> ~/scripts/zip_with_not_to_zip.sh, with Python fallback
#   pbsa    -> promptbranch src add ...
#
# Important fix: ./run_chatgpt_service.sh is started DETACHED by default so this
# workflow does not hang forever on a foreground service process.

project_name="chatgpt_claudecode_workflow"
if [[ -n "${PROMPTBRANCH_RELEASE_WORKFLOW_REPO_ROOT:-}" ]]; then
  repo_root="${PROMPTBRANCH_RELEASE_WORKFLOW_REPO_ROOT}"
else
  repo_root="$(pwd)"
fi
repo_basename="$(basename "${repo_root}")"
# Artifact identity is release-line specific. It can be pinned explicitly or
# derived from --install-from-zip. Defaulting to the repo/worktree basename keeps
# worktree artifact lines such as chatgpt_claudecode_workflow-2_vX.zip stable.
artifact_project_name="${PROMPTBRANCH_ARTIFACT_PROJECT_NAME:-${repo_basename}}"
# Runtime/Docker identity is intentionally single-default per machine.
# Installing from another branch/worktree replaces the active local runtime; it
# must not create a second Compose stack or alternate service port. Artifact
# identity may still be branch/worktree-specific and is handled separately below.
runtime_mode="single_default"
compose_project_name="${PROMPTBRANCH_DEFAULT_COMPOSE_PROJECT_NAME:-${project_name}}"
service_port="${PROMPTBRANCH_DEFAULT_SERVICE_PORT:-8000}"
service_base_url="http://localhost:${service_port}"
export COMPOSE_PROJECT_NAME="${compose_project_name}"
export PROMPTBRANCH_SERVICE_PORT="${service_port}"
export CHATGPT_SERVICE_BASE_URL="${service_base_url}"
version_file="${repo_root}/VERSION"
downloads_dir="${DOWNLOADS_DIR:-${HOME}/Downloads}"
work_parent="${TMPDIR:-/tmp}/${repo_basename}_release_import"
container_id="${PROMPTBRANCH_CONTAINER_ID:-}"
owner_user="${PROMPTBRANCH_OWNER_USER:-${SUDO_USER:-${USER}}}"
owner_group="${PROMPTBRANCH_OWNER_GROUP:-$(id -gn "${owner_user}" 2>/dev/null || printf '%s' "${owner_user}")}"
version_arg="${PB_RELEASE_VERSION:-}"
release_log_root_arg="${PROMPTBRANCH_RELEASE_LOG_DIR:-}"
release_log_keep="${PROMPTBRANCH_RELEASE_LOG_KEEP:-12}"
prune_release_logs=0

skip_compare=1  # deprecated no-op; Beyond Compare is no longer used.
skip_zip_import=0
install_from_zip=0
install_zip=""
allow_dirty=0
skip_commit=0
skip_push=0
skip_source_add=0
skip_install=0
skip_chown=0
skip_service=0
skip_tests=1
skip_docker_logs=0
keep_workdir=0
import_plan=0
tests_only=0
adopt_current=0
adopt_if_green=0

# detached prevents the release-control script from being captured by a long-running service.
service_mode="${PROMPTBRANCH_SERVICE_MODE:-detached}"
service_timeout_seconds="${PROMPTBRANCH_SERVICE_TIMEOUT_SECONDS:-90}"
test_timeout_seconds="${PROMPTBRANCH_TEST_TIMEOUT_SECONDS:-3600}"
workflow_rc=0

default_packager="${HOME}/scripts/zip_with_not_to_zip.sh"
packager="${PROMPTBRANCH_PACKAGER:-${default_packager}}"

usage() {
  cat <<USAGE
Usage:
  $(basename "$0") --version v0.0.239 [options]
  $(basename "$0") v0.0.239 [options]
  $(basename "$0") --install-from-zip ~/Downloads/chatgpt_claudecode_workflow_v0.0.239.zip
  $(basename "$0") --version v0.0.241 --import-plan

Options:
  -v, --version VERSION       Highest-precedence release version override.
                              Accepts v0.0.239, v0.0.239.1, 0.0.239, 0.0.239.1, or <artifact-prefix>_v0.0.239.zip.
      --downloads-dir DIR     Directory containing the downloaded candidate ZIP. Default: ~/Downloads.
      --install-from-zip ZIP   Install this candidate ZIP into the working tree before commit/package.
      --skip-zip-import       Do not install a candidate ZIP; operate on the current working tree.
      --import-plan,
      --dry-run-import        Validate and describe the candidate ZIP import without modifying
                              the working tree, committing, packaging, uploading, installing,
                              starting services, or running tests.
      --allow-dirty           Allow automatic ZIP import over a dirty working tree. Default: fail closed.
      --container-id ID       Docker container id/name for service logs. Auto-detected if omitted.
      --owner USER[:GROUP]    Owner for generated repo-local state (.pb_profile and debug_artifacts). Default: ${owner_user}:${owner_group}.
      --packager PATH         Packaging helper. Default: ${default_packager}.
      --skip-compare          Deprecated compatibility no-op. Beyond Compare is no longer used.
      --skip-commit           Skip git add/commit/push.
      --no-push               Commit but do not git push.
      --skip-source-add       Skip promptbranch src add.
      --skip-install          Skip pipx reinstall from generated ZIP.
      --skip-chown            Skip ownership normalization of .pb_profile and debug_artifacts.
      --skip-service          Skip ./run_chatgpt_service.sh.
      --service-mode MODE     detached or foreground. Default: detached.
                              detached mode starts ./run_chatgpt_service.sh with nohup and continues.
      --service-timeout SEC   Seconds to wait for service readiness. Default: 90.
      --test-timeout SEC      Max seconds for pb test full. Default: 3600.
      --run-tests             Run pb test full/report. Disabled by default.
                              The test block is wrapped in startlog/stoplog when available,
                              or an internal tee-based session log fallback otherwise.
                              Does not imply adoption. Use --tests-only --adopt-if-green for
                              guarded adoption of an already uploaded Project Source ZIP.
      --tests-only            Run only the logged pb test full/report block for the selected
                              version. Implies --run-tests and skips ZIP import,
                              commit, packaging, source add, install, service, and docker logs.
      --adopt-current         Adopt the selected local ZIP as the current Project Source/artifact
                              baseline after verifying the ZIP and Project Source. Skips release
                              ZIP import, commit, packaging, source add, install, service,
                              and docker logs.
      --adopt-if-green        With --tests-only, adopt the selected ZIP only when pb test report
                              is ok:true, status:verified, and failure_count:0. Not valid with
                              the full --run-tests release workflow.
      --skip-tests            Explicitly skip pb test full/report.
      --skip-docker-logs      Skip docker logs capture.
      --release-log-dir DIR    Directory root for release-control logs. Default: .pb_profile/release_logs.
      --release-log-keep N     Number of version log directories to keep when pruning. Default: 12.
      --prune-release-logs     After the workflow, prune old release log directories under the
                              release log root. The current version directory is always kept.
      --keep-workdir          Keep temporary extracted candidate directory.
  -h, --help                  Show this help.

Version precedence:
  CLI argument > PB_RELEASE_VERSION > VERSION file

Automatic ZIP import:
  By default this script installs ${project_name}_VERSION.zip from --downloads-dir
  into the repository before commit/package. This is an overwrite import, not a
  merge. It preserves .git/, .env, .generated/, .pb_profile/, profile/, and debug_artifacts/.
  It requires candidate ZIP control files (.gitignore and .not_to_zip) and
  refuses to stage local secrets or generated artifacts.

Typical use:
  $(basename "$0") --version v0.0.239
  $(basename "$0") --tests-only
  $(basename "$0") --tests-only --adopt-if-green
  $(basename "$0") --adopt-current
  $(basename "$0") --run-tests --skip-docker-logs
  $(basename "$0") --skip-zip-import --run-tests
  $(basename "$0") --version v0.0.241 --import-plan
USAGE
}

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required"
}

normalize_version() {
  local raw="$1"
  raw="${raw##*/}"
  raw="${raw%.zip}"
  raw="${raw#${project_name}_}"
  raw="${raw#${project_name}}"
  raw="${raw#${artifact_project_name}_}"
  raw="${raw#${artifact_project_name}}"
  raw="${raw#_}"
  raw="${raw#-}"
  if [[ "${raw}" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
    raw="${raw#v}"
    printf 'v%s\n' "${raw}"
    return 0
  fi
  # Accept noncanonical transport filenames such as
  # chatgpt_claudecode_workflow-2_v0.1.0.zip by extracting only the trailing
  # version token. This keeps input ZIP handling flexible while release output
  # uses the selected artifact identity.
  if [[ "${raw}" =~ (^|[_-])(v?[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?)$ ]]; then
    raw="${BASH_REMATCH[2]}"
    raw="${raw#v}"
    printf 'v%s\n' "${raw}"
    return 0
  fi
  return 1
}


artifact_prefix_from_zip_name() {
  local raw="$1"
  raw="${raw##*/}"
  raw="${raw%.zip}"
  if [[ "${raw}" =~ ^(.+)[_-]v?[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
    printf '%s\n' "${BASH_REMATCH[1]}"
    return 0
  fi
  printf '%s\n' "${artifact_project_name}"
}

resolve_download_zip() {
  local ver_value="$1"
  local dir="$2"
  local canonical="${dir}/${artifact_project_name}_${ver_value}.zip"
  local legacy_canonical="${dir}/${project_name}_${ver_value}.zip"
  local fallback="${dir}/${ver_value}.zip"
  local matches=()
  local candidate

  if [[ -f "${canonical}" ]]; then
    printf '%s\n' "${canonical}"
    return 0
  fi
  if [[ -f "${fallback}" ]]; then
    printf '%s\n' "${fallback}"
    return 0
  fi

  # Tolerate noncanonical transport artifacts from worktree-local packagers,
  # for example chatgpt_claudecode_workflow-2_v0.1.0.zip. Ambiguity fails
  # closed so the operator must pass --install-from-zip explicitly.
  shopt -s nullglob
  for candidate in "${dir}"/*_"${ver_value}".zip "${dir}"/*-"${ver_value}".zip; do
    [[ -f "${candidate}" ]] || continue
    matches+=("${candidate}")
  done
  shopt -u nullglob
  if [[ ${#matches[@]} -eq 1 ]]; then
    printf '%s\n' "${matches[0]}"
    return 0
  fi
  if [[ ${#matches[@]} -gt 1 ]]; then
    printf 'ambiguous candidate ZIPs for %s in %s:\n' "${ver_value}" "${dir}" >&2
    printf '  %s\n' "${matches[@]}" >&2
    return 1
  fi

  printf '%s\n' "${canonical}"
  return 1
}

find_stage0_install_zip_arg() {
  local parsed_ver="${PB_RELEASE_VERSION:-}"
  local parsed_downloads_dir="${DOWNLOADS_DIR:-${HOME}/Downloads}"
  local explicit_zip=""
  local disable_import=0
  local arg

  while [[ $# -gt 0 ]]; do
    arg="$1"
    case "${arg}" in
      -h|--help|--tests-only|--run-tests-only|--adopt-current|--import-plan|--dry-run-import)
        return 1
        ;;
      --skip-zip-import)
        disable_import=1
        shift
        ;;
      --install-from-zip)
        [[ $# -ge 2 ]] || return 1
        explicit_zip="$2"
        shift 2
        ;;
      --install-from-zip=*)
        explicit_zip="${arg#*=}"
        shift
        ;;
      -v|--version)
        [[ $# -ge 2 ]] || return 1
        parsed_ver="$2"
        shift 2
        ;;
      --version=*)
        parsed_ver="${arg#*=}"
        shift
        ;;
      --downloads-dir)
        [[ $# -ge 2 ]] || return 1
        parsed_downloads_dir="$2"
        shift 2
        ;;
      --downloads-dir=*)
        parsed_downloads_dir="${arg#*=}"
        shift
        ;;
      --)
        shift
        if [[ $# -ge 1 && -z "${parsed_ver}" ]]; then
          parsed_ver="$1"
        fi
        break
        ;;
      --*)
        shift
        ;;
      *)
        if [[ -z "${parsed_ver}" ]]; then
          parsed_ver="${arg}"
        fi
        shift
        ;;
    esac
  done

  (( disable_import == 0 )) || return 1

  if [[ -n "${explicit_zip}" ]]; then
    [[ -f "${explicit_zip}" ]] || return 1
    printf '%s\n' "${explicit_zip}"
    return 0
  fi

  if [[ -z "${parsed_ver}" ]]; then
    [[ -f "${version_file}" ]] || return 1
    parsed_ver="$(head -n 1 "${version_file}" | tr -d '[:space:]')"
  fi

  parsed_ver="$(normalize_version "${parsed_ver}" 2>/dev/null)" || return 1
  local resolved
  resolved="$(resolve_download_zip "${parsed_ver}" "${parsed_downloads_dir}" 2>/dev/null)" || return 1
  [[ -f "${resolved}" ]] || return 1
  printf '%s\n' "${resolved}"
}

if [[ "${PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0:-0}" != "1" ]]; then
  if candidate_stage0_zip="$(find_stage0_install_zip_arg "$@" 2>/dev/null)"; then
    [[ -n "${candidate_stage0_zip}" ]] || fail "could not resolve candidate ZIP for Stage-0 delegation"
    [[ -f "${candidate_stage0_zip}" ]] || fail "candidate ZIP not found: ${candidate_stage0_zip}"
    need_cmd unzip

    candidate_stage0_script="$(mktemp "${TMPDIR:-/tmp}/promptbranch-release-candidate-workflow.XXXXXX.sh")"
    if ! unzip -p "${candidate_stage0_zip}" chatgpt_claudecode_workflow_release_control.sh > "${candidate_stage0_script}" 2>/dev/null; then
      rm -f "${candidate_stage0_script}"
      fail "candidate ZIP does not contain chatgpt_claudecode_workflow_release_control.sh"
    fi
    chmod +x "${candidate_stage0_script}"
    echo "== Delegate to workflow runner from candidate ZIP =="
    echo "candidate_zip: ${candidate_stage0_zip}"
    echo "stage0_script: ${candidate_stage0_script}"
    export PROMPTBRANCH_RELEASE_WORKFLOW_REPO_ROOT="${repo_root}"
    export PROMPTBRANCH_RELEASE_WORKFLOW_CANDIDATE_STAGE0=1
    exec "${candidate_stage0_script}" "$@"
  fi
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--version)
      [[ $# -ge 2 ]] || fail "--version requires a value"
      version_arg="$2"
      shift 2
      ;;
    --version=*) version_arg="${1#*=}"; shift ;;
    --downloads-dir)
      [[ $# -ge 2 ]] || fail "--downloads-dir requires a value"
      downloads_dir="$2"
      shift 2
      ;;
    --downloads-dir=*) downloads_dir="${1#*=}"; shift ;;
    --install-from-zip)
      [[ $# -ge 2 ]] || fail "--install-from-zip requires a ZIP path"
      install_from_zip=1
      install_zip="$2"
      shift 2
      ;;
    --install-from-zip=*)
      install_from_zip=1
      install_zip="${1#*=}"
      shift
      ;;
    --skip-zip-import) skip_zip_import=1; shift ;;
    --import-plan|--dry-run-import)
      import_plan=1
      skip_commit=1
      skip_push=1
      skip_source_add=1
      skip_install=1
      skip_chown=1
      skip_service=1
      skip_tests=1
      skip_docker_logs=1
      shift
      ;;
    --allow-dirty) allow_dirty=1; shift ;;
    --release-log-dir)
      [[ $# -ge 2 ]] || fail "--release-log-dir requires a value"
      release_log_root_arg="$2"
      shift 2
      ;;
    --release-log-dir=*) release_log_root_arg="${1#*=}"; shift ;;
    --release-log-keep)
      [[ $# -ge 2 ]] || fail "--release-log-keep requires an integer value"
      release_log_keep="$2"
      shift 2
      ;;
    --release-log-keep=*) release_log_keep="${1#*=}"; shift ;;
    --prune-release-logs) prune_release_logs=1; shift ;;
    --container-id)
      [[ $# -ge 2 ]] || fail "--container-id requires a value"
      container_id="$2"
      shift 2
      ;;
    --container-id=*) container_id="${1#*=}"; shift ;;
    --owner)
      [[ $# -ge 2 ]] || fail "--owner requires USER or USER:GROUP"
      owner_value="$2"
      owner_user="${owner_value%%:*}"
      owner_group="${owner_value#*:}"
      [[ "${owner_group}" != "${owner_value}" ]] || owner_group="${owner_user}"
      shift 2
      ;;
    --owner=*)
      owner_value="${1#*=}"
      owner_user="${owner_value%%:*}"
      owner_group="${owner_value#*:}"
      [[ "${owner_group}" != "${owner_value}" ]] || owner_group="${owner_user}"
      shift
      ;;
    --packager)
      [[ $# -ge 2 ]] || fail "--packager requires a path"
      packager="$2"
      shift 2
      ;;
    --packager=*) packager="${1#*=}"; shift ;;
    --skip-compare) skip_compare=1; shift ;; # deprecated no-op
    --skip-commit) skip_commit=1; shift ;;
    --no-push) skip_push=1; shift ;;
    --skip-source-add) skip_source_add=1; shift ;;
    --skip-install) skip_install=1; shift ;;
    --skip-chown) skip_chown=1; shift ;;
    --skip-service) skip_service=1; shift ;;
    --service-mode)
      [[ $# -ge 2 ]] || fail "--service-mode requires detached or foreground"
      service_mode="$2"
      shift 2
      ;;
    --service-mode=*) service_mode="${1#*=}"; shift ;;
    --service-timeout)
      [[ $# -ge 2 ]] || fail "--service-timeout requires seconds"
      service_timeout_seconds="$2"
      shift 2
      ;;
    --service-timeout=*) service_timeout_seconds="${1#*=}"; shift ;;
    --test-timeout)
      [[ $# -ge 2 ]] || fail "--test-timeout requires seconds"
      test_timeout_seconds="$2"
      shift 2
      ;;
    --test-timeout=*) test_timeout_seconds="${1#*=}"; shift ;;
    --run-tests) skip_tests=0; shift ;;
    --tests-only|--run-tests-only)
      tests_only=1
      skip_tests=0
      skip_compare=1
      skip_zip_import=1
      skip_commit=1
      skip_push=1
      skip_source_add=1
      skip_install=1
      skip_chown=1
      skip_service=1
      skip_docker_logs=1
      shift
      ;;
    --adopt-current)
      adopt_current=1
      skip_compare=1
      skip_zip_import=1
      skip_commit=1
      skip_push=1
      skip_source_add=1
      skip_install=1
      skip_chown=1
      skip_service=1
      skip_docker_logs=1
      shift
      ;;
    --adopt-if-green)
      adopt_if_green=1
      shift
      ;;
    --skip-tests) skip_tests=1; shift ;;
    --skip-docker-logs) skip_docker_logs=1; shift ;;
    --keep-workdir) keep_workdir=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --*) fail "unknown option: $1" ;;
    *)
      if [[ -z "${version_arg}" ]]; then
        version_arg="$1"
        shift
      else
        fail "unexpected positional argument: $1"
      fi
      ;;
  esac
done

case "${service_mode}" in
  detached|foreground) ;;
  *) fail "--service-mode must be detached or foreground; got ${service_mode}" ;;
esac
[[ "${service_timeout_seconds}" =~ ^[0-9]+$ ]] || fail "--service-timeout must be an integer number of seconds"
[[ "${test_timeout_seconds}" =~ ^[0-9]+$ ]] || fail "--test-timeout must be an integer number of seconds"
[[ "${release_log_keep}" =~ ^[0-9]+$ ]] || fail "--release-log-keep must be an integer number of version directories"
if (( release_log_keep < 1 )); then
  fail "--release-log-keep must be at least 1 so the current release log directory is retained"
fi
if [[ ${adopt_if_green} -eq 1 && ${tests_only} -eq 0 ]]; then
  fail "--adopt-if-green is only supported with --tests-only. Use --tests-only --adopt-if-green for guarded adoption, or run --run-tests and then --adopt-current as a separate explicit step."
fi
if [[ ${adopt_if_green} -eq 1 && ${skip_tests} -eq 1 ]]; then
  fail "--adopt-if-green requires --tests-only to run the full test/report block"
fi

if [[ ${import_plan} -eq 1 && ${skip_zip_import} -eq 1 ]]; then
  fail "--import-plan requires a candidate ZIP; do not combine it with --skip-zip-import"
fi
if [[ ${import_plan} -eq 1 && ${adopt_current} -eq 1 ]]; then
  fail "--import-plan cannot be combined with --adopt-current"
fi

if [[ -z "${version_arg}" ]]; then
  if [[ ${install_from_zip} -eq 1 ]]; then
    version_arg="${install_zip}"
  else
    [[ -f "${version_file}" ]] || fail "VERSION file not found and no --version supplied: ${version_file}"
    version_arg="$(head -n 1 "${version_file}" | tr -d '[:space:]')"
  fi
fi

ver="$(normalize_version "${version_arg}")" || fail "version must look like v0.0.239, v0.0.239.1, 0.0.239, 0.0.239.1, or <artifact-prefix>_v0.0.239.zip; got '${version_arg}'"
ver_plain="${ver#v}"
if [[ ${install_from_zip} -eq 1 ]]; then
  [[ -n "${install_zip}" ]] || fail "--install-from-zip did not provide a ZIP path"
  [[ -f "${install_zip}" ]] || fail "install ZIP not found: ${install_zip}"
  artifact_project_name="$(artifact_prefix_from_zip_name "${install_zip}")"
elif [[ -n "${PROMPTBRANCH_ARTIFACT_PROJECT_NAME:-}" ]]; then
  artifact_project_name="${PROMPTBRANCH_ARTIFACT_PROJECT_NAME}"
else
  artifact_project_name="${repo_basename}"
fi
artifact_zip="${artifact_project_name}_${ver}.zip"
if [[ ${install_from_zip} -eq 0 ]]; then
  install_zip="$(resolve_download_zip "${ver}" "${downloads_dir}" 2>/dev/null || true)"
fi
download_zip="${install_zip}"
work_dir="${work_parent}/${artifact_project_name}_${ver}"
release_log_root="${release_log_root_arg:-${repo_root}/.pb_profile/release_logs}"
release_log_dir="${release_log_root}/${ver}"
mkdir -p "${release_log_dir}"
full_log="${release_log_dir}/pb_test.full.${ver}.log"
report_json="${release_log_dir}/pb_test.full.${ver}.report.json"
if [[ -n "${PROMPTBRANCH_TEST_SESSION_LOG:-}" ]]; then
  case "${PROMPTBRANCH_TEST_SESSION_LOG}" in
    /*) test_session_log="${PROMPTBRANCH_TEST_SESSION_LOG}" ;;
    *) test_session_log="${release_log_dir}/${PROMPTBRANCH_TEST_SESSION_LOG}" ;;
  esac
else
  test_session_log="${release_log_dir}/session_$(date +%Y%m%d_%H%M%S).log"
fi
test_session_logging_mode="none"
service_log="${release_log_dir}/promptbranch-service.${ver_plain}.log"
service_start_log="${release_log_dir}/promptbranch-service-start.${ver_plain}.log"
service_pid_file="${release_log_dir}/promptbranch-service-start.${ver_plain}.pid"

if [[ ${tests_only} -eq 0 && ${adopt_current} -eq 0 && ${skip_zip_import} -eq 0 ]]; then
  [[ -f "${download_zip}" ]] || fail "Download ZIP not found. Expected ${downloads_dir}/${artifact_zip} or ${downloads_dir}/${ver}.zip; use --install-from-zip ZIP or --skip-zip-import."
fi

need_cmd python3
if [[ ${import_plan} -eq 0 ]]; then
  need_cmd promptbranch
fi
if [[ ${skip_tests} -eq 0 || ${adopt_current} -eq 1 ]]; then
  need_cmd pb
fi
if [[ ${import_plan} -eq 0 && ${tests_only} -eq 0 && ${adopt_current} -eq 0 ]]; then
  need_cmd unzip
  need_cmd git
  need_cmd pipx
  if [[ ${skip_zip_import} -eq 0 ]]; then
    need_cmd rsync
  fi
fi
if [[ ${skip_tests} -eq 0 || ${skip_service} -eq 0 ]]; then
  need_cmd timeout
fi
if [[ ${skip_docker_logs} -eq 0 ]]; then
  need_cmd docker
fi

if [[ ${import_plan} -eq 1 ]]; then
  need_cmd unzip
fi

release_import_plan_json() {
  local zip_path="$1"
  local expected_version="$2"
  local repo_path="$3"
  local preserved_csv=".git,.env,.generated,.pb_profile,profile,debug_artifacts"
  python3 - "$zip_path" "$expected_version" "$repo_path" "$preserved_csv" <<'INNERPY'
import json
import sys
import zipfile
from pathlib import Path

zip_path = Path(sys.argv[1]).expanduser().resolve()
expected_version = sys.argv[2]
repo_path = Path(sys.argv[3]).expanduser().resolve()
preserved_paths = sys.argv[4].split(",")
script_name = "chatgpt_claudecode_workflow_release_control.sh"
required_root_files = ["VERSION", "pyproject.toml", ".gitignore", ".not_to_zip", script_name]
protected_zip_roots = [".env", ".generated", ".pb_profile", "profile", "debug_artifacts"]
payload = {
    "ok": False,
    "action": "release_zip_import_plan",
    "version": expected_version,
    "candidate_zip": str(zip_path),
    "repo_root": str(repo_path),
    "zip_exists": zip_path.is_file(),
    "zip_crc_ok": False,
    "zip_version": None,
    "zip_root_layout": "unknown",
    "candidate_script_present": False,
    "required_root_files": required_root_files,
    "missing_required_root_files": [],
    "protected_zip_entries_sample": [],
    "preserved_paths": preserved_paths,
    "would_install": False,
    "errors": [],
    "root_entries_sample": [],
    "would_remove_root_entries_sample": [],
    "would_install_root_entries_sample": [],
}
if not zip_path.is_file():
    payload["errors"].append("candidate_zip_missing")
    print(json.dumps(payload, indent=2, sort_keys=True))
    raise SystemExit(1)
try:
    with zipfile.ZipFile(zip_path) as archive:
        bad_crc = archive.testzip()
        if bad_crc:
            payload["errors"].append(f"zip_crc_failure:{bad_crc}")
        else:
            payload["zip_crc_ok"] = True
        names = [name for name in archive.namelist() if name and not name.endswith("/")]
        top_entries = sorted({name.split("/", 1)[0] for name in names})
        payload["root_entries_sample"] = top_entries[:40]
        wrapper = bool(top_entries) and len(top_entries) == 1 and all("/" in name for name in names)
        if wrapper:
            payload["zip_root_layout"] = "wrapper_folder"
            payload["errors"].append("wrapper_folder")
        elif "VERSION" in names:
            payload["zip_root_layout"] = "repo_root"
        else:
            payload["zip_root_layout"] = "missing_root_VERSION"
            payload["errors"].append("missing_root_VERSION")
        if "VERSION" in names:
            payload["zip_version"] = archive.read("VERSION").decode("utf-8", errors="replace").strip()
            if payload["zip_version"] != expected_version:
                payload["errors"].append("version_mismatch")
        payload["candidate_script_present"] = script_name in names
        missing_required = [item for item in required_root_files if item not in names]
        payload["missing_required_root_files"] = missing_required
        if missing_required:
            payload["errors"].append("missing_required_root_files")
        if not payload["candidate_script_present"]:
            payload["errors"].append("candidate_script_missing")
        protected_entries = []
        for name in names:
            if name == ".env" or name.startswith(".env."):
                protected_entries.append(name)
                continue
            if any(name == root or name.startswith(root + "/") for root in protected_zip_roots):
                protected_entries.append(name)
        if protected_entries:
            payload["protected_zip_entries_sample"] = protected_entries[:20]
            payload["errors"].append("protected_zip_entries_present")
        bad_generated = [name for name in names if ".pytest_cache" in name or "__pycache__" in name or name.endswith((".pyc", ".pyo"))]
        if bad_generated:
            payload["errors"].append("generated_cache_entries_present")
            payload["bad_generated_entries_sample"] = bad_generated[:20]
        payload["would_install_root_entries_sample"] = top_entries[:40]
except zipfile.BadZipFile:
    payload["errors"].append("bad_zip_file")
if repo_path.is_dir():
    preserved = set(preserved_paths)
    removable = sorted(path.name for path in repo_path.iterdir() if path.name not in preserved)
    payload["would_remove_root_entries_sample"] = removable[:40]
else:
    payload["errors"].append("repo_root_missing")
payload["would_install"] = not payload["errors"]
payload["ok"] = payload["would_install"]
print(json.dumps(payload, indent=2, sort_keys=True))
raise SystemExit(0 if payload["ok"] else 1)
INNERPY
}

validate_release_import_plan() {
  local zip_path="$1"
  local expected_version="$2"
  local repo_path="$3"
  release_import_plan_json "$zip_path" "$expected_version" "$repo_path" >/dev/null
}

verify_release_import_copied_entries() {
  local zip_path="$1"
  local repo_path="$2"
  python3 - "$zip_path" "$repo_path" <<'INNERPY'
import json
import sys
import zipfile
from pathlib import Path

zip_path = Path(sys.argv[1]).expanduser().resolve()
repo_path = Path(sys.argv[2]).expanduser().resolve()
protected_roots = {".git", ".env", ".generated", ".pb_profile", "profile", "debug_artifacts"}
missing = []
checked = 0
with zipfile.ZipFile(zip_path) as archive:
    for info in archive.infolist():
        name = info.filename.strip("/")
        if not name or info.is_dir():
            continue
        root = name.split("/", 1)[0]
        if root in protected_roots or name == ".env" or name.startswith(".env."):
            continue
        checked += 1
        if not (repo_path / name).exists():
            missing.append(name)
if missing:
    print(json.dumps({
        "ok": False,
        "action": "release_zip_import_copy_verification",
        "checked_count": checked,
        "missing_count": len(missing),
        "missing_sample": missing[:40],
    }, indent=2, sort_keys=True), file=sys.stderr)
    raise SystemExit(1)
print(json.dumps({
    "ok": True,
    "action": "release_zip_import_copy_verification",
    "checked_count": checked,
    "missing_count": 0,
}, indent=2, sort_keys=True))
INNERPY
}

force_add_intentional_ignored_release_paths() {
  local path
  for path in \
    "ollama_mcp_verification_harness" \
    "ollama_mcp_verification_harness_v2" \
    "promptbranch.egg-info"
  do
    if [[ -e "${repo_root}/${path}" ]]; then
      git add -f -- "${path}"
    fi
  done
}

assert_release_staging_safe() {
  local bad=()
  local status path rest
  while IFS=$'\t' read -r status path rest; do
    [[ -n "${status}" && -n "${path}" ]] || continue
    case "${path}" in
      .env|.env.*|.generated|.generated/*|.pb_profile|.pb_profile/*|profile|profile/*|debug_artifacts|debug_artifacts/*|*.zip|*.tar.gz|*.log|*.trace|*.trace.zip|*.pyc|*.pyo|__pycache__|__pycache__/*|.pytest_cache|.pytest_cache/*|.mypy_cache|.mypy_cache/*|.ruff_cache|.ruff_cache/*)
        bad+=("${status}${IFS}${path}")
        ;;
    esac
    if [[ "${status}" == D* ]]; then
      case "${path}" in
        .gitignore|.not_to_zip)
          bad+=("${status}${IFS}${path}")
          ;;
      esac
    fi
  done < <(git diff --cached --name-status)

  if [[ ${#bad[@]} -gt 0 ]]; then
    printf 'ERROR: unsafe release-control staged paths detected:\n' >&2
    printf '  %s\n' "${bad[@]}" >&2
    printf 'ERROR: refusing to commit local secrets/generated artifacts/control-file deletion.\n' >&2
    return 1
  fi
}

owner_uid_for_user() {
  local user_name="$1"
  id -u "${user_name}" 2>/dev/null || return 1
}

ownership_normalization_targets() {
  local candidate
  for candidate in "${repo_root}/.pb_profile" "${repo_root}/debug_artifacts"; do
    if [[ -e "${candidate}" ]]; then
      printf '%s
' "${candidate}"
    fi
  done
}

normalize_generated_ownership() {
  local phase="$1"
  [[ ${skip_chown} -eq 0 ]] || return 0

  owner_uid_for_user "${owner_user}" >/dev/null || fail "could not resolve owner user for chown: ${owner_user}"

  mapfile -t chown_targets < <(ownership_normalization_targets)
  if [[ ${#chown_targets[@]} -eq 0 ]]; then
    return 0
  fi

  echo "== Normalize generated artifact ownership (${phase}) =="
  printf 'owner: %s:%s
' "${owner_user}" "${owner_group}"
  printf 'targets:
'
  printf '  %s
' "${chown_targets[@]}"

  if [[ "$(id -u)" -eq 0 ]]; then
    chown -R "${owner_user}:${owner_group}" "${chown_targets[@]}"
  else
    need_cmd sudo
    sudo chown -R "${owner_user}:${owner_group}" "${chown_targets[@]}"
  fi
}

printf '\n== Release control ==\n'
printf 'repo_root:      %s\n' "${repo_root}"
printf 'version:        %s\n' "${ver}"
printf 'artifact_zip:   %s\n' "${artifact_zip}"
printf 'download_zip:   %s\n' "${download_zip}"
printf 'repo_basename:  %s\n' "${repo_basename}"
printf 'compose_name:   %s\n' "${compose_project_name}"
printf 'service_port:   %s\n' "${service_port}"
printf 'work_dir:       %s\n' "${work_dir}"
printf 'release_logs:   %s\n' "${release_log_dir}"
printf 'log_prune:      %s\n' "${prune_release_logs}"
printf 'log_keep:       %s\n' "${release_log_keep}"
printf 'service_mode:   %s\n' "${service_mode}"
printf 'service_wait:   %ss\n' "${service_timeout_seconds}"
printf 'test_timeout:   %ss\n' "${test_timeout_seconds}"
printf 'tests_only:     %s\n' "${tests_only}"
printf 'adopt_current:  %s\n' "${adopt_current}"
printf 'adopt_if_green: %s\n' "${adopt_if_green}"
printf 'zip_import:     %s\n' "$((1 - skip_zip_import))"
printf 'import_plan:    %s\n' "${import_plan}"
printf '\n'

if [[ ${import_plan} -eq 1 ]]; then
  [[ -f "${download_zip}" ]] || fail "import plan ZIP not found: ${download_zip}"
  release_import_plan_json "${download_zip}" "${ver}" "${repo_root}"
  exit $?
fi

if [[ ${tests_only} -eq 0 && ${adopt_current} -eq 0 && ${skip_zip_import} -eq 0 ]]; then
  [[ -f "${download_zip}" ]] || fail "install ZIP not found: ${download_zip}"

  if [[ ${allow_dirty} -eq 0 ]]; then
    dirty="$(git status --porcelain --untracked-files=all)"
    [[ -z "${dirty}" ]] || fail "working tree has tracked/untracked changes; commit/stash first or use --allow-dirty"
  fi

  echo
  echo "== Verify install ZIP =="
  release_import_plan_json "${download_zip}" "${ver}" "${repo_root}"
  validate_release_import_plan "${download_zip}" "${ver}" "${repo_root}"

  rm -rf "${work_dir}"
  mkdir -p "${work_dir}"
  unzip -q "${download_zip}" -d "${work_dir}"
  [[ -f "${work_dir}/VERSION" ]] || fail "candidate ZIP must contain repository contents at ZIP root"

  echo
  echo "== Install ZIP into working tree =="
  normalize_generated_ownership "pre-import"
  find "${repo_root}" -mindepth 1 -maxdepth 1     ! -name ".git"     ! -name ".env"     ! -name ".generated"     ! -name ".pb_profile"     ! -name "profile"     ! -name "debug_artifacts"     -exec rm -rf {} +

  rsync -a     --exclude='.git'     --exclude='.git/'     --exclude='.env'     --exclude='.env.*'     --exclude='.generated/'     --exclude='.pb_profile/'     --exclude='profile/'     --exclude='debug_artifacts/'     "${work_dir}/" "${repo_root}/"

  verify_release_import_copied_entries "${download_zip}" "${repo_root}"

  cp "${download_zip}" "${repo_root}/${artifact_zip}"
  # ZIP archives produced by browser/download handoff may not reliably preserve
  # executable bits. Restore repository shell entrypoint permissions after
  # install before any service/test/finalizer step can evaluate them.
  find "${repo_root}" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} + 2>/dev/null || true
  if [[ -d "${repo_root}/scripts" ]]; then
    find "${repo_root}/scripts" -type f -name '*.sh' -exec chmod +x {} + 2>/dev/null || true
  fi
  if [[ -d "${repo_root}/docker" ]]; then
    find "${repo_root}/docker" -type f -name '*.sh' -exec chmod +x {} + 2>/dev/null || true
  fi
  echo "Installed ${download_zip} into ${repo_root}"

  if [[ ${keep_workdir} -eq 0 ]]; then
    rm -rf "${work_dir}"
  fi
fi

if [[ ${tests_only} -eq 0 && ${adopt_current} -eq 0 ]]; then
# Commit current working tree with the release ZIP name as commit message.
if [[ ${skip_commit} -eq 0 ]]; then
  git add -A .
  force_add_intentional_ignored_release_paths
  assert_release_staging_safe
  if git diff --cached --quiet; then
    echo "No staged git changes; skipping git commit."
  else
    git commit -m "${artifact_zip}"
  fi
  if [[ ${skip_push} -eq 0 ]]; then
    git push
  fi
fi

# Build canonical release ZIP. Prefer your existing packager, but provide a strict fallback.
# Remove transported/canonical release ZIPs before packaging so verification cannot
# accidentally validate the input ZIP instead of the newly packaged output.
rm -f "${artifact_zip}" "${repo_basename}_${ver}.zip" "${repo_basename}_${ver_plain}.zip" "${project_name}_${ver}.zip" "${project_name}_${ver_plain}.zip" "${artifact_project_name}_${ver}.zip" "${artifact_project_name}_${ver_plain}.zip"
if [[ -x "${packager}" ]]; then
  "${packager}"
else
  echo "WARN: packager not executable: ${packager}"
  echo "WARN: using built-in Python packaging fallback."
  python3 - "${repo_root}" "${artifact_zip}" <<'PY'
from pathlib import Path
import fnmatch
import os
import sys
import zipfile

root = Path(sys.argv[1]).resolve()
out = root / sys.argv[2]

exclude_patterns = [
    ".git/", "__pycache__/", "*.pyc", "*.pyo", ".pytest_cache/", ".mypy_cache/", ".ruff_cache/",
    "node_modules/", "dist/", "build/", "coverage/", ".venv/", "venv/", "env/",
    ".env", ".env.*", "*.zip", "*.tar.gz", "*.log", ".pb_profile/", "profile/",
    "debug_artifacts/", ".DS_Store",
]
not_to_zip = root / ".not_to_zip"
if not_to_zip.exists():
    for line in not_to_zip.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        exclude_patterns.append(line)

def match(rel: str, pattern: str, is_dir: bool) -> bool:
    rel = rel.strip("/")
    pattern = pattern.strip()
    if not pattern:
        return False
    directory_only = pattern.endswith("/")
    pattern = pattern.strip("/")
    if directory_only and not is_dir and not rel.startswith(pattern + "/"):
        return False
    candidates = {rel, Path(rel).name}
    if is_dir:
        candidates.add(rel + "/")
    return any(fnmatch.fnmatch(candidate, pattern) for candidate in candidates) or fnmatch.fnmatch(rel, pattern) or rel.startswith(pattern + "/")

def excluded(path: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if any(part in {".git", "__pycache__", ".pytest_cache"} for part in rel.split("/")):
        return True
    if path.suffix in {".pyc", ".pyo"}:
        return True
    parts = rel.split("/")
    for i in range(1, len(parts) + 1):
        candidate = "/".join(parts[:i])
        candidate_path = root / candidate
        is_dir = i < len(parts) or candidate_path.is_dir()
        if any(match(candidate, pattern, is_dir) for pattern in exclude_patterns):
            return True
    return False

files = []
for current, dirs, filenames in os.walk(root):
    current_path = Path(current)
    dirs[:] = [d for d in sorted(dirs) if not excluded(current_path / d)]
    for filename in sorted(filenames):
        path = current_path / filename
        if path == out:
            continue
        if not excluded(path):
            files.append(path)

if out.exists():
    out.unlink()
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted(files, key=lambda p: p.relative_to(root).as_posix()):
        archive.write(path, path.relative_to(root).as_posix())
print(f"created {out}")
PY
fi

# Normalize possible packager output names to the selected artifact identity.
# The packager may derive its output name from the worktree directory basename;
# release-control normalizes that to ${artifact_project_name}_${ver}.zip.
matched_packager_output=0
current_git_short="$(git rev-parse --short HEAD 2>/dev/null || true)"
packager_candidates=(
  "${artifact_zip}"
  "${artifact_project_name}_${ver}.zip"
  "${artifact_project_name}_${ver_plain}.zip"
  "${repo_basename}_${ver}.zip"
  "${repo_basename}_${ver_plain}.zip"
  "source_${ver}.zip"
  "source_${ver_plain}.zip"
  "source_${artifact_project_name}_${ver}.zip"
  "source_${artifact_project_name}_${ver_plain}.zip"
  "source_${project_name}_${ver}.zip"
  "source_${project_name}_${ver_plain}.zip"
  "source_${repo_basename}_${ver}.zip"
  "source_${repo_basename}_${ver_plain}.zip"
)
if [[ -n "${current_git_short}" ]]; then
  packager_candidates+=(
    "${artifact_project_name}-${current_git_short}.zip"
    "${artifact_project_name}_${current_git_short}.zip"
    "${project_name}-${current_git_short}.zip"
    "${project_name}_${current_git_short}.zip"
    "${repo_basename}-${current_git_short}.zip"
    "${repo_basename}_${current_git_short}.zip"
  )
fi
for candidate in "${packager_candidates[@]}"; do
  if [[ -f "${candidate}" ]]; then
    if [[ "${candidate}" != "${artifact_zip}" ]]; then
      mv -f "${candidate}" "${artifact_zip}"
    fi
    matched_packager_output=1
    break
  fi
done

if [[ ${matched_packager_output} -eq 0 ]]; then
  shopt -s nullglob
  generated_version_zips=("${repo_basename}"*_"${ver}".zip "${repo_basename}"*-"${ver}".zip "${artifact_project_name}"*_"${ver}".zip "${artifact_project_name}"*-"${ver}".zip)
  shopt -u nullglob
  if [[ ${#generated_version_zips[@]} -eq 1 ]]; then
    mv -f "${generated_version_zips[0]}" "${artifact_zip}"
    matched_packager_output=1
  elif [[ ${#generated_version_zips[@]} -gt 1 ]]; then
    printf 'ERROR: ambiguous packager outputs for version %s:\n' "${ver}" >&2
    printf '  %s\n' "${generated_version_zips[@]}" >&2
    fail "ambiguous packager output; refusing to choose release artifact"
  fi
fi

[[ -f "${artifact_zip}" ]] || fail "could not find packaging output for version ${ver}; expected ${artifact_zip}, source_* variants, ${repo_basename}_${ver}.zip, or git-sha variants"

# Verify ZIP hygiene before using it.
python3 - "${artifact_zip}" "${ver}" <<'PY'
import sys
import zipfile
from pathlib import Path
zip_path = Path(sys.argv[1])
expected_version = sys.argv[2]
with zipfile.ZipFile(zip_path) as z:
    bad_crc = z.testzip()
    if bad_crc:
        raise SystemExit(f"ZIP CRC failure at {bad_crc}")
    names = z.namelist()
    bad_entries = [n for n in names if ".pytest_cache" in n or "__pycache__" in n or n.endswith((".pyc", ".pyo"))]
    if bad_entries:
        raise SystemExit("bad generated/cache entries in ZIP: " + ", ".join(bad_entries[:20]))
    roots = {n.split("/")[0] for n in names if n.strip("/")}
    wrapper = len(roots) == 1 and all("/" in n for n in names if n.strip("/"))
    if wrapper:
        raise SystemExit("ZIP appears to contain a wrapper/root folder")
    version = z.read("VERSION").decode("utf-8").strip()
    if version != expected_version:
        raise SystemExit(f"VERSION mismatch in ZIP: expected {expected_version}, got {version}")
print(f"ZIP verified: {zip_path}")
PY

# Add release ZIP to ChatGPT Project Sources.
if [[ ${skip_source_add} -eq 0 ]]; then
  promptbranch src add "${artifact_zip}"
fi

# Reinstall local CLI from the release ZIP.
if [[ ${skip_install} -eq 0 ]]; then
  pipx uninstall promptbranch || true
  pipx install "./${artifact_zip}"
fi

# Restore ownership of generated repo-local state if needed.
normalize_generated_ownership "post-release"
fi



json_file_is_ok_true() {
  local path="$1"
  python3 - "$path" <<'INNERPY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="replace")
idx = raw.find("{")
if idx < 0:
    raise SystemExit(f"invalid JSON in {path}: no JSON object found")
payload = json.loads(raw[idx:])
if payload.get("ok") is not True:
    raise SystemExit(f"{path}: ok is not true")
INNERPY
}

report_is_green() {
  local path="$1"
  python3 - "$path" <<'INNERPY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="replace")
idx = raw.find("{")
if idx < 0:
    raise SystemExit(f"invalid test report JSON in {path}: no JSON object found")
payload = json.loads(raw[idx:])
if payload.get("ok") is not True:
    raise SystemExit(f"test report is not ok:true in {path}")
if payload.get("status") != "verified":
    raise SystemExit(f"test report status is not verified in {path}: {payload.get('status')!r}")
if int(payload.get("failure_count") or 0) != 0:
    raise SystemExit(f"test report failure_count is not 0 in {path}: {payload.get('failure_count')!r}")
INNERPY
}

verify_source_list_mentions_artifact() {
  local src_list_json="$1"
  python3 -c '
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
expected = sys.argv[2]
raw = path.read_text(encoding="utf-8", errors="replace")
idx = raw.find("{")
if idx < 0:
    raise SystemExit(f"invalid source list JSON in {path}: no JSON object found")
payload = json.loads(raw[idx:])

def source_objects(obj):
    if isinstance(obj, dict):
        keys = {"name", "filename", "file_name", "title", "source_name"}
        if any(obj.get(key) == expected for key in keys):
            yield obj
        for value in obj.values():
            yield from source_objects(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from source_objects(item)

matches = list(source_objects(payload))
if len(matches) != 1:
    raise SystemExit(f"expected exactly one Project Source named {expected}, found {len(matches)}")
' "$src_list_json" "${artifact_zip}"
}

verify_current_matches_version() {
  local current_json="$1"
  python3 - "$current_json" "${ver}" "${artifact_zip}" <<'INNERPY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
expected_version = sys.argv[2]
expected_artifact = sys.argv[3]
raw = path.read_text(encoding="utf-8", errors="replace")
idx = raw.find("{")
if idx < 0:
    raise SystemExit(f"invalid artifact current JSON in {path}: no JSON object found")
payload = json.loads(raw[idx:])
if payload.get("ok") is not True:
    raise SystemExit("artifact current did not return ok:true")
runtime = payload.get("runtime") or {}
state = payload.get("state") or {}
registry = payload.get("registry_current") or {}
for key, value in {
    "runtime.version": runtime.get("version"),
    "state.artifact_version": state.get("artifact_version"),
    "state.source_version": state.get("source_version"),
    "registry_current.version": registry.get("version"),
}.items():
    if value != expected_version:
        raise SystemExit(f"{key} mismatch: expected {expected_version}, got {value!r}")
for key, value in {
    "state.artifact_ref": state.get("artifact_ref"),
    "state.source_ref": state.get("source_ref"),
    "registry_current.filename": registry.get("filename"),
}.items():
    if value != expected_artifact:
        raise SystemExit(f"{key} mismatch: expected {expected_artifact}, got {value!r}")
consistency = payload.get("consistency") or {}
for key in ("registry_current_matches_state_artifact", "state_source_matches_state_artifact", "code_version_matches_state_source"):
    if consistency.get(key) is not True:
        raise SystemExit(f"consistency.{key} is not true")
INNERPY
}

adopt_current_artifact() {
  local local_zip="${repo_root}/${artifact_zip}"
  local verify_json="${release_log_dir}/pb_artifact_verify.${ver}.json"
  local src_list_json="${release_log_dir}/pb_src_list.before_adopt.${ver}.json"
  local adopt_json="${release_log_dir}/pb_artifact_adopt.${ver}.json"
  local current_json="${release_log_dir}/pb_artifact_current.${ver}.json"

  echo "== Adopt current Project Source artifact =="
  echo "artifact: ${artifact_zip}"
  echo "local_zip: ${local_zip}"

  [[ -f "${local_zip}" ]] || fail "local ZIP not found for adoption: ${local_zip}"

  echo "+ pb artifact verify ${local_zip} --json"
  pb artifact verify "${local_zip}" --json | tee "${verify_json}"
  json_file_is_ok_true "${verify_json}"

  echo "+ pb src list --json"
  pb src list --json | tee "${src_list_json}"
  json_file_is_ok_true "${src_list_json}"
  verify_source_list_mentions_artifact "${src_list_json}"

  echo "+ pb artifact adopt ${artifact_zip} --from-project-source --local-path ${local_zip} --json"
  pb artifact adopt "${artifact_zip}" --from-project-source --local-path "${local_zip}" --json | tee "${adopt_json}"
  python3 - "${adopt_json}" <<'INNERPY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="replace")
idx = raw.find("{")
if idx < 0:
    raise SystemExit("artifact adopt output did not contain JSON")
payload = json.loads(raw[idx:])
if payload.get("ok") is not True:
    raise SystemExit("artifact adopt did not return ok:true")
if payload.get("status") != "adopted":
    raise SystemExit(f"artifact adopt status is not adopted: {payload.get('status')!r}")
for key in ("source_verified", "artifact_registry_updated", "state_artifact_updated", "state_source_updated"):
    if payload.get(key) is not True:
        raise SystemExit(f"artifact adopt field {key} is not true")
if payload.get("project_source_mutated") is not False:
    raise SystemExit("artifact adopt unexpectedly mutated Project Sources")
INNERPY

  echo "+ pb artifact current --json"
  pb artifact current --json | tee "${current_json}"
  verify_current_matches_version "${current_json}"
  echo "Adopt verified: ${artifact_zip}"
}

start_test_session_log() {
  # Prefer operator-defined startlog/stoplog when available. In non-interactive
  # script contexts these shell functions often are not exported, so keep a
  # deterministic built-in fallback that mirrors: startlog; ...; stoplog.
  if command -v startlog >/dev/null 2>&1 && command -v stoplog >/dev/null 2>&1; then
    startlog "${test_session_log}"
    test_session_logging_mode="external"
    return 0
  fi

  exec 3>&1
  exec 4>&2
  exec > >(tee -a "${test_session_log}") 2>&1
  test_session_logging_mode="internal"
  echo "Logging started: ${test_session_log}"
  echo "Run completed test logging will restore normal stdout/stderr automatically."
}

stop_test_session_log() {
  case "${test_session_logging_mode}" in
    external)
      stoplog || true
      ;;
    internal)
      echo "Logging stopped: ${test_session_log}"
      exec 1>&3
      exec 2>&4
      exec 3>&-
      exec 4>&-
      ;;
    none|*)
      ;;
  esac
  test_session_logging_mode="none"
}

compose_file="docker-compose.chatgpt-service.yml"
service_health_json="${release_log_dir}/promptbranch_service_health.${ver}.json"
service_container_before_json="${release_log_dir}/docker_container_before.${ver}.json"
service_container_after_json="${release_log_dir}/docker_container_after.${ver}.json"
service_compose_ps_json="${release_log_dir}/docker_compose_ps.${ver}.json"

compose_service_container_id() {
  if ! command -v docker >/dev/null 2>&1; then
    return 0
  fi
  COMPOSE_PROJECT_NAME="${compose_project_name}" PROMPTBRANCH_SERVICE_PORT="${service_port}" CHATGPT_SERVICE_BASE_URL="${service_base_url}" docker compose -p "${compose_project_name}" -f "${compose_file}" ps -q 2>/dev/null | head -n 1 || true
}

write_container_inspect_json() {
  local container="$1"
  local output="$2"
  if [[ -z "${container}" ]]; then
    printf '{"ok":false,"status":"container_not_found"}
' > "${output}"
    return 0
  fi
  if docker inspect "${container}" > "${output}" 2>"${output}.stderr"; then
    rm -f "${output}.stderr"
  else
    printf '{"ok":false,"status":"docker_inspect_failed","container":"%s"}
' "${container}" > "${output}"
  fi
}

service_health_probe() {
  local expected_version_plain="${ver#v}"
  python3 - "${expected_version_plain}" "${service_health_json}" "${service_port}" <<'INNERPY'
import json
import sys
import urllib.request

expected = sys.argv[1]
out_path = sys.argv[2]
last_error = None
for path in ("/healthz", "/health"):
    url = f"http://127.0.0.1:{sys.argv[3]}" + path
    try:
        with urllib.request.urlopen(url, timeout=2.0) as response:
            raw = response.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"raw": raw}
            payload.setdefault("url", url)
            payload.setdefault("http_status", response.status)
            with open(out_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            actual = str(payload.get("version") or "")
            if actual == expected:
                raise SystemExit(0)
            raise SystemExit(f"service version mismatch: expected {expected}, got {actual!r}")
    except SystemExit:
        raise
    except Exception as exc:
        last_error = f"{url}: {exc}"
with open(out_path, "w", encoding="utf-8") as handle:
    json.dump({"ok": False, "status": "health_probe_failed", "expected_version": expected, "error": last_error}, handle, indent=2, sort_keys=True)
    handle.write("\n")
raise SystemExit(last_error or "service health probe failed")
INNERPY
}

wait_for_promptbranch_service_version() {
  local deadline=$((SECONDS + service_timeout_seconds))
  local detected=""
  echo "Waiting up to ${service_timeout_seconds}s for Promptbranch service version ${ver#v}..."
  while (( SECONDS < deadline )); do
    detected="$(compose_service_container_id)"
    if [[ -n "${detected}" ]]; then
      container_id="${detected}"
    fi
    if service_health_probe >/dev/null 2>"${service_health_json}.stderr"; then
      rm -f "${service_health_json}.stderr"
      echo "Promptbranch service health/version verified: ${ver#v}"
      if [[ -n "${container_id}" ]]; then
        echo "Detected service container: ${container_id}"
      fi
      return 0
    fi
    sleep 2
  done
  echo "ERROR: service did not report expected version ${ver#v} within ${service_timeout_seconds}s" >&2
  echo "ERROR: inspect service_start_log=${service_start_log}" >&2
  echo "ERROR: inspect service_health_json=${service_health_json}" >&2
  [[ ! -s "${service_health_json}.stderr" ]] || cat "${service_health_json}.stderr" >&2
  return 1
}

deploy_promptbranch_service_detached() {
  need_cmd docker
  [[ -f "${compose_file}" ]] || fail "compose file not found: ${compose_file}"

  local before_container
  before_container="$(compose_service_container_id)"
  write_container_inspect_json "${before_container}" "${service_container_before_json}"

  {
    echo "== Docker service recreate =="
    echo "compose_file: ${compose_file}"
    echo "runtime_mode: ${runtime_mode}"
    echo "compose_project_name: ${compose_project_name}"
    echo "service_port: ${service_port}"
    echo "service_base_url: ${service_base_url}"
    echo "expected_version: ${ver#v}"
    echo "+ COMPOSE_PROJECT_NAME=${compose_project_name} PROMPTBRANCH_SERVICE_PORT=${service_port} docker compose -p ${compose_project_name} -f ${compose_file} down --remove-orphans"
    COMPOSE_PROJECT_NAME="${compose_project_name}" PROMPTBRANCH_SERVICE_PORT="${service_port}" CHATGPT_SERVICE_BASE_URL="${service_base_url}" docker compose -p "${compose_project_name}" -f "${compose_file}" down --remove-orphans
    echo "+ COMPOSE_PROJECT_NAME=${compose_project_name} PROMPTBRANCH_SERVICE_PORT=${service_port} docker compose -p ${compose_project_name} -f ${compose_file} build --pull"
    COMPOSE_PROJECT_NAME="${compose_project_name}" PROMPTBRANCH_SERVICE_PORT="${service_port}" CHATGPT_SERVICE_BASE_URL="${service_base_url}" docker compose -p "${compose_project_name}" -f "${compose_file}" build --pull
    echo "+ COMPOSE_PROJECT_NAME=${compose_project_name} PROMPTBRANCH_SERVICE_PORT=${service_port} docker compose -p ${compose_project_name} -f ${compose_file} up -d --force-recreate --remove-orphans"
    COMPOSE_PROJECT_NAME="${compose_project_name}" PROMPTBRANCH_SERVICE_PORT="${service_port}" CHATGPT_SERVICE_BASE_URL="${service_base_url}" docker compose -p "${compose_project_name}" -f "${compose_file}" up -d --force-recreate --remove-orphans
    echo "+ COMPOSE_PROJECT_NAME=${compose_project_name} PROMPTBRANCH_SERVICE_PORT=${service_port} docker compose -p ${compose_project_name} -f ${compose_file} ps"
    COMPOSE_PROJECT_NAME="${compose_project_name}" PROMPTBRANCH_SERVICE_PORT="${service_port}" CHATGPT_SERVICE_BASE_URL="${service_base_url}" docker compose -p "${compose_project_name}" -f "${compose_file}" ps
    COMPOSE_PROJECT_NAME="${compose_project_name}" PROMPTBRANCH_SERVICE_PORT="${service_port}" CHATGPT_SERVICE_BASE_URL="${service_base_url}" docker compose -p "${compose_project_name}" -f "${compose_file}" ps --format json > "${service_compose_ps_json}" 2>/dev/null || true
  } >"${service_start_log}" 2>&1

  container_id="$(compose_service_container_id)"
  write_container_inspect_json "${container_id}" "${service_container_after_json}"

  if [[ -n "${before_container}" && -n "${container_id}" && "${before_container}" == "${container_id}" ]]; then
    echo "ERROR: Docker container was not recreated; before and after container IDs are both ${container_id}" >&2
    echo "ERROR: inspect service_start_log=${service_start_log}" >&2
    return 1
  fi

  wait_for_promptbranch_service_version
}

# Start/restart ChatGPT service using deterministic Docker Compose recreation.
if [[ ${skip_service} -eq 0 ]]; then
  if [[ -f "./run_chatgpt_service.sh" && ! -x "./run_chatgpt_service.sh" ]]; then
    chmod +x ./run_chatgpt_service.sh || fail "service script not executable and chmod failed: ./run_chatgpt_service.sh"
  fi
  [[ -x "./run_chatgpt_service.sh" ]] || fail "service script not executable: ./run_chatgpt_service.sh"
  if [[ "${service_mode}" == "detached" ]]; then
    echo "Recreating Docker service detached; output -> ${service_start_log}"
    rm -f "${service_pid_file}"
    deploy_promptbranch_service_detached || fail "Docker service recreate/version verification failed"
  else
    echo "Running ./run_chatgpt_service.sh in foreground with ${service_timeout_seconds}s timeout."
    if ! timeout --foreground "${service_timeout_seconds}" ./run_chatgpt_service.sh --build --force-recreate --remove-orphans; then
      echo "WARN: service foreground command exited non-zero or timed out." >&2
      workflow_rc=1
    fi
    wait_for_promptbranch_service_version || fail "service version verification failed"
  fi
fi

# Run full suite and parsed report. Always try to create a report, even if the suite fails.
if [[ ${skip_tests} -eq 0 ]]; then
  start_test_session_log
  test_rc=0
  report_rc=0
  set +e

  echo "+ CHATGPT_SERVICE_BASE_URL=${service_base_url} timeout --foreground ${test_timeout_seconds} pb test full --json 2>&1 | tee ${full_log}"
  CHATGPT_SERVICE_BASE_URL="${service_base_url}" timeout --foreground "${test_timeout_seconds}" pb test full --json 2>&1 | tee "${full_log}"
  test_rc=${PIPESTATUS[0]}
  if [[ ${test_rc} -ne 0 ]]; then
    echo "WARN: pb test full exited with ${test_rc}; continuing to test report." >&2
    workflow_rc=${test_rc}
  fi

  echo "+ CHATGPT_SERVICE_BASE_URL=${service_base_url} pb test report ${full_log} --json"
  CHATGPT_SERVICE_BASE_URL="${service_base_url}" pb test report "${full_log}" --json | tee "${report_json}"
  report_rc=${PIPESTATUS[0]}
  if [[ ${report_rc} -ne 0 ]]; then
    echo "WARN: pb test report exited with ${report_rc}." >&2
    workflow_rc=${report_rc}
  fi

  set -e

  if [[ ${adopt_if_green} -eq 1 ]]; then
    if [[ ${test_rc} -ne 0 || ${report_rc} -ne 0 ]]; then
      echo "WARN: skipping adopt because test/report command failed." >&2
    else
      report_is_green "${report_json}"
      adopt_current_artifact
    fi
  fi

  stop_test_session_log
fi

if [[ ${skip_tests} -eq 1 && ${adopt_current} -eq 1 ]]; then
  adopt_current_artifact
fi

capture_docker_logs_best_effort() {
  if [[ -z "${container_id}" ]]; then
    container_id="$(docker ps --format '{{.ID}} {{.Image}} {{.Names}}' | awk '/promptbranch|chatgpt/ {print $1; exit}' || true)"
  fi
  if [[ -z "${container_id}" ]]; then
    echo "WARN: no promptbranch/chatgpt docker container auto-detected; skipping docker logs" >&2
    return 0
  fi
  if ! docker inspect "${container_id}" >/dev/null 2>&1; then
    echo "WARN: docker container no longer exists; skipping docker logs: ${container_id}" >&2
    return 0
  fi
  if docker logs "${container_id}" > "${service_log}" 2>"${service_log}.stderr"; then
    if [[ ! -s "${service_log}.stderr" ]]; then
      rm -f "${service_log}.stderr"
    else
      echo "WARN: docker logs wrote stderr; see ${service_log}.stderr" >&2
    fi
    echo "Service log written: ${service_log}"
    return 0
  fi
  echo "WARN: docker logs failed for ${container_id}; continuing without failing release control. See ${service_log}.stderr if present." >&2
  return 0
}

prune_release_logs_best_effort() {
  # Explicit opt-in cleanup only. Logs are diagnostic evidence, so never prune
  # unless the operator asked for it. The current version directory is always
  # retained, even when it is older than other directories.
  python3 - "${release_log_root}" "${release_log_dir}" "${release_log_keep}" <<'INNERPY'
from __future__ import annotations

from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1]).expanduser().resolve()
current = Path(sys.argv[2]).expanduser().resolve()
keep = int(sys.argv[3])
if keep < 1:
    raise SystemExit("release_log_keep must be >= 1")
if not root.exists():
    print(f"Release log pruning skipped: root does not exist: {root}")
    raise SystemExit(0)
if not root.is_dir():
    print(f"WARN: release log root is not a directory; skipping prune: {root}", file=sys.stderr)
    raise SystemExit(0)
try:
    current.relative_to(root)
except ValueError:
    print(f"WARN: current release log dir is outside release log root; skipping prune: {current}", file=sys.stderr)
    raise SystemExit(0)
entries = [path for path in root.iterdir() if path.is_dir()]
entries.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
kept: list[Path] = []
removed: list[Path] = []
if current.exists():
    kept.append(current)
for path in entries:
    if path == current:
        continue
    if len(kept) < keep:
        kept.append(path)
    else:
        removed.append(path)
for path in removed:
    shutil.rmtree(path)
print("Release log pruning completed:")
print(f"  root:    {root}")
print(f"  keep:    {keep}")
print(f"  kept:    {len(kept)}")
print(f"  removed: {len(removed)}")
if removed:
    print("  removed_dirs:")
    for path in removed:
        print(f"    {path}")
INNERPY
}

# Capture service logs as a best-effort diagnostic only.
if [[ ${skip_docker_logs} -eq 0 ]]; then
  capture_docker_logs_best_effort
fi

prune_summary_active=0
if [[ ${prune_release_logs} -eq 1 ]]; then
  prune_release_logs_best_effort
  prune_summary_active=1
fi

summary_value() {
  local active="$1"
  local value="$2"
  if [[ "${active}" -eq 1 ]]; then
    printf '%s
' "${value}"
  else
    printf 'skipped
'
  fi
}

tests_summary_active=0
service_summary_active=0
docker_log_summary_active=0
if [[ ${skip_tests} -eq 0 ]]; then
  tests_summary_active=1
fi
if [[ ${skip_service} -eq 0 ]]; then
  service_summary_active=1
fi
if [[ ${skip_docker_logs} -eq 0 ]]; then
  docker_log_summary_active=1
fi

cat <<DONE

Release workflow completed.
version:       ${ver}
artifact:      ${artifact_zip}
artifact_name: ${artifact_project_name}
release_logs:  ${release_log_dir}
log_prune:     $(summary_value "${prune_summary_active}" "keep=${release_log_keep}")
full_log:      $(summary_value "${tests_summary_active}" "${full_log}")
report_json:   $(summary_value "${tests_summary_active}" "${report_json}")
adopt_current: ${adopt_current}
adopt_if_green: ${adopt_if_green}
test_session:  $(summary_value "${tests_summary_active}" "${test_session_log}")
service_log:   $(summary_value "${docker_log_summary_active}" "${service_log}")
service_start: $(summary_value "${service_summary_active}" "${service_start_log}")
runtime_mode:   ${runtime_mode}
compose_name:   ${compose_project_name}
service_port:   ${service_port}
service_base:   ${service_base_url}
service_health: $(summary_value "${service_summary_active}" "${service_health_json}")
compose_ps:     $(summary_value "${service_summary_active}" "${service_compose_ps_json}")
service_pid:   $(summary_value "${service_summary_active}" "${service_pid_file}")
exit_code:     ${workflow_rc}
DONE

exit "${workflow_rc}"
