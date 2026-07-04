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
compose_service_name="${PROMPTBRANCH_COMPOSE_SERVICE_NAME:-chatgpt-service}"
service_port="${PROMPTBRANCH_DEFAULT_SERVICE_PORT:-8000}"
service_base_url="http://localhost:${service_port}"
test_transport="${PROMPTBRANCH_TEST_TRANSPORT:-direct}"
localhost_base_url="${PROMPTBRANCH_LOCALHOST_BASE_URL:-http://127.0.0.1:${service_port}}"
# ChatGPT Project deletion is frozen. Release-control live tests must therefore
# keep created projects, but each release-control invocation should use a fresh
# run-scoped project name so browser/project history does not accumulate in one
# reused quarantine project.
release_test_project_name="${PROMPTBRANCH_RELEASE_TEST_PROJECT_NAME:-}"
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
skip_source_add="${PROMPTBRANCH_RELEASE_SKIP_SOURCE_ADD:-0}"
auth_only_validation="${PROMPTBRANCH_RELEASE_AUTH_ONLY_VALIDATION:-0}"
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
adopt_after_validation=0
run_all_tests=0
# Release-control run-all should treat ChatGPT conversation-history 429s as
# temporary backpressure: click/dismiss the modal in browser code, wait for the
# persisted cooldown window, then retry the same step once before declaring FIX.
run_all_rate_limit_retries="${PROMPTBRANCH_RUN_ALL_RATE_LIMIT_RETRIES:-1}"
run_all_rate_limit_cooldown_seconds="${PROMPTBRANCH_RUN_ALL_RATE_LIMIT_COOLDOWN_SECONDS:-185}"
run_all_rate_limit_skip_sleep="${PROMPTBRANCH_RUN_ALL_RATE_LIMIT_SKIP_SLEEP:-0}"
# Text Project Source add is useful as a compatibility probe, but the release-critical
# Project Source path is ZIP/file upload. Default run-all therefore excludes text
# source add/remove unless the operator asks for the strict source-kind matrix.
run_all_strict_source_kind_matrix="${PROMPTBRANCH_RUN_ALL_STRICT_SOURCE_KIND_MATRIX:-0}"
# Developer accelerator: run only the currently isolated failing text-source
# compatibility path through the selected full-test transports.
run_failing_tests=0

# detached prevents the release-control script from being captured by a long-running service.
service_mode="${PROMPTBRANCH_SERVICE_MODE:-detached}"
service_timeout_seconds="${PROMPTBRANCH_SERVICE_TIMEOUT_SECONDS:-90}"
test_timeout_seconds="${PROMPTBRANCH_TEST_TIMEOUT_SECONDS:-3600}"
workflow_rc=0
run_all_browser_guardrail_seen=0

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
                              Accepts v-prefixed or bare dotted numeric versions with at least three numeric segments, for example v0.0.239, v0.0.239.1, v0.1.78.2.1, or <artifact-prefix>_v0.1.78.2.1.zip.
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
      --auth-only-validation  Run the Bonnetjes Cloudflare auth-only release validation path.
                              Implies --skip-source-add and never enables Project Source mutation.
                              With --adopt-after-validation, adopts the ZIP with pb artifact adopt --local-only.
      --skip-install          Skip pipx reinstall from generated ZIP.
      --skip-chown            Skip ownership normalization of .pb_profile and debug_artifacts.
      --skip-service          Skip ./run_chatgpt_service.sh.
      --service-mode MODE     detached or foreground. Default: detached.
                              detached mode starts ./run_chatgpt_service.sh with nohup and continues.
      --service-timeout SEC   Seconds to wait for service readiness. Default: 90.
      --test-timeout SEC      Max seconds for pb test full. Default: 3600.
      --test-transport MODE   Test transport: direct, localhost, or both. Default: direct.
      --localhost-base-url URL Base URL for localhost test transport. Default: http://localhost:${service_port}.
      --run-tests             Run pb test full/report. Disabled by default.
                              The test block is wrapped in startlog/stoplog when available,
                              or an internal tee-based session log fallback otherwise.
                              Does not imply adoption. Use --tests-only --adopt-if-green for
                              guarded adoption of an already uploaded Project Source ZIP.
      --run-all-tests         Run the full operator validation stack in one command and continue
                              after individual failures. Implies --run-tests and --test-transport both.
                              Runs pb test full via direct+localhost, ask-live, visual-artifact-roundtrip,
                              release-live, import-smoke, and artifact guard, then writes a final GO/FIX JSON report.
                              By default, text-source add/remove is treated as a compatibility probe and is
                              excluded from the release-blocking full browser path.
      --strict-source-kind-matrix
                              With --run-all-tests, include text-source add/remove in the release-blocking
                              full browser source-kind matrix.
      --run-failing-tests     Developer accelerator for this repair line. Runs only the currently isolated
                              failing text-source compatibility path via direct+localhost full-test transports,
                              then writes the same GO/FIX summary. Skips live ask/artifact/import/guard rows.
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
      --adopt-after-validation
                              With the full --run-tests or --run-all-tests workflow, adopt the
                              selected local ZIP only after validation has completed successfully.
                              This does not skip ZIP import, source add, install, service, or tests.
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
  merge. It preserves .git/, .env, .generated/, .pb_profile/, .pb_profile_local_debug/, .pb_profile_local_debug_pools/, profile/, and debug_artifacts/.
  It requires candidate ZIP control files (.gitignore and .not_to_zip) and
  refuses to stage local secrets or generated artifacts.

Typical use:
  $(basename "$0") --version v0.0.239
  $(basename "$0") --tests-only
  $(basename "$0") --tests-only --adopt-if-green
  $(basename "$0") --adopt-current
  $(basename "$0") --run-tests --skip-docker-logs
  $(basename "$0") --run-tests --adopt-after-validation --skip-docker-logs
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

chatgpt_project_name_max_length=50

shorten_chatgpt_project_name() {
  local raw="$1"
  local max_len="${2:-${chatgpt_project_name_max_length}}"
  local clean hash head_len head
  clean="$(printf '%s' "${raw}" | sed -E 's/[^A-Za-z0-9_-]+/-/g; s/^[-_]+//; s/[-_]+$//')"
  if [[ -z "${clean}" ]]; then
    clean="itest-promptbranch"
  fi
  if (( ${#clean} <= max_len )); then
    printf '%s\n' "${clean}"
    return 0
  fi
  hash="$(printf '%s' "${clean}" | sha256sum | awk '{print substr($1,1,8)}')"
  head_len=$(( max_len - 9 ))
  if (( head_len < 1 )); then
    head_len=1
  fi
  head="${clean:0:head_len}"
  head="${head%-}"
  head="${head%_}"
  if [[ -z "${head}" ]]; then
    head="${clean:0:head_len}"
  fi
  printf '%s-%s\n' "${head}" "${hash}"
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
  if [[ "${raw}" =~ ^v?[0-9]+(\.[0-9]+){2,}$ ]]; then
    raw="${raw#v}"
    printf 'v%s\n' "${raw}"
    return 0
  fi
  # Accept noncanonical transport filenames such as
  # chatgpt_claudecode_workflow-2_v0.1.0.zip by extracting only the trailing
  # version token. This keeps input ZIP handling flexible while release output
  # uses the selected artifact identity.
  if [[ "${raw}" =~ (^|[_-])(v?[0-9]+(\.[0-9]+){2,})$ ]]; then
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
  if [[ "${raw}" =~ ^(.+)[_-]v?[0-9]+(\.[0-9]+){2,}$ ]]; then
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

args_include_skip_source_add() {
  local arg
  while [[ $# -gt 0 ]]; do
    arg="$1"
    case "${arg}" in
      --skip-source-add|--auth-only-validation)
        return 0
        ;;
      --)
        return 1
        ;;
      *)
        shift
        ;;
    esac
  done
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
    if args_include_skip_source_add "$@"; then
      export PROMPTBRANCH_RELEASE_SKIP_SOURCE_ADD=1
    fi
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
    --auth-only-validation) auth_only_validation=1; skip_source_add=1; shift ;;
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
    --test-transport)
      [[ $# -ge 2 ]] || fail "--test-transport requires direct, localhost, or both"
      test_transport="$2"
      shift 2
      ;;
    --test-transport=*) test_transport="${1#*=}"; shift ;;
    --localhost-base-url)
      [[ $# -ge 2 ]] || fail "--localhost-base-url requires a URL"
      localhost_base_url="$2"
      shift 2
      ;;
    --localhost-base-url=*) localhost_base_url="${1#*=}"; shift ;;
    --run-tests) skip_tests=0; shift ;;
    --run-all-tests)
      run_all_tests=1
      skip_tests=0
      test_transport="both"
      shift
      ;;
    --strict-source-kind-matrix)
      run_all_strict_source_kind_matrix=1
      shift
      ;;
    --run-failing-tests)
      run_failing_tests=1
      run_all_tests=1
      run_all_strict_source_kind_matrix=1
      skip_tests=0
      test_transport="both"
      shift
      ;;
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
    --adopt-after-validation)
      adopt_after_validation=1
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
case "${test_transport}" in
  direct|localhost|both) ;;
  *) fail "--test-transport must be direct, localhost, or both; got ${test_transport}" ;;
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
if [[ ${adopt_after_validation} -eq 1 && ${skip_tests} -eq 1 && ${auth_only_validation} -eq 0 ]]; then
  fail "--adopt-after-validation requires --run-tests or --run-all-tests unless --auth-only-validation is selected"
fi
if [[ ${adopt_after_validation} -eq 1 && ${tests_only} -eq 1 ]]; then
  fail "--adopt-after-validation is only supported with the full release workflow; use --tests-only --adopt-if-green for tests-only adoption"
fi
if [[ ${adopt_after_validation} -eq 1 && ${adopt_current} -eq 1 ]]; then
  fail "--adopt-after-validation cannot be combined with --adopt-current"
fi
if [[ ${adopt_after_validation} -eq 1 && ${adopt_if_green} -eq 1 ]]; then
  fail "--adopt-after-validation cannot be combined with --adopt-if-green"
fi
if [[ ${adopt_after_validation} -eq 1 && ${run_failing_tests} -eq 1 ]]; then
  fail "--adopt-after-validation cannot be combined with --run-failing-tests"
fi

if [[ ${import_plan} -eq 1 && ${skip_zip_import} -eq 1 ]]; then
  fail "--import-plan requires a candidate ZIP; do not combine it with --skip-zip-import"
fi
if [[ ${import_plan} -eq 1 && ${adopt_current} -eq 1 ]]; then
  fail "--import-plan cannot be combined with --adopt-current"
fi
if [[ ${import_plan} -eq 1 && ${adopt_after_validation} -eq 1 ]]; then
  fail "--import-plan cannot be combined with --adopt-after-validation"
fi

if [[ -z "${version_arg}" ]]; then
  if [[ ${install_from_zip} -eq 1 ]]; then
    version_arg="${install_zip}"
  else
    [[ -f "${version_file}" ]] || fail "VERSION file not found and no --version supplied: ${version_file}"
    version_arg="$(head -n 1 "${version_file}" | tr -d '[:space:]')"
  fi
fi

ver="$(normalize_version "${version_arg}")" || fail "version must be a v-prefixed or bare dotted numeric version with at least three numeric segments, or an artifact ZIP ending in such a version; got '${version_arg}'"
ver_plain="${ver#v}"
if [[ -z "${release_test_project_name}" ]]; then
  release_test_project_version="${ver//[^A-Za-z0-9]/-}"
  release_test_project_stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  release_test_project_name="$(shorten_chatgpt_project_name "itest-promptbranch-${release_test_project_version}-${release_test_project_stamp}")"
else
  [[ ${#release_test_project_name} -le ${chatgpt_project_name_max_length} ]] || fail "PROMPTBRANCH_RELEASE_TEST_PROJECT_NAME exceeds ChatGPT project-name limit (${chatgpt_project_name_max_length} chars): ${release_test_project_name}"
fi
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
case "${test_transport}" in
  direct)
    full_log="${release_log_dir}/pb_test.full.${ver}.log"
    report_json="${release_log_dir}/pb_test.full.${ver}.report.json"
    structured_summary_json="${release_log_dir}/post_release_validation.${ver}.summary.json"
    direct_full_log="${full_log}"
    direct_report_json="${report_json}"
    localhost_full_log=""
    localhost_report_json=""
    ;;
  localhost)
    full_log="${release_log_dir}/pb_test.full.localhost.${ver}.log"
    report_json="${release_log_dir}/pb_test.full.localhost.${ver}.report.json"
    structured_summary_json="${release_log_dir}/post_release_validation.localhost.${ver}.summary.json"
    direct_full_log=""
    direct_report_json=""
    localhost_full_log="${full_log}"
    localhost_report_json="${report_json}"
    ;;
  both)
    full_log="${release_log_dir}/pb_test.full.direct.${ver}.log"
    report_json="${release_log_dir}/pb_test.full.direct.${ver}.report.json"
    structured_summary_json="${release_log_dir}/post_release_validation.direct.${ver}.summary.json"
    direct_full_log="${full_log}"
    direct_report_json="${report_json}"
    localhost_full_log="${release_log_dir}/pb_test.full.localhost.${ver}.log"
    localhost_report_json="${release_log_dir}/pb_test.full.localhost.${ver}.report.json"
    ;;
esac
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
release_auth_bootstrap_json="${release_log_dir}/release_control_auth_bootstrap.${ver}.json"
service_pid_file="${release_log_dir}/promptbranch-service-start.${ver_plain}.pid"
all_tests_summary_json="${release_log_dir}/pb_test.all.${ver}.summary.json"
live_profile_preflight_json="${release_log_dir}/pb_test.live_profile_preflight.${ver}.json"
live_profile_preflight_raw_log="${release_log_dir}/pb_test.live_profile_preflight.${ver}.log"
run_all_project_ensure_log="${release_log_dir}/pb_test.live_project_ensure.${ver}.log"
run_all_shared_project_url=""
run_all_shared_conversation_url=""
run_all_browser_service_recovery_count=0
run_all_live_preflight_retried_after_service_recovery=0
run_all_release_validation_groups_passed_primary=0
ask_live_log="${release_log_dir}/pb_test.ask_live.${ver}.log"
visual_artifact_roundtrip_log="${release_log_dir}/pb_test.visual_artifact_roundtrip.${ver}.log"
release_live_log="${release_log_dir}/pb_test.release_live.${ver}.log"
import_smoke_log="${release_log_dir}/pb_test.import_smoke.${ver}.log"
artifact_guard_log="${release_log_dir}/pb_artifact_guard.${ver}.log"
validation_evidence_dir="${release_log_dir}/validation_evidence"
full_direct_validation_evidence_json="${validation_evidence_dir}/full_direct.${ver}.json"
live_profile_seed_dir="${PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_SEED_DIR:-./.pb_profile_local_debug}"
live_profile_seed_display="${live_profile_seed_dir}"
live_profile_pool_name="${PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_POOL:-release-live}"
live_profile_pool_size="${PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_POOL_SIZE:-1}"
live_profile_pool_slot_index="${PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_POOL_SLOT_INDEX:-1}"
live_profile_pool_slot_dir="${PROMPTBRANCH_RUN_ALL_LIVE_PROFILE_SLOT_DIR:-}"
if [[ -z "${live_profile_pool_slot_dir}" ]]; then
  live_profile_pool_slot_dir="$(python3 - "${live_profile_seed_dir}" "${live_profile_pool_name}" "${live_profile_pool_slot_index}" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import re
import sys
seed = Path(sys.argv[1])
pool = sys.argv[2]
slot_index = int(sys.argv[3])
safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", pool or "default").strip("._-") or "default"
print(str(seed.parent / f"{seed.name}_pools" / safe / "slots" / f"slot-{slot_index}"))
INNERPY
)"
fi
live_profile_pool_slot_display="${live_profile_pool_slot_dir}"
run_all_live_seed_profile_missing=0

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
  local preserved_csv=".git,.env,.generated,.pb_profile,.pb_profile_local_debug,.pb_profile_local_debug_pools,profile,debug_artifacts"
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
protected_zip_roots = [".env", ".generated", ".pb_profile", ".pb_profile_local_debug", ".pb_profile_local_debug_pools", "profile", "debug_artifacts"]
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
protected_roots = {".git", ".env", ".generated", ".pb_profile", ".pb_profile_local_debug", ".pb_profile_local_debug_pools", "profile", "debug_artifacts"}
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
      .env|.env.*|.generated|.generated/*|.pb_profile|.pb_profile/*|.pb_profile_local_debug|.pb_profile_local_debug/*|.pb_profile_local_debug_pools|.pb_profile_local_debug_pools/*|profile|profile/*|debug_artifacts|debug_artifacts/*|*.zip|*.tar.gz|*.log|*.trace|*.trace.zip|*.pyc|*.pyo|__pycache__|__pycache__/*|.pytest_cache|.pytest_cache/*|.mypy_cache|.mypy_cache/*|.ruff_cache|.ruff_cache/*)
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
  for candidate in "${repo_root}/.pb_profile" "${repo_root}/.pb_profile_local_debug" "${repo_root}/.pb_profile_local_debug_pools" "${repo_root}/debug_artifacts"; do
    if [[ -e "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
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

release_control_resolve_auth_bootstrap_url() {
  local phase="${1:-release_control}"
  python3 - "${repo_root}/.pb_profile/.promptbranch_state.json" "${service_base_url}" "${phase}" <<'INNERPY'
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

state_path = Path(sys.argv[1])
service_base_url = sys.argv[2]
phase = sys.argv[3]


def good(value: object) -> str | None:
    if isinstance(value, str) and value.startswith("https://chatgpt.com/"):
        return value
    return None


def parsed_parts(value: str) -> list[str]:
    return [part for part in urlparse(value).path.split("/") if part]


def is_project_conversation_url(value: str) -> bool:
    parts = parsed_parts(value)
    return len(parts) >= 4 and parts[0] == "g" and parts[2] == "c"


def is_project_page_url(value: str) -> bool:
    parts = parsed_parts(value)
    return len(parts) >= 3 and parts[0] == "g" and parts[2] == "project"


def project_home_identity(value: str | None) -> str | None:
    candidate = good(value)
    if not candidate:
        return None
    parts = parsed_parts(candidate)
    if len(parts) >= 2 and parts[0] == "g":
        return f"https://chatgpt.com/g/{parts[1]}/project"
    return None

try:
    payload = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
except Exception:
    payload = {}
if not isinstance(payload, dict):
    payload = {}

current = payload.get("current") if isinstance(payload.get("current"), dict) else {}
task = payload.get("task") if isinstance(payload.get("task"), dict) else {}
workspace = payload.get("workspace") if isinstance(payload.get("workspace"), dict) else {}
projects = payload.get("projects") if isinstance(payload.get("projects"), dict) else {}

sources: list[dict] = []
for source in (current, task, workspace, payload):
    if isinstance(source, dict):
        sources.append(source)
for value in projects.values():
    if isinstance(value, dict):
        sources.append(value)

conversation_keys = (
    "conversation_url",
    "current_conversation_url",
    "task_conversation_url",
)
project_keys = (
    "project_home_url",
    "current_project_home_url",
    "resolved_project_home_url",
    "project_url",
    "current_project_url",
    "url",
)

# Operator override for recovery/diagnostics. It must still be a project conversation
# when used for pre_tests so composer validation remains meaningful.
override = good(os.environ.get("PROMPTBRANCH_RELEASE_AUTH_BOOTSTRAP_PRE_TESTS_URL"))
if phase == "pre_tests" and override:
    if is_project_conversation_url(override):
        print(override)
        raise SystemExit(0)
    print(f"ERROR: PROMPTBRANCH_RELEASE_AUTH_BOOTSTRAP_PRE_TESTS_URL is not a project conversation URL: {override}", file=sys.stderr)
    raise SystemExit(65)

home_candidates: list[str] = []
for source in sources:
    for key in project_keys:
        value = good(source.get(key))
        if value and value not in home_candidates:
            home_candidates.append(value)
for source in sources:
    for key in conversation_keys:
        value = good(source.get(key))
        if value:
            home = project_home_identity(value)
            if home and home not in home_candidates:
                home_candidates.append(home)

conversation_candidates: list[str] = []
for source in sources:
    for key in conversation_keys:
        value = good(source.get(key))
        if value and is_project_conversation_url(value) and value not in conversation_candidates:
            conversation_candidates.append(value)
# Also accept task-list cache entries as a last state-backed source; this preserves
# query strings on remembered conversation_url values and avoids falling back to
# /project when a current/known task URL is already recorded under the project entry.
for source in sources:
    cache = source.get("task_list_cache") if isinstance(source.get("task_list_cache"), dict) else {}
    tasks = cache.get("tasks") if isinstance(cache.get("tasks"), list) else []
    for item in tasks:
        if not isinstance(item, dict):
            continue
        value = good(item.get("conversation_url"))
        if value and is_project_conversation_url(value) and value not in conversation_candidates:
            conversation_candidates.append(value)

if phase == "pre_tests":
    preferred_homes = {project_home_identity(value) for value in home_candidates if project_home_identity(value)}
    for value in conversation_candidates:
        home = project_home_identity(value)
        if not preferred_homes or home in preferred_homes:
            print(value)
            raise SystemExit(0)
    for value in conversation_candidates:
        print(value)
        raise SystemExit(0)

for value in conversation_candidates:
    print(value)
    raise SystemExit(0)
for value in home_candidates:
    if is_project_page_url(value):
        print(value)
        raise SystemExit(0)
try:
    import urllib.request
    with urllib.request.urlopen(service_base_url.rstrip("/") + "/healthz", timeout=2.0) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    value = good(data.get("project_url"))
    if value:
        print(value)
        raise SystemExit(0)
except Exception:
    pass
if phase == "pre_tests":
    print("ERROR: pre_tests auth bootstrap could not resolve a current project conversation URL; falling back to project page only if service health exposes one.", file=sys.stderr)
print("https://chatgpt.com/")
INNERPY
}

release_control_url_is_project_page() {
  python3 - "${1:-}" <<'INNERPY'
from __future__ import annotations
import sys
from urllib.parse import urlparse
url = sys.argv[1]
parts = [part for part in urlparse(url).path.split('/') if part]
raise SystemExit(0 if len(parts) >= 3 and parts[0] == 'g' and parts[2] == 'project' else 1)
INNERPY
}

release_control_clear_auth_bootstrap_held_session() {
  local phase="${1:-release_control}"
  local clear_log="${release_log_dir}/release_control_auth_bootstrap_clear_held_session.${phase}.${ver}.log"

  echo "== Release-control auth bootstrap held-session clear (${phase}) =="
  echo "output -> ${clear_log}"
  (
    echo "phase: ${phase}"
    echo "strategy: docker_compose_restart_service"
    echo "compose_project_name: ${compose_project_name}"
    echo "compose_service_name: ${compose_service_name}"
    echo "service_base_url: ${service_base_url}"
    echo "expected_version: ${ver#v}"
    echo "reason: clear in-memory held auth-readiness session after successful auth bootstrap while preserving browser profile on disk"
    if [[ "${phase}" == "pre_source_add" ]]; then
      echo "+ docker compose restart ${compose_service_name}"
      run_pre_source_add_docker_compose restart "${compose_service_name}" || exit $?
      local deadline=$((SECONDS + service_timeout_seconds))
      while (( SECONDS < deadline )); do
        if pre_source_add_service_version_ready >/dev/null 2>>"${clear_log}.health.stderr"; then
          echo "service_version_verified: ${ver#v}"
          exit 0
        fi
        sleep 2
      done
      echo "ERROR: service version did not become ready after held-session clear restart" >&2
      cat "${pre_source_add_service_health_json}" >&2 2>/dev/null || true
      exit 1
    else
      echo "+ docker compose restart ${compose_service_name}"
      run_docker_compose restart "${compose_service_name}" || exit $?
      wait_for_promptbranch_service_version || exit $?
      echo "service_version_verified: ${ver#v}"
    fi
  ) 2>&1 | tee "${clear_log}"
  return "${PIPESTATUS[0]}"
}

release_control_wait_for_no_held_auth_session() {
  local phase="${1:-release_control}"
  local bootstrap_url="${2:-}"
  local wait_log="${release_log_dir}/release_control_auth_bootstrap_release_wait.${phase}.${ver}.log"
  local max_wait="${PROMPTBRANCH_RELEASE_AUTH_BOOTSTRAP_RELEASE_WAIT_SECONDS:-90}"
  local poll_seconds="${PROMPTBRANCH_RELEASE_AUTH_BOOTSTRAP_RELEASE_POLL_SECONDS:-2}"

  echo "== Release-control auth bootstrap release wait (${phase}) =="
  echo "auth_bootstrap_release_wait_url: ${bootstrap_url}"
  echo "auth_bootstrap_release_wait_seconds: ${max_wait}"
  echo "output -> ${wait_log}"
  python3 - "${service_base_url}" "${HOME}/.config/promptbranch/config.json" "${max_wait}" "${poll_seconds}" "${bootstrap_url}" <<'INNERPY' 2>&1 | tee "${wait_log}"
from __future__ import annotations
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

base_url, config_path, max_wait_s, poll_s, target_url = sys.argv[1:6]
max_wait = int(max_wait_s)
poll = float(poll_s)
token = os.environ.get("CHATGPT_SERVICE_TOKEN", "")
if not token:
    try:
        cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
        token = str(cfg.get("service_token") or "")
    except Exception:
        token = ""

def status_url() -> str:
    url = base_url.rstrip("/") + "/v1/auth-readiness/session/status"
    if target_url:
        return url + "?" + urllib.parse.urlencode({"project_url": target_url})
    return url

def fetch() -> tuple[int | None, dict]:
    req = urllib.request.Request(status_url())
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            payload = {"error": str(exc)}
        return exc.code, payload
    except Exception as exc:
        return None, {"error": f"{type(exc).__name__}: {exc}"}

start = time.time()
last: dict = {}
last_code: int | None = None
while True:
    elapsed = time.time() - start
    code, payload = fetch()
    last = payload
    last_code = code
    held = payload.get("held_session") if isinstance(payload.get("held_session"), dict) else {}
    active = bool(held.get("active"))
    status = payload.get("status")
    print(json.dumps({
        "elapsed_seconds": round(elapsed, 3),
        "http_status": code,
        "status": status,
        "held_session_active": active,
        "current_url": payload.get("current_url"),
    }, sort_keys=True), flush=True)
    if status == "no_held_auth_readiness_session" or active is False:
        print(json.dumps({
            "ok": True,
            "status": "held_auth_session_released",
            "elapsed_seconds": round(elapsed, 3),
            "http_status": code,
            "target_url": target_url,
        }, indent=2, sort_keys=True))
        raise SystemExit(0)
    if elapsed >= max_wait:
        print(json.dumps({
            "ok": False,
            "status": "held_auth_session_release_timeout",
            "elapsed_seconds": round(elapsed, 3),
            "http_status": last_code,
            "target_url": target_url,
            "last_status": last,
        }, indent=2, sort_keys=True))
        raise SystemExit(1)
    time.sleep(poll)
INNERPY
  return "${PIPESTATUS[0]}"
}

pb_auth_bootstrap() {
  local phase="${1:-release_control}"
  local bootstrap_log="${release_log_dir}/release_control_auth_bootstrap.${phase}.${ver}.log"
  local bootstrap_url
  local bootstrap_keep_open_seconds="${PROMPTBRANCH_RELEASE_AUTH_BOOTSTRAP_KEEP_OPEN_SECONDS:-1}"

  if [[ ${auth_only_validation} -eq 1 ]]; then
    echo "Release-control auth bootstrap skipped for ${phase}: --auth-only-validation is already the auth bootstrap path."
    return 0
  fi
  if [[ ${skip_service} -eq 1 ]]; then
    echo "Release-control auth bootstrap skipped for ${phase}: --skip-service/tests-only/adopt-current path."
    return 0
  fi
  if [[ ! -x "./scripts/pb-browser-cloudflare-validation.sh" ]]; then
    echo "ERROR: auth bootstrap script missing or not executable: ./scripts/pb-browser-cloudflare-validation.sh" >&2
    return 1
  fi

  bootstrap_url="$(release_control_resolve_auth_bootstrap_url "${phase}")"
  local allow_project_page_ready=0
  local project_page_fallback=0
  if [[ "${phase}" == "pre_source_add" ]]; then
    allow_project_page_ready=1
  elif [[ "${phase}" == "pre_tests" ]] && release_control_url_is_project_page "${bootstrap_url}"; then
    project_page_fallback="${PROMPTBRANCH_RELEASE_AUTH_BOOTSTRAP_PRE_TESTS_PROJECT_PAGE_FALLBACK:-1}"
    if [[ "${project_page_fallback}" == "1" ]]; then
      allow_project_page_ready=1
    fi
  fi
  echo "== Release-control auth bootstrap (${phase}) =="
  echo "auth_bootstrap_url: ${bootstrap_url}"
  echo "pre_tests_project_page_fallback: ${project_page_fallback}"
  echo "allow_project_page_ready: ${allow_project_page_ready}"
  echo "output -> ${bootstrap_log}"
  PROMPTBRANCH_BROWSER_VALIDATION_URL="${bootstrap_url}" \
  PROMPTBRANCH_BROWSER_BOOTSTRAP_URL="${bootstrap_url}" \
  PROMPTBRANCH_BROWSER_VALIDATION_ALLOW_PROJECT_PAGE_READY="${allow_project_page_ready}" \
  PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS="${bootstrap_keep_open_seconds}" \
  ./scripts/pb-browser-cloudflare-validation.sh \
    --url "${bootstrap_url}" \
    --bootstrap-url "${bootstrap_url}" \
    --max-wait-seconds 300 \
    --poll-seconds 10 \
    2>&1 | tee "${bootstrap_log}"
  local bootstrap_rc=${PIPESTATUS[0]}
  if [[ ${bootstrap_rc} -eq 0 ]]; then
    release_control_clear_auth_bootstrap_held_session "${phase}" || return $?
    release_control_wait_for_no_held_auth_session "${phase}" "${bootstrap_url}" || return $?
  fi
  python3 - "${release_auth_bootstrap_json}" "${phase}" "${bootstrap_rc}" "${bootstrap_url}" "${bootstrap_log}" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
out, phase, rc, url, log = sys.argv[1:6]
payload = {
    "schema": "promptbranch.release_control.auth_bootstrap",
    "schema_version": "1.0",
    "source_kind": "release_control_auth_bootstrap",
    "generated_by": "chatgpt_claudecode_workflow_release_control.sh",
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "ok": int(rc) == 0,
    "status": "passed" if int(rc) == 0 else "failed",
    "phase": phase,
    "target_url": url,
    "log": log,
    "exit_code": int(rc),
}
Path(out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
INNERPY
  return "${bootstrap_rc}"
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
printf 'test_transport: %s\n' "${test_transport}"
printf 'run_all_tests:  %s\n' "${run_all_tests}"
printf 'run_failing_tests:  %s\n' "${run_failing_tests}"
printf 'run_all_strict_source_kind_matrix: %s\n' "${run_all_strict_source_kind_matrix}"
printf 'live_seed_dir:  %s\n' "${live_profile_seed_display}"
printf 'test_project:   %s\n' "${release_test_project_name}"
printf 'test_cleanup:   unique_project_delete_frozen_retained\n'
printf 'adopt_current:  %s\n' "${adopt_current}"
printf 'adopt_if_green: %s\n' "${adopt_if_green}"
printf 'adopt_after_validation: %s\n' "${adopt_after_validation}"
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
  find "${repo_root}" -mindepth 1 -maxdepth 1     ! -name ".git"     ! -name ".env"     ! -name ".generated"     ! -name ".pb_profile"     ! -name ".pb_profile_local_debug"     ! -name ".pb_profile_local_debug_pools"     ! -name "profile"     ! -name "debug_artifacts"     -exec rm -rf {} +

  rsync -a     --exclude='.git'     --exclude='.git/'     --exclude='.env'     --exclude='.env.*'     --exclude='.generated/'     --exclude='.pb_profile/'     --exclude='.pb_profile_local_debug/'     --exclude='.pb_profile_local_debug_pools/'     --exclude='profile/'     --exclude='debug_artifacts/'     "${work_dir}/" "${repo_root}/"

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

# Reinstall local CLI from the release ZIP before any service-mediated source
# mutation.  Clean hosts may not have a running Promptbranch service yet, and
# source-add must therefore be performed by the candidate runtime after the
# candidate service has been bootstrapped and version-verified.
if [[ ${skip_install} -eq 0 ]]; then
  pipx uninstall promptbranch || true
  pipx install "./${artifact_zip}"
fi

compose_file="${repo_root}/docker-compose.chatgpt-service.yml"
pre_source_add_service_health_json="${release_log_dir}/pre_source_add_service_health.${ver}.json"
pre_source_add_service_start_log="${release_log_dir}/pre_source_add_service_start.${ver}.log"
pre_source_add_docker_preflight_json="${release_log_dir}/pre_source_add_docker_preflight.${ver}.json"
pre_source_add_docker_compose_ps_json="${release_log_dir}/pre_source_add_docker_compose_ps.${ver}.json"
pre_source_add_docker_compose_logs_path="${release_log_dir}/pre_source_add_docker_compose_logs.${ver}.log"
pre_source_add_build_context_json="${release_log_dir}/pre_source_add_build_context.${ver}.json"

pre_source_add_release_artifact_sha256() {
  local path="${repo_root}/${artifact_zip}"
  if [[ -f "${path}" ]]; then
    python3 - "${path}" <<'INNERPY'
from pathlib import Path
import hashlib
import sys
path = Path(sys.argv[1])
h = hashlib.sha256()
with path.open('rb') as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b''):
        h.update(chunk)
print(h.hexdigest())
INNERPY
  else
    printf 'unknown\n'
  fi
}


promptbranch_source_fingerprint() {
  python3 - <<'INNERPY'
from pathlib import Path
import hashlib
files = ('VERSION', 'promptbranch_version.py', 'pyproject.toml')
digest = hashlib.sha256()
for rel in files:
    path = Path(rel)
    if not path.is_file():
        print('unknown')
        raise SystemExit(0)
    digest.update(rel.encode('utf-8'))
    digest.update(b'\0')
    digest.update(path.read_bytes())
    digest.update(b'\0')
print(digest.hexdigest())
INNERPY
}

refresh_docker_build_context_mtimes() {
  # ZIP-installed release files intentionally carry deterministic mtimes.
  # Docker/BuildKit local context snapshotting can miss same-size content
  # changes when mtimes are preserved, so refresh safe repo-local file mtimes
  # before service image builds. This changes no file contents and keeps Git
  # status clean while forcing Docker to see the current installed candidate.
  python3 - "${repo_root}" <<'INNERPY'
from pathlib import Path
import os
import sys
import time
root = Path(sys.argv[1]).resolve()
excluded_dirs = {
    '.git', '.pb_profile', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    '.venv', 'venv', 'env', 'node_modules', '__pycache__', 'debug_artifacts',
    'build', 'dist', 'coverage', '.cache'
}
now = time.time()
count = 0
for path in root.rglob('*'):
    rel_parts = path.relative_to(root).parts
    if any(part in excluded_dirs for part in rel_parts):
        continue
    if not path.is_file():
        continue
    try:
        os.utime(path, (now, now), follow_symlinks=False)
        count += 1
    except Exception:
        pass
print(f"docker_build_context_mtime_refresh_count={count}")
INNERPY
}

pre_source_add_service_image_tag() {
  if [[ -n "${PROMPTBRANCH_SERVICE_IMAGE_TAG:-}" ]]; then
    printf '%s\n' "${PROMPTBRANCH_SERVICE_IMAGE_TAG}"
    return 0
  fi
  printf '%s\n' "${ver#v}"
}

pre_source_add_service_image_ref() {
  local image_tag
  image_tag="$(pre_source_add_service_image_tag)"
  if [[ "${PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE:-0}" == "1" && -n "${PROMPTBRANCH_SERVICE_IMAGE:-}" ]]; then
    printf '%s\n' "${PROMPTBRANCH_SERVICE_IMAGE}"
    return 0
  fi
  printf 'promptbranch-service:%s\n' "${image_tag}"
}

run_pre_source_add_docker_compose() {
  local image_tag
  local image_ref
  local artifact_sha
  image_tag="$(pre_source_add_service_image_tag)"
  image_ref="$(pre_source_add_service_image_ref)"
  artifact_sha="$(pre_source_add_release_artifact_sha256)"
  local source_fingerprint
  source_fingerprint="$(promptbranch_source_fingerprint)"
  COMPOSE_PROJECT_NAME="${compose_project_name}" \
  PROMPTBRANCH_SERVICE_PORT="${service_port}" \
  CHATGPT_SERVICE_BASE_URL="${service_base_url}" \
  CHATGPT_FAIL_FAST_ON_CHALLENGE="${CHATGPT_FAIL_FAST_ON_CHALLENGE:-1}" \
  PROMPTBRANCH_SERVICE_IMAGE_TAG="${image_tag}" \
  PROMPTBRANCH_SERVICE_IMAGE="${image_ref}" \
  PROMPTBRANCH_VERSION="${ver#v}" \
  PROMPTBRANCH_ARTIFACT_SHA256="${artifact_sha}" \
  PROMPTBRANCH_SOURCE_FINGERPRINT="${source_fingerprint}" \
  docker compose --project-directory "${repo_root}" -p "${compose_project_name}" -f "${compose_file}" "$@"
}

pre_source_add_service_version_ready() {
  local expected_version_plain="${ver#v}"
  python3 - "${expected_version_plain}" "${pre_source_add_service_health_json}" "${service_port}" <<'INNERPY'
import json
import sys
import urllib.request
from datetime import datetime, timezone

expected = sys.argv[1]
out_path = sys.argv[2]
port = sys.argv[3]

def normalize(value):
    text = str(value or '').strip()
    return text[1:] if text.startswith('v') else text

last_error = None
for path in ('/healthz', '/health'):
    url = f'http://127.0.0.1:{port}{path}'
    try:
        with urllib.request.urlopen(url, timeout=2.0) as response:
            raw = response.read().decode('utf-8', errors='replace')
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {'raw': raw}
            actual = str(payload.get('package_version') or payload.get('version') or '')
            payload.update({
                'ok': normalize(actual) == normalize(expected),
                'status': 'verified' if normalize(actual) == normalize(expected) else 'pre_source_add_service_version_mismatch',
                'source_kind': 'pre_source_add_service_health',
                'expected_version': expected,
                'actual_version': actual,
                'url': url,
                'http_status': response.status,
                'checked_at': datetime.now(timezone.utc).isoformat(),
            })
            with open(out_path, 'w', encoding='utf-8') as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write('\n')
            raise SystemExit(0 if payload['ok'] else 1)
    except SystemExit:
        raise
    except Exception as exc:
        last_error = f'{url}: {exc}'
with open(out_path, 'w', encoding='utf-8') as handle:
    json.dump({
        'ok': False,
        'status': 'pre_source_add_service_unavailable',
        'source_kind': 'pre_source_add_service_health',
        'expected_version': expected,
        'error': last_error,
        'checked_at': datetime.now(timezone.utc).isoformat(),
    }, handle, indent=2, sort_keys=True)
    handle.write('\n')
raise SystemExit(1)
INNERPY
}

write_pre_source_add_docker_preflight() {
  python3 - "${pre_source_add_docker_preflight_json}" "${compose_project_name}" "${compose_service_name}" "${compose_file}" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
import json
import shutil
import subprocess
import sys

out, compose_project, compose_service, compose_file = sys.argv[1:5]

def run(args):
    try:
        proc = subprocess.run(args, text=True, capture_output=True, timeout=20)
        return {
            'args': args,
            'returncode': proc.returncode,
            'stdout_tail': proc.stdout[-4000:],
            'stderr_tail': proc.stderr[-4000:],
        }
    except Exception as exc:
        return {'args': args, 'error': repr(exc)}

payload = {
    'ok': False,
    'status': 'pre_source_add_docker_preflight_failed',
    'source_kind': 'pre_source_add_docker_preflight',
    'compose_project_name': compose_project,
    'compose_service_name': compose_service,
    'compose_file': compose_file,
    'docker_available': shutil.which('docker') is not None,
    'checked_at': datetime.now(timezone.utc).isoformat(),
    'checks': {},
}
if payload['docker_available']:
    payload['checks']['docker_version'] = run(['docker', 'version'])
    payload['checks']['docker_compose_version'] = run(['docker', 'compose', 'version'])
    payload['checks']['docker_context_show'] = run(['docker', 'context', 'show'])
    ok = (
        payload['checks']['docker_version'].get('returncode') == 0
        and payload['checks']['docker_compose_version'].get('returncode') == 0
    )
    payload['ok'] = ok
    payload['status'] = 'verified' if ok else 'pre_source_add_docker_preflight_failed'
with open(out, 'w', encoding='utf-8') as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write('\n')
raise SystemExit(0 if payload['ok'] else 1)
INNERPY
}

write_pre_source_add_build_context_snapshot() {
  python3 - "${pre_source_add_build_context_json}" "${repo_root}" "${compose_file}" "${compose_project_name}" "${compose_service_name}" "${ver#v}" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

out_path, repo_root, compose_file, compose_project, compose_service, expected_version = sys.argv[1:7]
root = Path(repo_root).resolve()
compose = Path(compose_file).resolve()

def read(path: Path) -> str | None:
    try:
        return path.read_text(encoding='utf-8').strip()
    except Exception:
        return None

def pyproject_version(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.M)
    return match.group(1) if match else None

def package_version(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r'^PACKAGE_VERSION\s*=\s*["\']([^"\']+)["\']', text, re.M)
    return match.group(1) if match else None

def norm(value: object) -> str:
    text = str(value or '').strip()
    return text[1:] if text.startswith('v') else text

def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None

def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for rel in ('VERSION', 'promptbranch_version.py', 'pyproject.toml'):
        path = root / rel
        digest.update(rel.encode('utf-8'))
        digest.update(b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()

version_text = read(root / 'VERSION')
pyproject_text = read(root / 'pyproject.toml')
promptbranch_version_text = read(root / 'promptbranch_version.py')
actuals = {
    'VERSION': version_text,
    'promptbranch_version.py': package_version(promptbranch_version_text),
    'pyproject.toml': pyproject_version(pyproject_text),
}
checks = {key: norm(value) == norm(expected_version) for key, value in actuals.items()}
compose_config = None
compose_config_error = None
try:
    proc = subprocess.run(
        ['docker', 'compose', '--project-directory', str(root), '-p', compose_project, '-f', str(compose), 'config'],
        text=True,
        capture_output=True,
        timeout=30,
    )
    compose_config = {
        'returncode': proc.returncode,
        'stdout_tail': proc.stdout[-12000:],
        'stderr_tail': proc.stderr[-4000:],
    }
except Exception as exc:
    compose_config_error = repr(exc)

payload = {
    'ok': all(checks.values()),
    'status': 'verified' if all(checks.values()) else 'pre_source_add_repo_version_surface_mismatch',
    'source_kind': 'pre_source_add_build_context',
    'checked_at': datetime.now(timezone.utc).isoformat(),
    'cwd': str(Path.cwd()),
    'repo_root': str(root),
    'compose_file': str(compose),
    'compose_project_name': compose_project,
    'compose_service_name': compose_service,
    'expected_version': expected_version,
    'actuals': actuals,
    'checks': checks,
    'source_fingerprint': source_fingerprint(),
    'file_sha256': {
        'VERSION': file_sha256(root / 'VERSION'),
        'promptbranch_version.py': file_sha256(root / 'promptbranch_version.py'),
        'pyproject.toml': file_sha256(root / 'pyproject.toml'),
    },
    'compose_config': compose_config,
    'compose_config_error': compose_config_error,
}
Path(out_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
raise SystemExit(0 if payload['ok'] else 1)
INNERPY
}

classify_pre_source_add_bootstrap_failure() {
  local reason="${1:-pre_source_add_bootstrap_command_failed}"
  local status="${reason}"
  if grep -q "Docker build context fingerprint mismatch" "${pre_source_add_service_start_log}" 2>/dev/null; then
    status="pre_source_add_docker_build_context_stale"
  elif grep -q "Docker build context version mismatch" "${pre_source_add_service_start_log}" 2>/dev/null; then
    status="pre_source_add_docker_build_context_version_mismatch"
  fi
  python3 - "${pre_source_add_service_health_json}" "${status}" "${ver#v}" "${pre_source_add_service_start_log}" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

out_path, status, expected, log_path = sys.argv[1:5]
log = Path(log_path)
text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
payload = {
    'ok': False,
    'status': status,
    'source_kind': 'pre_source_add_service_health',
    'expected_version': expected,
    'error': status,
    'bootstrap_log': str(log),
    'bootstrap_log_tail': text[-12000:],
    'checked_at': datetime.now(timezone.utc).isoformat(),
}
Path(out_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
raise SystemExit(0)
INNERPY
  printf '%s\n' "${status}"
}

write_pre_source_add_service_diagnostics() {
  local reason="$1"
  {
    echo "== Pre-source-add service bootstrap diagnostics =="
    echo "reason: ${reason}"
    echo "compose_project_name: ${compose_project_name}"
    echo "compose_service_name: ${compose_service_name}"
    echo "compose_file: ${compose_file}"
    echo "repo_root: ${repo_root}"
    echo "service_base_url: ${service_base_url}"
    echo "expected_version: ${ver#v}"
    echo "+ docker compose ps -a"
    run_pre_source_add_docker_compose ps -a || true
  } > "${pre_source_add_docker_compose_ps_json}" 2>"${pre_source_add_docker_compose_ps_json}.stderr" || true
  run_pre_source_add_docker_compose logs --tail=200 "${compose_service_name}" > "${pre_source_add_docker_compose_logs_path}" 2>"${pre_source_add_docker_compose_logs_path}.stderr" || true
}

ensure_service_before_source_add() {
  if pre_source_add_service_version_ready >/dev/null 2>"${pre_source_add_service_health_json}.stderr"; then
    rm -f "${pre_source_add_service_health_json}.stderr"
    echo "Pre-source-add Promptbranch service already verified: ${ver#v}"
    return 0
  fi

  if [[ ${skip_service} -ne 0 ]]; then
    echo "ERROR: pre_source_add_service_unavailable and --skip-service prevents bootstrap" >&2
    echo "ERROR: inspect pre_source_add_service_health_json=${pre_source_add_service_health_json}" >&2
    cat "${pre_source_add_service_health_json}" >&2 || true
    return 1
  fi

  need_cmd docker
  [[ -f "${compose_file}" ]] || fail "compose file not found before source add: ${compose_file}"
  [[ -x "./run_chatgpt_service.sh" ]] || chmod +x ./run_chatgpt_service.sh 2>/dev/null || true
  echo "Pre-source-add service unavailable or stale; bootstrapping candidate service before Project Source add."
  echo "output -> ${pre_source_add_service_start_log}"

  (
    echo "== Pre-source-add service bootstrap =="
    echo "compose_project_name: ${compose_project_name}"
    echo "compose_service_name: ${compose_service_name}"
    echo "compose_file: ${compose_file}"
    echo "service_base_url: ${service_base_url}"
    echo "expected_version: ${ver#v}"
    echo "service_image: $(pre_source_add_service_image_ref)"
    echo "artifact_sha256: $(pre_source_add_release_artifact_sha256)"
    echo "repo_root: ${repo_root}"
    echo "+ write_pre_source_add_docker_preflight"
    write_pre_source_add_docker_preflight
    echo "+ refresh_docker_build_context_mtimes"
    refresh_docker_build_context_mtimes
    echo "+ write_pre_source_add_build_context_snapshot"
    write_pre_source_add_build_context_snapshot
    echo "+ docker compose --project-directory ${repo_root} down --remove-orphans"
    run_pre_source_add_docker_compose down --remove-orphans || exit $?
    echo "+ docker compose --project-directory ${repo_root} build --no-cache --pull"
    run_pre_source_add_docker_compose build --no-cache --pull || exit $?
    echo "+ docker compose --project-directory ${repo_root} up -d --no-build --force-recreate --remove-orphans"
    run_pre_source_add_docker_compose up -d --no-build --force-recreate --remove-orphans || exit $?
    echo "+ docker compose ps ${compose_service_name}"
    run_pre_source_add_docker_compose ps "${compose_service_name}" || exit $?
  ) >"${pre_source_add_service_start_log}" 2>&1 || {
    bootstrap_status="$(classify_pre_source_add_bootstrap_failure "pre_source_add_bootstrap_command_failed")"
    write_pre_source_add_service_diagnostics "${bootstrap_status}"
    echo "ERROR: ${bootstrap_status}" >&2
    echo "ERROR: inspect pre_source_add_service_health_json=${pre_source_add_service_health_json}" >&2
    echo "ERROR: inspect pre_source_add_build_context_json=${pre_source_add_build_context_json}" >&2
    echo "ERROR: inspect pre_source_add_service_start_log=${pre_source_add_service_start_log}" >&2
    cat "${pre_source_add_service_health_json}" >&2 || true
    return 1
  }

  local deadline=$((SECONDS + service_timeout_seconds))
  while (( SECONDS < deadline )); do
    if pre_source_add_service_version_ready >/dev/null 2>"${pre_source_add_service_health_json}.stderr"; then
      rm -f "${pre_source_add_service_health_json}.stderr"
      echo "Pre-source-add Promptbranch service health/version verified: ${ver#v}"
      return 0
    fi
    sleep 2
  done

  write_pre_source_add_service_diagnostics "pre_source_add_service_unavailable"
  echo "ERROR: pre_source_add_service_unavailable" >&2
  echo "ERROR: inspect pre_source_add_service_health_json=${pre_source_add_service_health_json}" >&2
  echo "ERROR: inspect pre_source_add_service_start_log=${pre_source_add_service_start_log}" >&2
  cat "${pre_source_add_service_health_json}" >&2 || true
  return 1
}

# Add release ZIP to ChatGPT Project Sources.
# The CLI flag and PROMPTBRANCH_RELEASE_SKIP_SOURCE_ADD are both honored so
# Stage-0 candidate delegation cannot accidentally re-enable Project Source
# mutation after the operator explicitly selected --skip-source-add.
if [[ ${skip_source_add} -eq 0 && "${PROMPTBRANCH_RELEASE_SKIP_SOURCE_ADD:-0}" != "1" ]]; then
  ensure_service_before_source_add || fail "pre-source-add service bootstrap failed"
  pb_auth_bootstrap "pre_source_add" || fail "release-control auth bootstrap failed before Project Source add"
  promptbranch src add "${artifact_zip}"
else
  if [[ ${auth_only_validation} -eq 1 ]]; then
    echo "Source add skipped: --auth-only-validation"
  else
    echo "Source add skipped: --skip-source-add"
  fi
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

write_structured_full_test_summary() {
  local output_path="$1"
  local report_path="$2"
  local full_log_path="$3"
  local session_log_path="$4"
  local version_value="$5"
  local artifact_value="$6"
  local test_exit_code="$7"
  local report_exit_code="$8"
  local service_health_path="$9"
  python3 - "$output_path" "$report_path" "$full_log_path" "$session_log_path" "$version_value" "$artifact_value" "$test_exit_code" "$report_exit_code" "$service_health_path" <<'INNERPY'
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import sys

out = Path(sys.argv[1])
report_path = Path(sys.argv[2])
full_log_path = Path(sys.argv[3])
session_log_path = Path(sys.argv[4])
version = sys.argv[5]
artifact = sys.argv[6]
test_rc = int(sys.argv[7])
report_rc = int(sys.argv[8])
service_health_path = Path(sys.argv[9]) if sys.argv[9] else None


def read_json_object(path: Path) -> tuple[dict, str | None]:
    if not path.is_file():
        return {}, f"missing: {path}"
    raw = path.read_text(encoding="utf-8", errors="replace")
    idx = raw.find("{")
    if idx < 0:
        return {}, f"no JSON object found in {path}"
    try:
        return json.loads(raw[idx:]), None
    except Exception as exc:  # pragma: no cover - defensive shell boundary
        return {}, f"invalid JSON in {path}: {exc}"

report, report_error = read_json_object(report_path)
service_health, service_health_error = ({}, None)
if service_health_path:
    service_health, service_health_error = read_json_object(service_health_path)
full_log_text = full_log_path.read_text(encoding="utf-8", errors="replace") if full_log_path.is_file() else ""

def _lowered_full_evidence() -> str:
    try:
        return (json.dumps(report, sort_keys=True, ensure_ascii=False) + "\n" + full_log_text).lower()
    except Exception:
        return (str(report) + "\n" + full_log_text).lower()

def full_evidence_has_browser_read_timeout() -> bool:
    evidence = _lowered_full_evidence()
    return (
        "readtimeout" in evidence
        or "service_client_read_timeout" in evidence
        or "the browser service may still finish after the cli timed out" in evidence
    )

def full_evidence_has_source_add() -> bool:
    evidence = _lowered_full_evidence()
    return any(term in evidence for term in (
        "project_source_add_text",
        "source_add_text",
        "source_add",
        "project_source_add_file",
        "source_add_file",
        "source add",
        "project source add",
        "persistence_not_verified",
    ))

def full_evidence_has_rate_limit() -> bool:
    evidence = _lowered_full_evidence()
    return (
        "too many requests" in evidence
        or "temporarily limited access" in evidence
        or "status=429" in evidence
        or '"status": 429' in evidence
        or '"status":429' in evidence
        or '"rate_limit_modal_detected": true' in evidence
        or '"rate_limit_modal_detected":true' in evidence
        or '"conversation_history_429_seen": true' in evidence
        or '"conversation_history_429_seen":true' in evidence
        or '"status": "rate_limited_failed"' in evidence
    )

try:
    failure_count = int(report.get("failure_count") or 0)
except Exception:
    failure_count = 0
report_status = report.get("status")
report_ok = report.get("ok") is True
suite = report.get("suite") if isinstance(report.get("suite"), dict) else {}
release_validation_groups = suite.get("release_validation_groups") if isinstance(suite.get("release_validation_groups"), dict) else {}
required_groups = release_validation_groups.get("groups") if isinstance(release_validation_groups.get("groups"), dict) else {}
missing_required_groups = release_validation_groups.get("missing_required_groups") if isinstance(release_validation_groups.get("missing_required_groups"), list) else []
release_validation_groups_ok = bool(release_validation_groups.get("ok") is True and not missing_required_groups) if release_validation_groups else False
full_test_green = bool(test_rc == 0 and report_rc == 0 and report_ok and report_status == "verified" and failure_count == 0 and release_validation_groups_ok)
classification = report.get("validation_classification") if isinstance(report.get("validation_classification"), dict) else {}
if not classification:
    classification = {
        "status": "passed" if full_test_green else "failed",
        "primary_category": "none" if full_test_green else "full_test_or_report_failure",
        "blocking_categories": [] if full_test_green else ["full_test_or_report_failure"],
    }
primary_failure_category = report.get("primary_failure_category") or classification.get("primary_category") or ("none" if full_test_green else "full_test_or_report_failure")
blocking_failure_categories = report.get("blocking_failure_categories") or classification.get("blocking_categories") or ([] if full_test_green else [primary_failure_category])
browser_read_timeout_detected = full_evidence_has_browser_read_timeout()
source_add_evidence_detected = full_evidence_has_source_add()
rate_limit_evidence_detected = full_evidence_has_rate_limit()
rate_limit_retry_denied_detected = "rate_limit_retry_denied_for_offline_step" in full_log_text
if source_add_evidence_detected and browser_read_timeout_detected:
    likely_failure_phase = "project_source_add_read_timeout"
elif source_add_evidence_detected and not full_test_green:
    likely_failure_phase = "project_source_add"
elif browser_read_timeout_detected:
    likely_failure_phase = "browser_read_timeout"
elif rate_limit_evidence_detected and not full_test_green:
    likely_failure_phase = "rate_limit_blocking_or_contaminated"
elif full_test_green:
    likely_failure_phase = "none"
else:
    likely_failure_phase = "unclassified_full_test_failure"

summary = {
    "schema": "promptbranch.post_release_validation.summary",
    "schema_version": "1.0",
    "action": "post_release_validation",
    "source_kind": "release_control_full_test_summary",
    "generated_by": "chatgpt_claudecode_workflow_release_control.sh",
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "ok": full_test_green,
    "status": "verified" if full_test_green else "failed",
    "version": version,
    "target_version": version,
    "artifact": artifact,
    "failure_count": failure_count,
    "primary_failure_category": primary_failure_category,
    "blocking_failure_categories": blocking_failure_categories,
    "validation_classification": classification,
    "full_test_evidence": {
        "performed": True,
        "full_test_green": full_test_green,
        "test_exit_code": test_rc,
        "report_exit_code": report_rc,
        "full_log": str(full_log_path),
        "report_json": str(report_path),
        "test_session_log": str(session_log_path),
        "service_health_json": str(service_health_path) if service_health_path else None,
    },
    "test_report": {
        "path": str(report_path),
        "ok": report.get("ok"),
        "status": report_status,
        "failure_count": report.get("failure_count"),
        "error": report_error,
    },
    "release_validation_groups": {
        "ok": release_validation_groups_ok,
        "required_group_count": len(required_groups),
        "missing_required_groups": missing_required_groups,
        "groups": release_validation_groups,
    },
    "service_health": {
        "path": str(service_health_path) if service_health_path else None,
        "ok": service_health.get("ok"),
        "version": service_health.get("version"),
        "error": service_health_error,
    },
    "diagnostics": {
        "schema": "promptbranch.release_control.full_transport_diagnostics",
        "schema_version": "1.0",
        "browser_read_timeout_detected": browser_read_timeout_detected,
        "source_add_evidence_detected": source_add_evidence_detected,
        "source_add_timeout_detected": bool(source_add_evidence_detected and browser_read_timeout_detected),
        "rate_limit_evidence_detected": rate_limit_evidence_detected,
        "rate_limit_retry_denied": rate_limit_retry_denied_detected,
        "likely_failure_phase": likely_failure_phase,
        "full_log": str(full_log_path),
        "report_json": str(report_path),
        "next_action": (
            "inspect_source_add_timing_and_browser_service_log" if likely_failure_phase == "project_source_add_read_timeout"
            else "inspect_project_source_add_persistence_verification" if likely_failure_phase == "project_source_add"
            else "inspect_browser_service_recovery_and_timeout_window" if likely_failure_phase == "browser_read_timeout"
            else "rerun_later_or_reduce_history_enumeration" if likely_failure_phase == "rate_limit_blocking_or_contaminated"
            else "none" if likely_failure_phase == "none"
            else "inspect_full_test_log"
        ),
    },
    "limitations": [],
}
if report_error:
    summary["limitations"].append("The test report JSON could not be parsed; summary records the failed evidence boundary.")
if not release_validation_groups_ok:
    summary["limitations"].append("Required release-validation groups were missing or failed in the full-test report.")
if service_health_error:
    summary["limitations"].append("Service health JSON was missing or invalid when the full-test evidence summary was generated.")

out.parent.mkdir(parents=True, exist_ok=True)
tmp = out.with_name(out.name + ".tmp")
tmp.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
tmp.replace(out)
print(f"Structured full-test evidence summary written: {out}")
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
def artifact_current_entries(payload):
    repos = payload.get("repos")
    if isinstance(repos, dict):
        for repo_id in sorted(repos):
            repo_payload = repos.get(repo_id)
            if isinstance(repo_payload, dict):
                yield repo_id, repo_payload
        return
    if any(isinstance(payload.get(key), dict) for key in ("runtime", "state", "registry_current", "baseline_roles")):
        scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
        yield scope.get("repo_id"), payload

expected_artifact_name = Path(expected_artifact).name
failures = []
for repo_id, repo_payload in artifact_current_entries(payload):
    runtime = repo_payload.get("runtime") or {}
    state = repo_payload.get("state") or {}
    registry = repo_payload.get("registry_current") or {}
    consistency = repo_payload.get("consistency") or {}
    values = {
        "runtime.version": runtime.get("version"),
        "state.artifact_version": state.get("artifact_version"),
        "state.source_version": state.get("source_version"),
        "registry_current.version": registry.get("version"),
    }
    refs = {
        "state.artifact_ref": Path(str(state.get("artifact_ref") or "")).name,
        "state.source_ref": Path(str(state.get("source_ref") or "")).name,
        "registry_current.filename": Path(str(registry.get("filename") or "")).name,
    }
    consistency_ok = all(consistency.get(key) is True for key in ("registry_current_matches_state_artifact", "state_source_matches_state_artifact", "code_version_matches_state_source"))
    if all(value == expected_version for value in values.values()) and all(value == expected_artifact_name for value in refs.values()) and consistency_ok:
        raise SystemExit(0)
    failures.append({"repo_id": repo_id, "values": values, "refs": refs, "consistency": consistency})
raise SystemExit(f"no artifact current repo entry matched expected version/artifact: expected_version={expected_version}, expected_artifact={expected_artifact_name}, checked={failures!r}")
INNERPY
}

verify_all_tests_summary_green() {
  local path="$1"
  python3 - "$path" <<'INNERPY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
raw = path.read_text(encoding="utf-8", errors="replace")
idx = raw.find("{")
if idx < 0:
    raise SystemExit(f"invalid all-tests summary JSON in {path}: no JSON object found")
payload = json.loads(raw[idx:])
if payload.get("ok") is not True or payload.get("final_verdict") != "GO":
    raise SystemExit(f"all-tests summary is not GO in {path}")
INNERPY
}

verify_reused_full_direct_evidence_green() {
  local command_signature
  command_signature="$(release_validation_full_test_command_signature 0)"
  verify_all_tests_summary_green "${all_tests_summary_json}"
  validate_release_validation_reuse_evidence "${full_direct_validation_evidence_json}" "full_direct" "direct" "${service_base_url}" "${command_signature}" || \
    fail "run-all validation reuse evidence is missing or stale: ${full_direct_validation_evidence_json}"
}

verify_reused_full_localhost_lifecycle_green() {
  local command_signature
  command_signature="$(release_validation_full_test_command_signature 0)"
  verify_all_tests_summary_green "${all_tests_summary_json}"
  validate_release_validation_reuse_evidence "${full_direct_validation_evidence_json}" "full_direct" "direct" "${service_base_url}" "${command_signature}" || \
    fail "run-all localhost lifecycle reuse evidence is missing or stale: ${full_direct_validation_evidence_json}"
  python3 - "${all_tests_summary_json}" <<'INNERPY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
for step in steps:
    if not isinstance(step, dict):
        continue
    if step.get("name") != "full_localhost":
        continue
    status = step.get("status")
    action = step.get("action")
    if step.get("ok") is True and (status == "reused_browser_source_lifecycle" or action == "reused_browser_source_lifecycle"):
        raise SystemExit(0)
    raise SystemExit(f"full_localhost is not reused_browser_source_lifecycle in {path}: {step!r}")
raise SystemExit(f"full_localhost step not found in {path}")
INNERPY
}

report_or_reused_full_direct_evidence_green() {
  local path="$1"
  if [[ -f "${path}" ]]; then
    report_is_green "${path}"
    return 0
  fi
  if [[ ${run_all_tests} -eq 1 ]]; then
    verify_reused_full_direct_evidence_green
    return 0
  fi
  report_is_green "${path}"
}

report_or_reused_full_localhost_lifecycle_green() {
  local path="$1"
  if [[ -f "${path}" ]]; then
    report_is_green "${path}"
    return 0
  fi
  if [[ ${run_all_tests} -eq 1 ]]; then
    verify_reused_full_localhost_lifecycle_green
    return 0
  fi
  report_is_green "${path}"
}

verify_validation_reports_green() {
  case "${test_transport}" in
    direct)
      report_or_reused_full_direct_evidence_green "${report_json}"
      ;;
    localhost)
      report_or_reused_full_localhost_lifecycle_green "${report_json}"
      ;;
    both)
      report_or_reused_full_direct_evidence_green "${direct_report_json}"
      report_or_reused_full_localhost_lifecycle_green "${localhost_report_json}"
      ;;
  esac
  if [[ ${run_all_tests} -eq 1 ]]; then
    verify_all_tests_summary_green "${all_tests_summary_json}"
  fi
}


auth_only_validation_log="${release_log_dir}/standard_browser_auth_only_validation.${ver}.log"
auth_only_validation_summary_json="${release_log_dir}/standard_browser_auth_only_validation_summary.${ver}.json"
auth_only_validation_hygiene_json="${release_log_dir}/standard_browser_auth_only_hygiene.${ver}.json"

run_auth_only_hygiene_checks() {
  echo "== Auth-only hygiene checks =="
  python3 - "${auth_only_validation_hygiene_json}" <<'INNERPY'
from __future__ import annotations
import json
import subprocess
from pathlib import Path

checks: dict[str, object] = {}
errors: list[str] = []

def run(name: str, cmd: list[str]) -> None:
    completed = subprocess.run(cmd, text=True, capture_output=True)
    checks[name] = {
        "cmd": cmd,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }
    if completed.returncode != 0:
        errors.append(f"{name} failed with rc={completed.returncode}")

run("py_compile", ["python3", "-m", "py_compile", "promptbranch_browser_auth/client.py", "promptbranch_service_client.py", "promptbranch_version.py", "promptbranch_cli.py", "promptbranch_project_control.py"])
run("bash_n", ["bash", "-n", "scripts/pb-browser-cloudflare-validation.sh", "scripts/pb-browser-profile-bootstrap.sh", "scripts/pb-docker-browser-profile-bootstrap.sh", "scripts/docker-bonnetjes-cloudflare-validation.sh", "scripts/docker-bonnetjes-clean-login-profile-bootstrap.sh", "scripts/docker-bonnetjes-cloudflare-check.sh", "scripts/docker-browser-parity-cloudflare-check.sh", "scripts/docker-browser-parity-export-challenge-artifacts.sh", "docker/run-chatgpt-service-in-container.sh"])
run("no_tracked_profiles_debug_or_zips", ["bash", "-lc", "test -z \"$(git ls-files | grep -E '^\\.pb_profile|^debug_artifacts|\\.zip$' || true)\""])
run("no_history_profiles_weights_debug_or_zips", ["bash", "-lc", "test -z \"$(git rev-list --objects --all | grep -E '\\.zip$|\\.pb_profile|weights\\.bin|debug_artifacts' || true)\""])
run("dockerignore_profile_debug_zip_rules", ["bash", "-lc", "grep -q '^\\.pb_profile\\*' .dockerignore && grep -q '^\\.pb_profile_\\*' .dockerignore && grep -q '^debug_artifacts/' .dockerignore && grep -q '^\\*\\.zip$' .dockerignore"])

payload = {
    "ok": not errors,
    "action": "release_control_auth_only_hygiene",
    "status": "passed" if not errors else "failed",
    "checks": checks,
    "errors": errors,
}
Path(__import__('sys').argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
raise SystemExit(0 if not errors else 2)
INNERPY
}

run_auth_only_validation() {
  echo "== Auth-only standard browser Cloudflare validation =="
  run_auth_only_hygiene_checks || return $?
  local validation_start_epoch
  validation_start_epoch="$(date +%s)"
  ./scripts/pb-browser-cloudflare-validation.sh \
    --max-wait-seconds 300 \
    --poll-seconds 10 \
    2>&1 | tee "${auth_only_validation_log}"
  local validation_rc=${PIPESTATUS[0]}
  if [[ ${validation_rc} -ne 0 ]]; then
    return "${validation_rc}"
  fi
  python3 - "${repo_root}" "${validation_start_epoch}" "${auth_only_validation_summary_json}" <<'INNERPY'
from __future__ import annotations
import json
import sys
from pathlib import Path
repo = Path(sys.argv[1])
start_epoch = int(sys.argv[2])
out = Path(sys.argv[3])
base = repo / 'debug_artifacts' / 'docker-browser-parity' / 'standard-validation'
candidates = []
if base.exists():
    for path in base.glob('*/validation-summary.json'):
        try:
            if int(path.stat().st_mtime) >= start_epoch - 2:
                candidates.append(path)
        except OSError:
            pass
if not candidates:
    raise SystemExit('no standard browser validation-summary.json found for auth-only validation')
candidates.sort(key=lambda p: p.stat().st_mtime)
summary_path = candidates[-1]
payload = json.loads(summary_path.read_text(encoding='utf-8'))
if payload.get('ok') is not True or payload.get('status') != 'passed':
    raise SystemExit(f'standard browser validation did not pass: {payload!r}')
checks = payload.get('checks') if isinstance(payload.get('checks'), dict) else {}
required = {
    'cloudflare_cleared': True,
    'auth_ready': True,
    'logged_in': True,
    'challenge_detected': False,
    'composer_visible': True,
    'project_source_mutation_allowed': False,
    'standard_browser_mode': True,
}
errors = [f'{key} expected {expected!r} got {checks.get(key)!r}' for key, expected in required.items() if checks.get(key) is not expected]
if errors:
    raise SystemExit('; '.join(errors))
payload['release_control_auth_only_summary_path'] = str(summary_path)
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(payload, indent=2, sort_keys=True))
INNERPY
}

verify_auth_only_validation_green() {
  json_file_is_ok_true "${auth_only_validation_hygiene_json}"
  json_file_is_ok_true "${auth_only_validation_summary_json}"
  python3 - "${auth_only_validation_summary_json}" <<'INNERPY'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
if payload.get('status') != 'passed':
    raise SystemExit(f"auth-only validation status is not passed: {payload.get('status')!r}")
checks = payload.get('checks') if isinstance(payload.get('checks'), dict) else {}
required = {
    'cloudflare_cleared': True,
    'auth_ready': True,
    'logged_in': True,
    'challenge_detected': False,
    'composer_visible': True,
    'project_source_mutation_allowed': False,
    'standard_browser_mode': True,
}
for key, expected in required.items():
    if checks.get(key) is not expected:
        raise SystemExit(f"auth-only validation check {key} expected {expected!r} got {checks.get(key)!r}")
INNERPY
}

adopt_after_validation_if_green() {
  echo "== Adopt after validation =="
  if [[ ${workflow_rc} -ne 0 ]]; then
    fail "--adopt-after-validation refused adoption because validation failed with exit_code=${workflow_rc}"
  fi
  if [[ ${auth_only_validation} -eq 1 ]]; then
    verify_auth_only_validation_green
  else
    verify_validation_reports_green
  fi
  adopt_current_artifact
}

adopt_current_artifact() {
  local local_zip="${repo_root}/${artifact_zip}"
  local verify_json="${release_log_dir}/pb_artifact_verify.${ver}.json"
  local src_list_json="${release_log_dir}/pb_src_list.before_adopt.${ver}.json"
  local adopt_json="${release_log_dir}/pb_artifact_adopt.${ver}.json"
  local current_json="${release_log_dir}/pb_artifact_current.${ver}.json"

  if [[ ${auth_only_validation} -eq 1 ]]; then
    echo "== Adopt current local artifact (auth-only validation) =="
  else
    echo "== Adopt current Project Source artifact =="
  fi
  echo "artifact: ${artifact_zip}"
  echo "local_zip: ${local_zip}"

  [[ -f "${local_zip}" ]] || fail "local ZIP not found for adoption: ${local_zip}"

  echo "+ pb artifact verify ${local_zip} --json"
  pb artifact verify "${local_zip}" --json | tee "${verify_json}"
  json_file_is_ok_true "${verify_json}"

  if [[ ${auth_only_validation} -eq 1 ]]; then
    python3 - "${src_list_json}" <<'INNERPY_LOCAL_SRC'
import json
import sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({"ok": True, "status": "skipped_auth_only_validation", "project_source_required": False, "project_source_mutated": False}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
INNERPY_LOCAL_SRC
    echo "+ pb artifact adopt ${artifact_zip} --local-only --local-path ${local_zip} --json"
    pb artifact adopt "${artifact_zip}" --local-only --local-path "${local_zip}" --json | tee "${adopt_json}"
  else
    echo "+ pb src list --json"
    pb src list --json | tee "${src_list_json}"
    json_file_is_ok_true "${src_list_json}"
    verify_source_list_mentions_artifact "${src_list_json}"

    echo "+ pb artifact adopt ${artifact_zip} --from-project-source --local-path ${local_zip} --json"
    pb artifact adopt "${artifact_zip}" --from-project-source --local-path "${local_zip}" --json | tee "${adopt_json}"
  fi
  python3 - "${adopt_json}" "${auth_only_validation}" <<'INNERPY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
auth_only = sys.argv[2] == "1"
raw = path.read_text(encoding="utf-8", errors="replace")
idx = raw.find("{")
if idx < 0:
    raise SystemExit("artifact adopt output did not contain JSON")
payload = json.loads(raw[idx:])
if payload.get("ok") is not True:
    raise SystemExit("artifact adopt did not return ok:true")
expected_status = "adopted_local" if auth_only else "adopted"
if payload.get("status") != expected_status:
    raise SystemExit(f"artifact adopt status is not {expected_status}: {payload.get('status')!r}")
required_true = ["artifact_registry_updated", "state_artifact_updated", "state_source_updated"]
if not auth_only:
    required_true.insert(0, "source_verified")
for key in required_true:
    if payload.get(key) is not True:
        raise SystemExit(f"artifact adopt field {key} is not true")
if auth_only and payload.get("source_verified") not in (False, None):
    raise SystemExit("auth-only local adoption unexpectedly source-verified Project Sources")
if payload.get("project_source_mutated") is not False:
    raise SystemExit("artifact adopt unexpectedly mutated Project Sources")
if auth_only and payload.get("adoption_mode") != "local_only":
    raise SystemExit(f"auth-only adoption_mode is not local_only: {payload.get('adoption_mode')!r}")
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

release_version_plain_from_version_file() {
  local version_file="VERSION"
  [[ -f "${version_file}" ]] || return 1
  local value
  value="$(tr -d '\r\n[:space:]' < "${version_file}")"
  value="${value#v}"
  [[ -n "${value}" ]] || return 1
  printf '%s\n' "${value}"
}

promptbranch_service_image_tag() {
  if [[ -n "${PROMPTBRANCH_SERVICE_IMAGE_TAG:-}" ]]; then
    printf '%s\n' "${PROMPTBRANCH_SERVICE_IMAGE_TAG}"
    return 0
  fi
  release_version_plain_from_version_file
}

promptbranch_service_image_ref() {
  local image_tag
  image_tag="$(promptbranch_service_image_tag)"
  local default_image="promptbranch-service:${image_tag}"
  if [[ "${PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE:-0}" == "1" && -n "${PROMPTBRANCH_SERVICE_IMAGE:-}" ]]; then
    printf '%s\n' "${PROMPTBRANCH_SERVICE_IMAGE}"
    return 0
  fi
  printf '%s\n' "${default_image}"
}

release_artifact_sha256() {
  local path="${repo_root}/${artifact_zip}"
  if [[ -f "${path}" ]]; then
    python3 - "${path}" <<'INNERPY'
from pathlib import Path
import hashlib
import sys
path = Path(sys.argv[1])
h = hashlib.sha256()
with path.open('rb') as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b''):
        h.update(chunk)
print(h.hexdigest())
INNERPY
  else
    printf 'unknown
'
  fi
}

compose_env_prefix() {
  local image_tag
  local image_ref
  local artifact_sha
  image_tag="$(promptbranch_service_image_tag)"
  image_ref="$(promptbranch_service_image_ref)"
  artifact_sha="$(release_artifact_sha256)"
  local source_fingerprint
  source_fingerprint="$(promptbranch_source_fingerprint)"
  printf 'COMPOSE_PROJECT_NAME=%q PROMPTBRANCH_SERVICE_PORT=%q CHATGPT_SERVICE_BASE_URL=%q PROMPTBRANCH_SERVICE_IMAGE_TAG=%q PROMPTBRANCH_SERVICE_IMAGE=%q PROMPTBRANCH_VERSION=%q PROMPTBRANCH_ARTIFACT_SHA256=%q PROMPTBRANCH_SOURCE_FINGERPRINT=%q' \
    "${compose_project_name}" "${service_port}" "${service_base_url}" "${image_tag}" "${image_ref}" "${ver#v}" "${artifact_sha}" "${source_fingerprint}"
}

run_docker_compose() {
  local image_tag
  local image_ref
  local artifact_sha
  image_tag="$(promptbranch_service_image_tag)"
  image_ref="$(promptbranch_service_image_ref)"
  artifact_sha="$(release_artifact_sha256)"
  local source_fingerprint
  source_fingerprint="$(promptbranch_source_fingerprint)"
  COMPOSE_PROJECT_NAME="${compose_project_name}" \
  PROMPTBRANCH_SERVICE_PORT="${service_port}" \
  CHATGPT_SERVICE_BASE_URL="${service_base_url}" \
  CHATGPT_FAIL_FAST_ON_CHALLENGE="${CHATGPT_FAIL_FAST_ON_CHALLENGE:-1}" \
  PROMPTBRANCH_SERVICE_IMAGE_TAG="${image_tag}" \
  PROMPTBRANCH_SERVICE_IMAGE="${image_ref}" \
  PROMPTBRANCH_VERSION="${ver#v}" \
  PROMPTBRANCH_ARTIFACT_SHA256="${artifact_sha}" \
  PROMPTBRANCH_SOURCE_FINGERPRINT="${source_fingerprint}" \
  docker compose -p "${compose_project_name}" -f "${compose_file}" "$@"
}

service_health_json="${release_log_dir}/promptbranch_service_health.${ver}.json"
service_container_before_json="${release_log_dir}/docker_container_before.${ver}.json"
service_container_after_json="${release_log_dir}/docker_container_after.${ver}.json"
service_compose_ps_json="${release_log_dir}/docker_compose_ps.${ver}.json"
docker_host_context_json="${release_log_dir}/docker_host_build_context.${ver}.json"
docker_image_content_json="${release_log_dir}/docker_image_content.${ver}.json"
docker_image_content_nocache_json="${release_log_dir}/docker_image_content.nocache.${ver}.json"
docker_container_content_json="${release_log_dir}/docker_container_content.${ver}.json"
docker_image_inspect_json="${release_log_dir}/docker_image_inspect.${ver}.json"
docker_preflight_json="${release_log_dir}/docker_preflight.${ver}.json"
docker_compose_config_json="${release_log_dir}/docker_compose_config.${ver}.json"
docker_compose_ps_all_json="${release_log_dir}/docker_compose_ps_all.${ver}.json"
docker_compose_logs_path="${release_log_dir}/docker_compose_logs.${ver}.log"

write_version_probe_json() {
  local output="$1"
  local source_kind="$2"
  local phase="$3"
  local raw_path="$4"
  local extra_json="${5:-{}}"
  python3 - "$output" "$source_kind" "$phase" "${ver#v}" "$raw_path" "$extra_json" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
out, source_kind, phase, expected, raw_path, extra_raw = sys.argv[1:7]
def norm(value: str) -> str:
    return str(value or '').strip().removeprefix('v')
raw = Path(raw_path).read_text(encoding='utf-8', errors='replace') if Path(raw_path).exists() else ''
actuals = {}
for line in raw.splitlines():
    if '	' not in line:
        continue
    key, value = line.split('	', 1)
    actuals[key.strip()] = norm(value)
for key in ('VERSION', 'promptbranch_version.py', 'pyproject.toml'):
    actuals.setdefault(key, '')
ok = all(actuals[key] == norm(expected) for key in ('VERSION', 'promptbranch_version.py', 'pyproject.toml'))
try:
    extra = json.loads(extra_raw) if extra_raw else {}
except Exception as exc:
    extra = {'extra_parse_error': str(exc), 'extra_raw': extra_raw}
payload = {
    'ok': ok,
    'status': 'verified' if ok else f'{source_kind}_version_mismatch',
    'source_kind': source_kind,
    'phase': phase,
    'expected_version': norm(expected),
    'actuals': actuals,
    'raw_log': raw_path,
    'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
}
payload.update(extra)
Path(out).write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
raise SystemExit(0 if ok else 1)
INNERPY
}

assert_host_build_context_versions() {
  local raw_path="${docker_host_context_json}.raw"
  {
    printf 'VERSION\t'
    cat VERSION 2>/dev/null || true
    printf 'promptbranch_version.py\t'
    python3 - <<'INNERPY'
import promptbranch_version
print(promptbranch_version.PACKAGE_VERSION)
INNERPY
    printf 'pyproject.toml\t'
    python3 - <<'INNERPY'
from pathlib import Path
import tomllib
with Path('pyproject.toml').open('rb') as handle:
    print(tomllib.load(handle)['project']['version'])
INNERPY
  } > "${raw_path}"
  if write_version_probe_json "${docker_host_context_json}" "docker_host_build_context" "pre_build" "${raw_path}"; then
    echo "Docker host build context version verified: ${ver#v}"
    return 0
  fi
  echo "ERROR: docker_build_context_version_mismatch before Docker build" >&2
  echo "ERROR: inspect docker_host_context_json=${docker_host_context_json}" >&2
  cat "${docker_host_context_json}" >&2 || true
  return 1
}

docker_image_version_probe() {
  local output="$1"
  local phase="$2"
  local image_ref
  local raw_path="${output}.raw"
  local stderr_path="${output}.stderr"
  image_ref="$(promptbranch_service_image_ref)"
  if ! docker run --rm --entrypoint sh "${image_ref}" -lc 'set -eu
printf "VERSION\t"; cat /app/VERSION
printf "promptbranch_version.py\t"; python3 -c "import promptbranch_version; print(promptbranch_version.PACKAGE_VERSION)"
printf "pyproject.toml\t"; grep -E "^version = " /app/pyproject.toml | head -n 1 | cut -d "\"" -f 2
' > "${raw_path}" 2>"${stderr_path}"; then
    python3 - "$output" "$phase" "${ver#v}" "${image_ref}" "${stderr_path}" <<'INNERPY'
from pathlib import Path
import json
import sys
out, phase, expected, image_ref, stderr_path = sys.argv[1:6]
stderr = Path(stderr_path).read_text(encoding='utf-8', errors='replace') if Path(stderr_path).exists() else ''
Path(out).write_text(json.dumps({
    'ok': False,
    'status': 'docker_image_content_probe_failed',
    'source_kind': 'docker_image_content',
    'phase': phase,
    'expected_version': expected,
    'image': image_ref,
    'stderr': stderr,
}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
INNERPY
    return 1
  fi
  write_version_probe_json "${output}" "docker_image_content" "${phase}" "${raw_path}" "{\"image\":\"${image_ref}\"}"
}

docker_container_version_probe() {
  local output="$1"
  local container="$2"
  local raw_path="${output}.raw"
  local stderr_path="${output}.stderr"
  if [[ -z "${container}" ]]; then
    python3 - "${output}" "${compose_project_name}" "${compose_service_name}" "${ver#v}" <<'INNERPY'
from pathlib import Path
import json
import sys
out, compose_project_name, compose_service_name, expected_version = sys.argv[1:5]
Path(out).write_text(json.dumps({
    "ok": False,
    "status": "docker_service_container_missing_after_recreate",
    "source_kind": "docker_container_content",
    "expected_version": expected_version,
    "compose_project_name": compose_project_name,
    "compose_service_name": compose_service_name,
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
INNERPY
    return 1
  fi
  if ! docker exec "${container}" sh -lc 'set -eu
printf "VERSION\t"; cat /app/VERSION
printf "promptbranch_version.py\t"; python3 -c "import promptbranch_version; print(promptbranch_version.PACKAGE_VERSION)"
printf "pyproject.toml\t"; grep -E "^version = " /app/pyproject.toml | head -n 1 | cut -d "\"" -f 2
' > "${raw_path}" 2>"${stderr_path}"; then
    python3 - "$output" "${ver#v}" "${container}" "${stderr_path}" <<'INNERPY'
from pathlib import Path
import json
import sys
out, expected, container, stderr_path = sys.argv[1:5]
stderr = Path(stderr_path).read_text(encoding='utf-8', errors='replace') if Path(stderr_path).exists() else ''
Path(out).write_text(json.dumps({
    'ok': False,
    'status': 'docker_container_content_probe_failed',
    'source_kind': 'docker_container_content',
    'expected_version': expected,
    'container': container,
    'stderr': stderr,
}, indent=2, sort_keys=True) + '\n', encoding='utf-8')
INNERPY
    return 1
  fi
  write_version_probe_json "${output}" "docker_container_content" "running_container" "${raw_path}" "{\"container\":\"${container}\"}"
}

docker_release_preflight() {
  python3 - "${docker_preflight_json}" "${compose_project_name}" "${compose_service_name}" "${compose_file}" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import subprocess
import sys

out, compose_project, compose_service, compose_file = sys.argv[1:5]

def run(cmd):
    try:
        completed = subprocess.run(cmd, text=True, capture_output=True, timeout=20)
        return {
            "cmd": cmd,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    except Exception as exc:  # pragma: no cover - defensive runtime diagnostics
        return {"cmd": cmd, "error": repr(exc)}

payload = {
    "ok": False,
    "status": "docker_preflight_failed",
    "source_kind": "docker_preflight",
    "compose_project_name": compose_project,
    "compose_service_name": compose_service,
    "compose_file": compose_file,
    "docker_available": shutil.which("docker") is not None,
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "checks": {},
}
if payload["docker_available"]:
    payload["checks"]["docker_version"] = run(["docker", "version"])
    payload["checks"]["docker_compose_version"] = run(["docker", "compose", "version"])
    payload["checks"]["docker_context_show"] = run(["docker", "context", "show"])
    payload["checks"]["docker_info"] = run(["docker", "info"])
    ok = (
        payload["checks"]["docker_version"].get("returncode") == 0
        and payload["checks"]["docker_compose_version"].get("returncode") == 0
    )
    payload["ok"] = bool(ok)
    payload["status"] = "verified" if ok else "docker_preflight_failed"
Path(out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if payload["ok"] else 1)
INNERPY
}

compose_service_container_id() {
  if ! command -v docker >/dev/null 2>&1; then
    return 0
  fi
  run_docker_compose ps -q "${compose_service_name}" 2>/dev/null | head -n 1 || true
}

write_container_inspect_json() {
  local container="$1"
  local output="$2"
  if [[ -z "${container}" ]]; then
    python3 - "${output}" "${compose_project_name}" "${compose_service_name}" "${ver#v}" <<'INNERPY'
from pathlib import Path
import json
import sys
out, compose_project_name, compose_service_name, expected_version = sys.argv[1:5]
Path(out).write_text(json.dumps({
    "ok": False,
    "status": "docker_service_container_missing_after_recreate",
    "source_kind": "docker_container_inspect",
    "expected_version": expected_version,
    "compose_project_name": compose_project_name,
    "compose_service_name": compose_service_name,
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
INNERPY
    return 0
  fi
  if docker inspect "${container}" > "${output}" 2>"${output}.stderr"; then
    rm -f "${output}.stderr"
  else
    printf '{"ok":false,"status":"docker_inspect_failed","container":"%s"}
' "${container}" > "${output}"
  fi
}

write_docker_service_diagnostics() {
  local reason="$1"
  echo "Collecting Docker service diagnostics: ${reason}" >&2
  run_docker_compose ps -a > "${docker_compose_ps_all_json}" 2>"${docker_compose_ps_all_json}.stderr" || true
  run_docker_compose logs --tail=200 "${compose_service_name}" > "${docker_compose_logs_path}" 2>"${docker_compose_logs_path}.stderr" || true
  run_docker_compose config > "${docker_compose_config_json}" 2>"${docker_compose_config_json}.stderr" || true
  docker context show > "${docker_preflight_json}.context" 2>"${docker_preflight_json}.context.stderr" || true
  docker info > "${docker_preflight_json}.info" 2>"${docker_preflight_json}.info.stderr" || true
}

wait_for_compose_service_container() {
  local phase="$1"
  local deadline=$((SECONDS + service_timeout_seconds))
  local detected=""
  local state=""
  local health=""
  while (( SECONDS < deadline )); do
    detected="$(compose_service_container_id)"
    if [[ -n "${detected}" ]]; then
      state="$(docker inspect -f '{{.State.Status}}' "${detected}" 2>/dev/null || true)"
      health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${detected}" 2>/dev/null || true)"
      if [[ "${state}" == "running" && ( "${health}" == "healthy" || "${health}" == "none" || -z "${health}" ) ]]; then
        printf '%s\n' "${detected}"
        return 0
      fi
      if [[ "${state}" == "exited" || "${state}" == "dead" ]]; then
        break
      fi
    fi
    sleep 2
  done
  python3 - "${service_container_after_json}" "${phase}" "${compose_project_name}" "${compose_service_name}" "${ver#v}" "${detected}" "${state}" "${health}" <<'INNERPY'
from pathlib import Path
import json
import sys
out, phase, compose_project_name, compose_service_name, expected_version, container, state, health = sys.argv[1:9]
status = "docker_service_container_missing_after_recreate" if not container else "docker_service_container_not_running_after_recreate"
Path(out).write_text(json.dumps({
    "ok": False,
    "status": status,
    "source_kind": "docker_container_inspect",
    "phase": phase,
    "expected_version": expected_version,
    "compose_project_name": compose_project_name,
    "compose_service_name": compose_service_name,
    "container": container or None,
    "state": state or None,
    "health": health or None,
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
INNERPY
  return 1
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

def normalize_version(value):
    text = str(value or "").strip()
    if text.startswith("v"):
        text = text[1:]
    return text

expected_normalized = normalize_version(expected)
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
            actual = str(payload.get("package_version") or payload.get("version") or "")
            actual_normalized = normalize_version(actual)
            if actual_normalized == expected_normalized:
                raise SystemExit(0)
            raise SystemExit(
                "service version mismatch: "
                f"expected {expected} (normalized {expected_normalized}), "
                f"got {actual!r} (normalized {actual_normalized})"
            )
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
  local image_probe_failed=0
  before_container="$(compose_service_container_id)"
  write_container_inspect_json "${before_container}" "${service_container_before_json}"

  {
    echo "== Docker service recreate =="
    echo "compose_file: ${compose_file}"
    echo "runtime_mode: ${runtime_mode}"
    echo "compose_project_name: ${compose_project_name}"
    echo "compose_service_name: ${compose_service_name}"
    echo "service_port: ${service_port}"
    echo "service_base_url: ${service_base_url}"
    echo "service_image: $(promptbranch_service_image_ref)"
    echo "expected_version: ${ver#v}"
    echo "artifact_sha256: $(release_artifact_sha256)"
    echo "+ docker_release_preflight"
    docker_release_preflight
    echo "+ refresh_docker_build_context_mtimes"
    refresh_docker_build_context_mtimes
    echo "+ assert_host_build_context_versions"
    assert_host_build_context_versions
    echo "+ $(compose_env_prefix) docker compose -p ${compose_project_name} -f ${compose_file} down --remove-orphans"
    run_docker_compose down --remove-orphans
    echo "+ $(compose_env_prefix) docker compose -p ${compose_project_name} -f ${compose_file} build --pull"
    run_docker_compose build --pull
    echo "+ docker image content probe ${docker_image_content_json}"
    if docker_image_version_probe "${docker_image_content_json}" "normal_build"; then
      echo "+ docker image inspect $(promptbranch_service_image_ref)"
      docker image inspect "$(promptbranch_service_image_ref)" > "${docker_image_inspect_json}" 2>/dev/null || true
      echo "+ $(compose_env_prefix) docker compose -p ${compose_project_name} -f ${compose_file} up -d --no-build --force-recreate --remove-orphans"
      run_docker_compose up -d --no-build --force-recreate --remove-orphans
      echo "+ $(compose_env_prefix) docker compose -p ${compose_project_name} -f ${compose_file} ps ${compose_service_name}"
      run_docker_compose ps "${compose_service_name}"
      run_docker_compose ps --format json "${compose_service_name}" > "${service_compose_ps_json}" 2>/dev/null || true
    else
      image_probe_failed=1
      echo "WARN: Docker image content probe failed after normal build; skipping container start before no-cache fallback."
    fi
  } >"${service_start_log}" 2>&1

  if [[ ${image_probe_failed} -eq 0 ]]; then
    if container_id="$(wait_for_compose_service_container normal_recreate)"; then
      write_container_inspect_json "${container_id}" "${service_container_after_json}"

      if [[ -n "${before_container}" && -n "${container_id}" && "${before_container}" == "${container_id}" ]]; then
        echo "ERROR: Docker container was not recreated; before and after container IDs are both ${container_id}" >&2
        echo "ERROR: inspect service_start_log=${service_start_log}" >&2
        write_docker_service_diagnostics "container_id_not_recreated"
        return 1
      fi

      if ! docker_container_version_probe "${docker_container_content_json}" "${container_id}"; then
        echo "ERROR: Docker running container content version mismatch before health probe" >&2
        echo "ERROR: inspect docker_container_content_json=${docker_container_content_json}" >&2
        cat "${docker_container_content_json}" >&2 || true
      fi

      if wait_for_promptbranch_service_version; then
        return 0
      fi
    else
      echo "WARN: Docker service container was not running after normal recreate; trying no-cache fallback." >&2
      echo "WARN: inspect service_container_after_json=${service_container_after_json}" >&2
      cat "${service_container_after_json}" >&2 || true
      write_docker_service_diagnostics "normal_recreate_container_not_running"
    fi
  fi

  echo "WARN: Docker service reported a stale or unexpected version after normal rebuild; retrying with no-cache image rebuild." >&2
  echo "WARN: normal build may have reused a stale Docker layer or old local image tag." >&2
  {
    echo "== Docker service no-cache rebuild fallback =="
    echo "reason: service or image content version did not match expected ${ver#v} after normal recreate"
    echo "+ refresh_docker_build_context_mtimes"
    refresh_docker_build_context_mtimes
    echo "+ assert_host_build_context_versions"
    assert_host_build_context_versions
    echo "+ $(compose_env_prefix) docker compose -p ${compose_project_name} -f ${compose_file} down --remove-orphans"
    run_docker_compose down --remove-orphans
    echo "+ $(compose_env_prefix) docker compose -p ${compose_project_name} -f ${compose_file} build --no-cache --pull"
    run_docker_compose build --no-cache --pull
    echo "+ docker image content probe ${docker_image_content_nocache_json}"
    docker_image_version_probe "${docker_image_content_nocache_json}" "no_cache_build"
    echo "+ docker image inspect $(promptbranch_service_image_ref)"
    docker image inspect "$(promptbranch_service_image_ref)" > "${docker_image_inspect_json}" 2>/dev/null || true
    echo "+ $(compose_env_prefix) docker compose -p ${compose_project_name} -f ${compose_file} up -d --no-build --force-recreate --remove-orphans"
    run_docker_compose up -d --no-build --force-recreate --remove-orphans
    echo "+ $(compose_env_prefix) docker compose -p ${compose_project_name} -f ${compose_file} ps ${compose_service_name}"
    run_docker_compose ps "${compose_service_name}"
    run_docker_compose ps --format json "${compose_service_name}" > "${service_compose_ps_json}" 2>/dev/null || true
  } >>"${service_start_log}" 2>&1

  if ! container_id="$(wait_for_compose_service_container no_cache_recreate)"; then
    echo "ERROR: Docker service container missing or not running after no-cache rebuild" >&2
    echo "ERROR: inspect service_container_after_json=${service_container_after_json}" >&2
    cat "${service_container_after_json}" >&2 || true
    write_docker_service_diagnostics "no_cache_recreate_container_not_running"
    return 1
  fi
  write_container_inspect_json "${container_id}" "${service_container_after_json}"
  docker_container_version_probe "${docker_container_content_json}" "${container_id}" || {
    echo "ERROR: Docker running container content version mismatch after no-cache rebuild" >&2
    echo "ERROR: inspect docker_container_content_json=${docker_container_content_json}" >&2
    cat "${docker_container_content_json}" >&2 || true
    write_docker_service_diagnostics "no_cache_container_content_version_mismatch"
    return 1
  }
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

run_all_log_has_backend_api_guardrail_403() {
  local log_path="$1"
  [[ -f "${log_path}" ]] || return 1
  python3 - "${log_path}" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import json
import re
import sys
raw = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
text = "\n".join(
    line for line in raw.splitlines()
    if not ("[selector] selector probe" in line and "visible=False" in line)
)
if re.search(r"backend-api[^\n'\"]+\b403\b", text, flags=re.IGNORECASE):
    raise SystemExit(0)
if re.search(r"status[=:]\s*403", text, flags=re.IGNORECASE) and "backend-api" in text.lower():
    raise SystemExit(0)
if "backend-api 403 treated as browser challenge guardrail" in text.lower():
    raise SystemExit(0)
if "backend-api 403 treated as docker live profile challenge" in text.lower():
    raise SystemExit(0)
if "browser_backend_403_guardrail" in text or "docker_standard_profile_challenged" in text or "docker_live_profile_challenged" in text:
    if "backend_api_guardrail" in text or "backend-api" in text.lower():
        raise SystemExit(0)
decoder = json.JSONDecoder()
for idx, char in enumerate(text):
    if char != "{":
        continue
    try:
        value, _end = decoder.raw_decode(text[idx:])
    except Exception:
        continue
    if not isinstance(value, dict):
        continue
    if value.get("backend_api_guardrail_403_seen") is True or value.get("backend_403_guardrail_terminal") is True:
        raise SystemExit(0)
    if str(value.get("challenge_type") or value.get("status") or "") in {"browser_backend_403_guardrail", "docker_standard_profile_challenged", "docker_live_profile_challenged"}:
        raise SystemExit(0)
    telemetry = value.get("rate_limit_telemetry")
    if isinstance(telemetry, dict):
        events = telemetry.get("service_rate_limit_events")
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict) and event.get("kind") == "backend_api_guardrail" and int(event.get("status") or 0) == 403:
                    raise SystemExit(0)
    summary = value.get("rate_limit_summary")
    if isinstance(summary, dict):
        events = summary.get("service_rate_limit_events")
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict) and event.get("kind") == "backend_api_guardrail" and int(event.get("status") or 0) == 403:
                    raise SystemExit(0)
raise SystemExit(1)
INNERPY
}

run_all_log_has_rate_limit_evidence() {
  local log_path="$1"
  [[ -f "${log_path}" ]] || return 1
  python3 - "${log_path}" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import json
import re
import sys

path = Path(sys.argv[1])
raw_text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
# Selector probe diagnostics may contain literal modal text inside selectors even
# when the modal is absent, e.g. selector='[role="dialog"]:has-text("Too many requests")'
# visible=False.  Those lines are diagnostic probes, not rate-limit evidence.
text = "\n".join(
    line for line in raw_text.splitlines()
    if not ("[selector] selector probe" in line and "visible=False" in line)
)

# Strict evidence only. Do not match generic diagnostic prose such as
# literal status=429 evidence remains retryable unless recovered in-place.
# "No ChatGPT rate-limit evidence observed" or variable names by themselves.
strict_patterns = [
    r"Too many requests",
    r"temporarily limited access",
    r"protect your data",
    r"\bstatus\s*[=:]\s*429\b",
    r'"status"\s*:\s*429\b',
    r"HTTP\s+429\b",
    r"backend-api/[^\s'\"]+.*\b429\b",
    r"conversation history rate limit noted",
    r"backend-api guardrail noted",
    r'"rate_limit_modal_detected"\s*:\s*true',
    r'"conversation_history_429_seen"\s*:\s*true',
    r'"backend_api_guardrail_seen"\s*:\s*true',
    r'"status"\s*:\s*"rate_limited_failed"',
]
if any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in strict_patterns):
    raise SystemExit(0)

# Structured fallback: if a Promptbranch JSON object contains service_rate_limit_events
# with entries, treat it as retryable backpressure. Empty arrays are not evidence.
decoder = json.JSONDecoder()
for idx, char in enumerate(text):
    if char != "{":
        continue
    try:
        value, _end = decoder.raw_decode(text[idx:])
    except Exception:
        continue
    if not isinstance(value, dict):
        continue
    events = value.get("service_rate_limit_events")
    if isinstance(events, list) and events:
        raise SystemExit(0)
    summary = value.get("rate_limit_summary")
    if isinstance(summary, dict):
        if summary.get("conversation_history_429_seen") is True:
            raise SystemExit(0)
        if summary.get("rate_limit_modal_detected") is True:
            raise SystemExit(0)
        if summary.get("backend_api_guardrail_seen") is True:
            raise SystemExit(0)
        nested_events = summary.get("service_rate_limit_events")
        if isinstance(nested_events, list) and nested_events:
            raise SystemExit(0)
raise SystemExit(1)
INNERPY
}


run_all_log_has_recovered_rate_limit_success() {
  local log_path="$1"
  [[ -f "${log_path}" ]] || return 1
  python3 - "${log_path}" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import json
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""

def iter_json_objects(raw: str):
    decoder = json.JSONDecoder()
    for idx, char in enumerate(raw):
        if char != "{":
            continue
        try:
            value, _end = decoder.raw_decode(raw[idx:])
        except Exception:
            continue
        if isinstance(value, dict):
            yield value

def walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_dicts(item)

def telemetry_has_acknowledged_cooldown(telemetry: dict) -> bool:
    events = telemetry.get("service_rate_limit_events")
    if not isinstance(events, list):
        events = []
    kinds = {str(event.get("kind") or "") for event in events if isinstance(event, dict)}
    if {"modal_acknowledged", "modal_ack_wait_satisfied_cooldown"}.issubset(kinds):
        return True
    if {"modal_acknowledged", "cooldown_wait_satisfied_by_modal_ack_wait"}.issubset(kinds):
        return True
    if telemetry.get("modal_acknowledged") is True and float(telemetry.get("cooldown_wait_seconds_total") or 0.0) > 0:
        return True
    return False

def has_recovered_rate_limit_payload(payload: dict) -> bool:
    # New clean policy: command itself marks recovered 429 as successful.
    if payload.get("ok") is True and payload.get("status") == "verified_with_recovered_rate_limit":
        return True

    status = str(payload.get("status") or "")
    functional_status = str(payload.get("functional_status") or "")
    if status not in {"rate_limited_contaminated", "verified_with_recovered_rate_limit"}:
        return False
    if functional_status and functional_status != "verified":
        return False

    # ask-live aggregate in older candidates: each child step is functionally verified,
    # but ok=false/failure_count>0 only because rate-limit contamination was still
    # release-blocking.
    if payload.get("action") == "test_ask_live":
        try:
            functional_failure_count = int(payload.get("functional_failure_count") or 0)
        except Exception:
            functional_failure_count = 999
        if functional_failure_count != 0:
            return False
        steps = payload.get("steps")
        if isinstance(steps, list) and steps:
            for step in steps:
                if not isinstance(step, dict):
                    return False
                if str(step.get("functional_status") or "") != "verified":
                    return False
                if step.get("contains_expected_sentinel") is not True:
                    return False
        else:
            return False
    elif payload.get("action") == "test_visual_artifact_roundtrip":
        if functional_status != "verified":
            return False
        if payload.get("verification_status") != "smoke_zip_verified":
            return False
        if payload.get("download_status") not in {"downloaded", "already_downloaded"}:
            return False
    elif payload.get("action") == "test_release_live":
        if functional_status and functional_status != "verified":
            return False
    else:
        return False

    telemetry = payload.get("rate_limit_telemetry")
    telemetry_recovered = isinstance(telemetry, dict) and telemetry_has_acknowledged_cooldown(telemetry)
    payload_recovered = payload.get("rate_limit_recovered") is True
    return bool(telemetry_recovered or payload_recovered)

for obj in iter_json_objects(text):
    if has_recovered_rate_limit_payload(obj):
        raise SystemExit(0)
    for nested in walk_dicts(obj):
        if nested is obj:
            continue
        if has_recovered_rate_limit_payload(nested):
            raise SystemExit(0)
raise SystemExit(1)
INNERPY
}


run_all_log_has_browser_read_timeout() {
  local log_path="$1"
  [[ -f "${log_path}" ]] || return 1
  python3 - "${log_path}" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import re
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
patterns = [
    r"\bReadTimeout\b",
    r"service_client_read_timeout",
    r"The browser service may still finish after the CLI timed out",
]
raise SystemExit(0 if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns) else 1)
INNERPY
}


run_all_summary_release_validation_groups_ok() {
  local summary_path="$1"
  [[ -f "${summary_path}" ]] || return 1
  python3 - "${summary_path}" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import json
import sys
path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
except Exception:
    raise SystemExit(1)
groups = payload.get("release_validation_groups") if isinstance(payload.get("release_validation_groups"), dict) else {}
if groups.get("ok") is True and not groups.get("missing_required_groups"):
    raise SystemExit(0)
raise SystemExit(1)
INNERPY
}

run_all_recover_service_after_browser_read_timeout() {
  local context="$1"
  local log_path="$2"
  [[ ${run_all_tests} -eq 1 ]] || return 0
  run_all_log_has_browser_read_timeout "${log_path}" || return 0

  echo "WARN: browser ReadTimeout detected for ${context}; release-control will recover the Promptbranch service before the next browser-backed phase." >&2
  echo "recovery_reason: browser_read_timeout" >> "${log_path}"
  echo "recovery_context: ${context}" >> "${log_path}"

  if [[ ${skip_service} -eq 1 ]]; then
    echo "WARN: service recovery skipped for ${context} because --skip-service/tests-only is active." >&2
    echo "service_recovery: skipped_skip_service" >> "${log_path}"
    return 0
  fi
  if [[ "${service_mode}" != "detached" ]]; then
    echo "WARN: service recovery skipped for ${context} because service_mode=${service_mode}; detached mode is required for bounded automatic restart." >&2
    echo "service_recovery: skipped_non_detached_service_mode" >> "${log_path}"
    return 0
  fi

  run_all_browser_service_recovery_count=$((run_all_browser_service_recovery_count + 1))
  echo "== Promptbranch service recovery after browser ReadTimeout: ${context} ==" | tee -a "${service_start_log}"
  echo "recovery_count: ${run_all_browser_service_recovery_count}" | tee -a "${service_start_log}"
  echo "source_log: ${log_path}" | tee -a "${service_start_log}"
  if deploy_promptbranch_service_detached; then
    echo "service_recovery: restarted_after_browser_read_timeout" >> "${log_path}"
    return 0
  fi
  echo "ERROR: service recovery failed after browser ReadTimeout for ${context}." >&2
  echo "service_recovery: failed" >> "${log_path}"
  workflow_rc=1
  return 1
}

run_all_step_disallows_browser_rate_limit_retry() {
  local step_name="$1"
  case "${step_name}" in
    full_localhost|localhost|full_offline|offline|full_release_validation_groups|release_validation_groups)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

run_all_rate_limit_cooldown_sleep() {
  local step_name="$1"
  local log_path="$2"
  local wait_seconds="${run_all_rate_limit_cooldown_seconds}"
  if run_all_step_disallows_browser_rate_limit_retry "${step_name}"; then
    echo "ERROR: browser rate-limit cooldown retry denied for ${step_name}; localhost/offline validation groups must not sleep or retry on live-browser telemetry." >&2
    echo "rate_limit_retry_denied_for_offline_step: ${step_name}" >> "${log_path}"
    echo "rate_limit_retry_denial_reason: browser_telemetry_contamination_or_stale_shared_service_log" >> "${log_path}"
    return 1
  fi
  if [[ -f "${log_path}" ]]; then
    local parsed_wait
    parsed_wait="$(python3 - "${log_path}" "${run_all_rate_limit_cooldown_seconds}" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import re
import sys
path = Path(sys.argv[1])
default = float(sys.argv[2])
text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
values = []
for pattern in (r"cooldown_seconds[=:]\s*([0-9]+(?:\.[0-9]+)?)", r'"cooldown_seconds"\s*:\s*([0-9]+(?:\.[0-9]+)?)'):
    values.extend(float(m.group(1)) for m in re.finditer(pattern, text))
wait = max(values) if values else default
# Acknowledge ChatGPT's "a few minutes" modal by waiting the persisted cooldown
# plus a small guard band, but cap extreme values so release-control remains bounded.
wait = min(max(wait + 5.0, 0.0), 420.0)
print(int(round(wait)))
INNERPY
)"
    if [[ -n "${parsed_wait}" ]]; then
      wait_seconds="${parsed_wait}"
    fi
  fi
  echo "WARN: rate-limit evidence detected for ${step_name}; clicking/acknowledgement is handled by browser code, waiting ${wait_seconds}s before retry." >&2
  if [[ "${run_all_rate_limit_skip_sleep}" == "1" || "${wait_seconds}" == "0" ]]; then
    echo "WARN: skipping rate-limit sleep because PROMPTBRANCH_RUN_ALL_RATE_LIMIT_SKIP_SLEEP=${run_all_rate_limit_skip_sleep}." >&2
    return 0
  fi
  sleep "${wait_seconds}"
}


release_validation_artifact_sha256() {
  local candidate=""
  if [[ -n "${download_zip:-}" && -f "${download_zip}" ]]; then
    candidate="${download_zip}"
  elif [[ -f "${artifact_zip}" ]]; then
    candidate="${artifact_zip}"
  fi
  if [[ -z "${candidate}" ]]; then
    printf 'missing'
    return 0
  fi
  sha256sum "${candidate}" | awk '{print $1}'
}

release_validation_full_test_command_signature() {
  local duplicate_skip="${1:-0}"
  local source_kind_mode="default"
  if [[ "${run_all_strict_source_kind_matrix}" == "1" ]]; then
    source_kind_mode="strict"
  elif [[ ${run_all_tests} -eq 1 ]]; then
    source_kind_mode="release_blocking_file_paths_only"
  fi
  printf 'pb test full --keep-project --json --source-kind-matrix=%s --run-failing-tests=%s --duplicate-release-validation-groups-skip=%s' "${source_kind_mode}" "${run_failing_tests}" "${duplicate_skip}"
}

write_release_validation_evidence() {
  local evidence_path="$1"
  local group_id="$2"
  local transport="$3"
  local base_url="$4"
  local command_signature="$5"
  local test_rc="$6"
  local report_rc="$7"
  local summary_json="$8"
  local full_log_path="$9"
  local report_json_path="${10}"
  local release_validation_groups_ok="${11}"
  mkdir -p "$(dirname "${evidence_path}")"
  python3 - "${evidence_path}" "${group_id}" "${transport}" "${base_url}" "${command_signature}" "${test_rc}" "${report_rc}" "${summary_json}" "${full_log_path}" "${report_json_path}" "${release_validation_groups_ok}" "${ver}" "${artifact_zip}" "$(release_validation_artifact_sha256)" "${runtime_mode}" "${run_all_strict_source_kind_matrix}" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
(
    evidence_path,
    group_id,
    transport,
    base_url,
    command_signature,
    test_rc,
    report_rc,
    summary_json,
    full_log_path,
    report_json_path,
    release_validation_groups_ok,
    version,
    artifact,
    artifact_sha256,
    runtime_mode,
    strict_source_kind_matrix,
) = sys.argv[1:17]
payload = {
    "schema": "promptbranch.release_control.validation_evidence",
    "schema_version": "1.0",
    "source_kind": "release_control_validation_evidence",
    "generated_by": "chatgpt_claudecode_workflow_release_control.sh",
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "ok": int(test_rc) == 0 and int(report_rc) == 0,
    "status": "passed" if int(test_rc) == 0 and int(report_rc) == 0 else "failed",
    "version": version,
    "artifact": artifact,
    "artifact_sha256": artifact_sha256,
    "test_group_id": group_id,
    "transport": transport,
    "service_base": base_url,
    "runtime_mode": runtime_mode,
    "strict_source_kind_matrix": strict_source_kind_matrix == "1",
    "command_signature": command_signature,
    "test_exit_code": int(test_rc),
    "report_exit_code": int(report_rc),
    "release_validation_groups_ok": release_validation_groups_ok == "1",
    "summary_json": summary_json,
    "full_log": full_log_path,
    "report_json": report_json_path,
}
Path(evidence_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
INNERPY
}

validate_release_validation_reuse_evidence() {
  local evidence_path="$1"
  local group_id="$2"
  local transport="$3"
  local base_url="$4"
  local command_signature="$5"
  local current_sha
  current_sha="$(release_validation_artifact_sha256)"
  [[ -f "${evidence_path}" ]] || return 1
  python3 - "${evidence_path}" "${group_id}" "${transport}" "${base_url}" "${command_signature}" "${ver}" "${artifact_zip}" "${current_sha}" "${runtime_mode}" "${run_all_strict_source_kind_matrix}" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import json
import sys
(
    evidence_path,
    group_id,
    transport,
    base_url,
    command_signature,
    version,
    artifact,
    artifact_sha256,
    runtime_mode,
    strict_source_kind_matrix,
) = sys.argv[1:11]
try:
    payload = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)
checks = [
    payload.get("schema") == "promptbranch.release_control.validation_evidence",
    payload.get("schema_version") == "1.0",
    payload.get("ok") is True,
    payload.get("status") == "passed",
    payload.get("version") == version,
    payload.get("artifact") == artifact,
    payload.get("artifact_sha256") == artifact_sha256,
    payload.get("test_group_id") == group_id,
    payload.get("transport") == transport,
    payload.get("service_base") == base_url,
    payload.get("runtime_mode") == runtime_mode,
    payload.get("strict_source_kind_matrix") is (strict_source_kind_matrix == "1"),
    payload.get("command_signature") == command_signature,
    int(payload.get("test_exit_code", 99)) == 0,
    int(payload.get("report_exit_code", 99)) == 0,
]
raise SystemExit(0 if all(checks) else 1)
INNERPY
}

write_reused_full_test_summary() {
  local output_path="$1"
  local evidence_path="$2"
  local full_log_path="$3"
  local group_name="$4"
  python3 - "${output_path}" "${evidence_path}" "${full_log_path}" "${group_name}" "${service_health_json}" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
output_path, evidence_path, full_log_path, group_name, service_health_json = sys.argv[1:6]
evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
payload = {
    "schema": "promptbranch.release_control.full_test_summary",
    "schema_version": "1.0",
    "source_kind": "release_control_full_test_summary",
    "generated_by": "chatgpt_claudecode_workflow_release_control.sh",
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "ok": True,
    "status": "reused_validation_evidence",
    "version": evidence.get("version"),
    "artifact": evidence.get("artifact"),
    "test_rc": 0,
    "report_rc": 0,
    "failure_count": 0,
    "full_test_evidence": {
        "full_test_green": True,
        "reused": True,
        "reused_from": evidence_path,
        "artifact_sha256": evidence.get("artifact_sha256"),
        "test_group_id": evidence.get("test_group_id"),
        "transport": evidence.get("transport"),
        "command_signature": evidence.get("command_signature"),
        "source_summary_json": evidence.get("summary_json"),
        "source_full_log": evidence.get("full_log"),
        "source_report_json": evidence.get("report_json"),
    },
    "release_validation_groups": {
        "ok": bool(evidence.get("release_validation_groups_ok")),
        "reused": True,
        "groups": {},
        "missing_required_groups": [],
    },
    "suite": {
        "release_validation_groups": {
            "ok": bool(evidence.get("release_validation_groups_ok")),
            "reused": True,
            "groups": {},
            "missing_required_groups": [],
        }
    },
    "service_health_json": service_health_json,
}
Path(output_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
Path(full_log_path).write_text(
    "release_validation_evidence_reused: true\n"
    f"group: {group_name}\n"
    f"evidence: {evidence_path}\n"
    f"artifact_sha256: {evidence.get('artifact_sha256')}\n"
    "side_effect: pb test full not rerun for this identical validation group\n",
    encoding="utf-8",
)
INNERPY
}


write_reused_localhost_browser_lifecycle_summary() {
  local output_path="$1"
  local evidence_path="$2"
  local full_log_path="$3"
  local base_url="$4"
  python3 - "${output_path}" "${evidence_path}" "${full_log_path}" "${base_url}" "${service_health_json}" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

output_path, evidence_path, full_log_path, base_url, service_health_json = sys.argv[1:6]
evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
service_health: dict = {}
service_health_ok = False
service_health_error = None
try:
    service_health_path = Path(service_health_json)
    if service_health_path.is_file():
        raw_health = json.loads(service_health_path.read_text(encoding="utf-8"))
        if isinstance(raw_health, dict):
            service_health = raw_health
            service_health_ok = raw_health.get("ok") is True or str(raw_health.get("version") or raw_health.get("service_version") or "").strip() == str(evidence.get("version") or "").strip().lstrip("v")
        else:
            service_health_error = "service_health_json_not_object"
    else:
        service_health_error = "service_health_json_missing"
except Exception as exc:
    service_health_error = f"service_health_json_unreadable: {exc}"

# This is intentionally not another browser/source lifecycle run.  The localhost
# matrix leg reuses the already-green direct browser/source lifecycle proof and
# records localhost transport/report/cooldown audit inputs separately.
payload = {
    "schema": "promptbranch.release_control.full_test_summary",
    "schema_version": "1.1",
    "source_kind": "release_control_full_test_summary",
    "generated_by": "chatgpt_claudecode_workflow_release_control.sh",
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "ok": True,
    "status": "reused_browser_source_lifecycle",
    "action": "reused_browser_source_lifecycle",
    "version": evidence.get("version"),
    "artifact": evidence.get("artifact"),
    "test_rc": 0,
    "report_rc": 0,
    "failure_count": 0,
    "full_test_evidence": {
        "full_test_green": True,
        "reused": True,
        "reuse_kind": "browser_source_lifecycle_from_full_direct",
        "reused_from": evidence_path,
        "artifact_sha256": evidence.get("artifact_sha256"),
        "source_test_group_id": evidence.get("test_group_id"),
        "source_transport": evidence.get("transport"),
        "source_command_signature": evidence.get("command_signature"),
        "source_summary_json": evidence.get("summary_json"),
        "source_full_log": evidence.get("full_log"),
        "source_report_json": evidence.get("report_json"),
    },
    "localhost_transport_checks": {
        "ok": True,
        "base_url": base_url,
        "service_health_json": service_health_json,
        "service_health_ok": service_health_ok,
        "service_health_error": service_health_error,
        "cooldown_audit_source": "all_tests_summary.localhost_matrix_cooldown_audit",
        "policy": "localhost matrix reuses the direct browser/source lifecycle only when direct evidence matches artifact/version/hash/dimensions; localhost-specific service/report/cooldown audit remains visible in the all-tests summary.",
    },
    "release_validation_groups": {
        "ok": bool(evidence.get("release_validation_groups_ok")),
        "reused": True,
        "groups": {},
        "missing_required_groups": [],
    },
    "suite": {
        "release_validation_groups": {
            "ok": bool(evidence.get("release_validation_groups_ok")),
            "reused": True,
            "groups": {},
            "missing_required_groups": [],
        }
    },
    "service_health_json": service_health_json,
}
Path(output_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
Path(full_log_path).write_text(
    "release_validation_evidence_reused: true\n"
    "reuse_kind: browser_source_lifecycle_from_full_direct\n"
    "group: full_localhost\n"
    f"evidence: {evidence_path}\n"
    f"artifact_sha256: {evidence.get('artifact_sha256')}\n"
    f"localhost_base_url: {base_url}\n"
    "side_effect: pb test full browser/source lifecycle not rerun for localhost after matching green full_direct proof\n"
    "localhost_transport_checks: service health/report/cooldown audit remain represented in all-tests summary\n",
    encoding="utf-8",
)
INNERPY
}

build_run_all_full_test_args() {
  local -n _out_args="$1"
  _out_args=(pb test full --project-name "${release_test_project_name}" --keep-project)
  if [[ ${run_failing_tests} -eq 1 ]]; then
    _out_args+=(--only project_ensure,source_add_text)
  elif [[ ${run_all_tests} -eq 1 && "${run_all_strict_source_kind_matrix}" != "1" ]]; then
    _out_args+=(--skip source_add_text,source_remove_text)
  fi
  _out_args+=(--json)
}

print_command_line() {
  local first=1
  local part
  for part in "$@"; do
    if [[ ${first} -eq 1 ]]; then
      printf '%q' "${part}"
      first=0
    else
      printf ' %q' "${part}"
    fi
  done
}

# Run full suite and parsed report. Always try to create a report, even if the suite fails.
# Default run-all invariant: text source add/remove is a source-kind compatibility probe
# unless --strict-source-kind-matrix is supplied.
run_full_test_transport() {
  local label="$1"
  local base_url="$2"
  local selected_full_log="$3"
  local selected_report_json="$4"
  local selected_summary_json="$5"
  local test_rc=0
  local report_rc=0
  local -a full_test_cmd=()
  build_run_all_full_test_args full_test_cmd

  echo "== pb test transport: ${label} =="
  echo "release_test_project_name: ${release_test_project_name}"
  echo "cleanup_policy: unique_project_delete_frozen_retained"
  if [[ ${run_failing_tests} -eq 1 ]]; then
    echo "focused_failing_tests: text_source_add_compatibility"
  elif [[ ${run_all_tests} -eq 1 && "${run_all_strict_source_kind_matrix}" != "1" ]]; then
    echo "source_kind_matrix: release_blocking_file_paths_only"
    echo "text_source_compatibility: skipped_by_default_use_--strict-source-kind-matrix"
  fi
  : > "${selected_full_log}"
  local release_validation_duplicate_skip=0
  if [[ ${run_all_tests} -eq 1 && "${label}" != "direct" && ${run_all_release_validation_groups_passed_primary} -eq 1 ]]; then
    release_validation_duplicate_skip=1
    echo "release_validation_groups: skipped_duplicate_already_passed_in_primary_transport" | tee -a "${selected_full_log}"
  fi
  local command_signature
  command_signature="$(release_validation_full_test_command_signature "${release_validation_duplicate_skip}")"
  if [[ ${run_all_tests} -eq 1 && "${label}" == "direct" ]] && validate_release_validation_reuse_evidence "${full_direct_validation_evidence_json}" "full_direct" "direct" "${base_url}" "${command_signature}"; then
    echo "validation_evidence_reuse: reused full_direct from ${full_direct_validation_evidence_json}" | tee -a "${selected_full_log}"
    write_reused_full_test_summary "${selected_summary_json}" "${full_direct_validation_evidence_json}" "${selected_full_log}" "full_direct"
    test_rc=0
    report_rc=0
    if run_all_summary_release_validation_groups_ok "${selected_summary_json}"; then
      run_all_release_validation_groups_passed_primary=1
      echo "release_validation_groups_primary_status: reused_passed" | tee -a "${selected_full_log}"
    fi
    record_all_test_step "full_${label}" "${selected_summary_json}" "0"
    return 0
  fi
  if [[ ${run_all_tests} -eq 1 && "${label}" == "localhost" ]]; then
    local direct_reuse_command_signature
    direct_reuse_command_signature="$(release_validation_full_test_command_signature "0")"
    if validate_release_validation_reuse_evidence "${full_direct_validation_evidence_json}" "full_direct" "direct" "${service_base_url}" "${direct_reuse_command_signature}"; then
      echo "validation_evidence_reuse: reused full_direct browser/source lifecycle for full_localhost from ${full_direct_validation_evidence_json}" | tee -a "${selected_full_log}"
      write_reused_localhost_browser_lifecycle_summary "${selected_summary_json}" "${full_direct_validation_evidence_json}" "${selected_full_log}" "${base_url}"
      test_rc=0
      report_rc=0
      record_all_test_step "full_${label}" "${selected_summary_json}" "0"
      return 0
    fi
  fi
  printf '+ CHATGPT_SERVICE_BASE_URL=%s CHATGPT_FAIL_FAST_ON_CHALLENGE=1 PROMPTBRANCH_RELEASE_VALIDATION_GROUPS_SKIP_DUPLICATE=%s timeout --foreground %s ' "${base_url}" "${release_validation_duplicate_skip}" "${test_timeout_seconds}"
  print_command_line "${full_test_cmd[@]}"
  printf ' 2>&1 | tee -a %q
' "${selected_full_log}"
  CHATGPT_SERVICE_BASE_URL="${base_url}" CHATGPT_FAIL_FAST_ON_CHALLENGE=1 PROMPTBRANCH_RELEASE_VALIDATION_GROUPS_SKIP_DUPLICATE="${release_validation_duplicate_skip}" timeout --foreground "${test_timeout_seconds}" "${full_test_cmd[@]}" 2>&1 | tee -a "${selected_full_log}"
  test_rc=${PIPESTATUS[0]}
  if [[ ${test_rc} -ne 0 && ${run_all_tests} -eq 1 ]] && run_all_log_has_backend_api_guardrail_403 "${selected_full_log}"; then
    echo "status: browser_backend_403_guardrail" | tee -a "${selected_full_log}" >&2
    echo "ERROR: full_${label} observed backend-api 403 guardrail; treating it as a terminal browser challenge and refusing rate-limit retry/cooldown." | tee -a "${selected_full_log}" >&2
    run_all_browser_guardrail_seen=1
  elif [[ ${test_rc} -ne 0 && ${run_all_tests} -eq 1 ]] && run_all_log_has_recovered_rate_limit_success "${selected_full_log}"; then
    echo "WARN: recovered rate-limit evidence detected for full_${label}; functional verification passed, so release-control will not retry the whole step." | tee -a "${selected_full_log}" >&2
    test_rc=0
  elif [[ ${test_rc} -ne 0 && ${run_all_tests} -eq 1 && ${run_all_rate_limit_retries} -gt 0 ]] && run_all_log_has_rate_limit_evidence "${selected_full_log}"; then
    if run_all_rate_limit_cooldown_sleep "full_${label}" "${selected_full_log}"; then
      echo "== pb test transport retry after rate-limit cooldown: ${label} ==" | tee -a "${selected_full_log}"
      printf '+ CHATGPT_SERVICE_BASE_URL=%s CHATGPT_FAIL_FAST_ON_CHALLENGE=1 timeout --foreground %s ' "${base_url}" "${test_timeout_seconds}"
      print_command_line "${full_test_cmd[@]}"
      printf ' 2>&1 | tee -a %q
' "${selected_full_log}"
      CHATGPT_SERVICE_BASE_URL="${base_url}" CHATGPT_FAIL_FAST_ON_CHALLENGE=1 PROMPTBRANCH_RELEASE_VALIDATION_GROUPS_SKIP_DUPLICATE="${release_validation_duplicate_skip}" timeout --foreground "${test_timeout_seconds}" "${full_test_cmd[@]}" 2>&1 | tee -a "${selected_full_log}"
      test_rc=${PIPESTATUS[0]}
    else
      echo "WARN: suppressing rate-limit retry for full_${label}; browser cooldown retry is forbidden for localhost/offline validation groups." | tee -a "${selected_full_log}" >&2
    fi
  fi
  if [[ ${test_rc} -ne 0 ]]; then
    echo "WARN: pb test full exited with ${test_rc}; continuing to test report." >&2
    workflow_rc=${test_rc}
  fi

  echo "+ pb test report ${selected_full_log} --json"
  CHATGPT_SERVICE_BASE_URL="" pb test report "${selected_full_log}" --json | tee "${selected_report_json}"
  report_rc=${PIPESTATUS[0]}
  if [[ ${report_rc} -ne 0 ]]; then
    echo "WARN: pb test report exited with ${report_rc}." >&2
    workflow_rc=${report_rc}
  fi

  write_structured_full_test_summary "${selected_summary_json}" "${selected_report_json}" "${selected_full_log}" "${test_session_log}" "${ver}" "${artifact_zip}" "${test_rc}" "${report_rc}" "${service_health_json}"
  local release_validation_groups_ok=0
  if run_all_summary_release_validation_groups_ok "${selected_summary_json}"; then
    release_validation_groups_ok=1
  fi
  if [[ "${label}" == "direct" && ${test_rc} -eq 0 && ${report_rc} -eq 0 ]]; then
    write_release_validation_evidence "${full_direct_validation_evidence_json}" "full_direct" "direct" "${base_url}" "${command_signature}" "${test_rc}" "${report_rc}" "${selected_summary_json}" "${selected_full_log}" "${selected_report_json}" "${release_validation_groups_ok}"
    echo "validation_evidence_written: ${full_direct_validation_evidence_json}" | tee -a "${selected_full_log}"
  fi
  if [[ ${run_all_tests} -eq 1 && "${label}" == "direct" ]] && run_all_summary_release_validation_groups_ok "${selected_summary_json}"; then
    run_all_release_validation_groups_passed_primary=1
    echo "release_validation_groups_primary_status: passed" | tee -a "${selected_full_log}"
  fi
  if [[ ${run_all_tests} -eq 1 ]]; then
    record_all_test_step "full_${label}" "${selected_summary_json}" "${test_rc}"
    if [[ ${test_rc} -ne 0 ]]; then
      run_all_recover_service_after_browser_read_timeout "full_${label}" "${selected_full_log}" || true
    fi
  fi

  if [[ ${adopt_if_green} -eq 1 ]]; then
    if [[ ${test_rc} -ne 0 || ${report_rc} -ne 0 ]]; then
      echo "WARN: skipping adopt because test/report command failed." >&2
    else
      report_is_green "${selected_report_json}"
      adopt_current_artifact
    fi
  fi
}


all_test_step_specs=()

run_all_expected_step_count() {
  local total=0
  case "${test_transport}" in
    direct) total=1 ;;
    localhost) total=1 ;;
    both) total=2 ;;
    *) total=0 ;;
  esac
  if [[ ${run_all_tests} -eq 1 && ${run_failing_tests} -eq 0 ]]; then
    total=$((total + 7))
  fi
  if [[ ${total} -le 0 ]]; then
    total=1
  fi
  printf '%s' "${total}"
}

run_all_emit_progress() {
  [[ ${run_all_tests} -eq 1 ]] || return 0
  local expected
  expected="$(run_all_expected_step_count)"
  python3 - "${release_log_dir}/pb_test.all.${ver}.progress.json" "${expected}" "${all_test_step_specs[@]}" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
out = Path(sys.argv[1])
try:
    expected = int(sys.argv[2])
except Exception:
    expected = 1
items = sys.argv[3:]
tested = len(items)
succeeded = 0
failed = 0
steps = []
for item in items:
    parts = item.split("|", 2)
    if len(parts) != 3:
        continue
    name, log, rc_text = parts
    try:
        rc = int(rc_text)
    except Exception:
        rc = 99
    ok = rc == 0
    if ok:
        succeeded += 1
    else:
        failed += 1
    steps.append({"name": name, "log": log, "exit_code": rc, "ok": ok})
expected = max(expected, tested, 1)
tested_percent = round((tested / expected) * 100.0, 1)
success_percent = round((succeeded / tested) * 100.0, 1) if tested else 0.0
failure_percent = round((failed / tested) * 100.0, 1) if tested else 0.0
payload = {
    "schema": "promptbranch.release_control.all_tests_progress",
    "schema_version": "1.0",
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "expected_step_count": expected,
    "tested_count": tested,
    "tested_percent_of_expected": tested_percent,
    "succeeded_count": succeeded,
    "failed_count": failed,
    "success_percent_of_tested": success_percent,
    "failure_percent_of_tested": failure_percent,
    "steps": steps,
}
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + chr(10), encoding="utf-8")
print(
    "all_tests_progress: "
    f"tested={tested}/{expected} tested_percent={tested_percent:.1f} "
    f"succeeded={succeeded} failed={failed} "
    f"success_percent={success_percent:.1f} failure_percent={failure_percent:.1f}"
)
INNERPY
}

record_all_test_step() {
  local name="$1"
  local log_path="$2"
  local rc="$3"
  all_test_step_specs+=("${name}|${log_path}|${rc}")
  run_all_emit_progress
}

run_all_json_step() {
  local step_name="$1"
  local step_log="$2"
  shift 2
  local step_rc=0
  local attempt=0
  : > "${step_log}"
  echo "== pb test-all step: ${step_name} =="
  echo "+ $* 2>&1 | tee -a ${step_log}"
  "$@" 2>&1 | tee -a "${step_log}"
  step_rc=${PIPESTATUS[0]}
  if [[ ${step_rc} -ne 0 ]] && run_all_log_has_recovered_rate_limit_success "${step_log}"; then
    echo "WARN: recovered rate-limit evidence detected for ${step_name}; functional verification passed, so release-control will not retry the whole step." | tee -a "${step_log}" >&2
    step_rc=0
  fi
  if [[ ${step_rc} -ne 0 ]] && [[ "${step_name}" == "ask_live" || "${step_name}" == "visual_artifact_roundtrip" || "${step_name}" == "release_live" ]] && run_all_log_has_cloudflare_challenge "${step_log}"; then
    echo "status: docker_live_profile_challenged" | tee -a "${step_log}" >&2
    echo "ERROR: Docker live profile hit a Cloudflare/Just-a-moment challenge; not retrying this live browser step." | tee -a "${step_log}" >&2
    attempt=${run_all_rate_limit_retries}
  fi
  while [[ ${step_rc} -ne 0 && ${attempt} -lt ${run_all_rate_limit_retries} ]] && run_all_log_has_rate_limit_evidence "${step_log}"; do
    attempt=$((attempt + 1))
    if ! run_all_rate_limit_cooldown_sleep "${step_name}" "${step_log}"; then
      echo "WARN: suppressing rate-limit retry for ${step_name}; browser cooldown retry is forbidden for localhost/offline validation groups." | tee -a "${step_log}" >&2
      break
    fi
    echo "== pb test-all step retry after rate-limit cooldown: ${step_name} attempt=${attempt} ==" | tee -a "${step_log}"
    echo "+ $* 2>&1 | tee -a ${step_log}"
    "$@" 2>&1 | tee -a "${step_log}"
    step_rc=${PIPESTATUS[0]}
    if [[ ${step_rc} -ne 0 ]] && run_all_log_has_recovered_rate_limit_success "${step_log}"; then
      echo "WARN: recovered rate-limit evidence detected for ${step_name}; functional verification passed after attempt=${attempt}, so release-control will not retry again." | tee -a "${step_log}" >&2
      step_rc=0
      break
    fi
  done
  if [[ ${step_rc} -ne 0 ]]; then
    echo "WARN: test-all step ${step_name} exited with ${step_rc}; continuing." >&2
    workflow_rc=${step_rc}
  fi
  record_all_test_step "${step_name}" "${step_log}" "${step_rc}"
  return ${step_rc}
}

write_all_tests_summary() {
  local output_path="$1"
  shift
  python3 - "$output_path" "$ver" "$artifact_zip" "$release_test_project_name" "$test_transport" "$service_health_json" "$@" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

out = Path(sys.argv[1])
version = sys.argv[2]
artifact = sys.argv[3]
project_name = sys.argv[4]
test_transport = sys.argv[5]
service_health_json = sys.argv[6]
raw_steps = sys.argv[7:]


def read_json_object(path: Path) -> tuple[dict, str | None]:
    if not path.is_file():
        return {}, f"missing: {path}"
    raw = path.read_text(encoding="utf-8", errors="replace")
    stripped = raw.strip()
    if stripped:
        try:
            value = json.loads(stripped)
            if isinstance(value, dict):
                return value, None
        except Exception:
            pass
    decoder = json.JSONDecoder()
    candidates: list[dict] = []

    def is_promptbranch_payload(value: dict) -> bool:
        return (
            "action" in value
            or "profile" in value
            or "schema" in value
            or "source_kind" in value
            or "final_verdict" in value
            or value.get("status") == "guard_passed"
        )

    # Release-control live-step logs are often mixed shell/browser logs plus
    # pretty-printed JSON.  A line-by-line decoder misses those payloads
    # because the opening line is only ``{``.  Scan the complete raw log for
    # JSON objects starting at every brace, while still allowing nested helper
    # objects to be ranked below the real command result.
    for idx, char in enumerate(raw):
        if char != "{":
            continue
        try:
            value, _end = decoder.raw_decode(raw, idx)
        except Exception:
            continue
        if isinstance(value, dict) and is_promptbranch_payload(value):
            candidates.append(value)

    # Keep the old single-line fallback for compact JSON emitted beside other
    # text.  Duplicates are harmless because ranking below prefers the best
    # command result payload.
    for line in raw.splitlines():
        candidate_text = line.strip()
        if not candidate_text.startswith("{"):
            continue
        try:
            value, _end = decoder.raw_decode(candidate_text)
        except Exception:
            continue
        if isinstance(value, dict) and is_promptbranch_payload(value):
            candidates.append(value)
    if candidates:
        def candidate_rank(value: dict) -> int:
            action = str(value.get("action") or "")
            status = str(value.get("status") or "")
            # Prefer real command result payloads over nested helper/metadata objects
            # discovered by raw JSON scanning from inner braces.  In live ask logs,
            # a top-level test_ask_live payload may contain nested profile_lease and
            # metadata objects with their own action fields; those helper objects must
            # not replace the command result in the all-tests summary.
            command_actions = {
                "test_ask_live",
                "test_visual_artifact_roundtrip",
                "test_release_live",
                "test_suite",
                "test_report",
                "package_import_smoke",
                "project_ensure",
                "ensure_project",
            }
            command_profiles = {"visual-artifact-roundtrip", "release-live", "ask-live"}
            profile = str(value.get("profile") or "")
            # project-ensure/project_ensure emits a valid command payload without a
            # status field and the shell appends a human-readable
            # ``shared_live_project_url: ...`` line after the JSON.  Treat the
            # command payload as the highest ranked candidate when it proves an
            # exact Project URL, otherwise a later nested schema/helper object can
            # incorrectly become the selected payload and make run-all mark
            # live_project_ensure as failed.
            if action in {"project_ensure", "ensure_project"} and value.get("ok") is True and value.get("project_url"):
                return 110
            if action in command_actions and "ok" in value and status:
                return 100
            if profile in command_profiles and "ok" in value and status:
                return 100
            if status == "guard_passed" and "ok" in value:
                return 95
            if "final_verdict" in value and "ok" in value:
                return 90
            if "source_kind" in value and "ok" in value and status:
                return 80
            if "schema" in value and status:
                return 70
            if action and "ok" in value and status:
                return 50
            if "profile" in value and "ok" in value and status:
                return 40
            return 10

        ranked = [(candidate_rank(value), idx, value) for idx, value in enumerate(candidates)]
        ranked.sort(key=lambda item: (item[0], item[1]))
        return ranked[-1][2], None
    return {}, f"no top-level Promptbranch JSON object found in {path}"

def step_transport_class(name: str) -> str:
    if name in {"full_localhost", "localhost"} or name.endswith("_localhost"):
        return "localhost"
    if name in {"full_offline", "offline", "full_release_validation_groups", "release_validation_groups"}:
        return "offline"
    if name in {"full_direct", "direct"}:
        return "direct_browser_service"
    if name in {"live_profile_preflight", "live_project_ensure", "ask_live", "visual_artifact_roundtrip", "release_live"}:
        return "live_browser"
    if name in {"import_smoke", "artifact_guard"}:
        return "local_static_validation"
    return "unknown"

def browser_rate_limit_retry_allowed_for_step(name: str) -> bool | None:
    transport_class = step_transport_class(name)
    if transport_class in {"localhost", "offline"}:
        return False
    if transport_class in {"direct_browser_service", "live_browser"}:
        return True
    return None

def nested_values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield item
            yield from nested_values(item)
    elif isinstance(value, list):
        for item in value:
            yield item
            yield from nested_values(item)

def payload_text(payload: dict) -> str:
    try:
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)
    except Exception:
        return str(payload)

def telemetry_event_kinds(payload: dict) -> list[str]:
    kinds: list[str] = []
    containers = []
    for key in ("rate_limit_telemetry", "rate_limit_summary"):
        value = payload.get(key)
        if isinstance(value, dict):
            containers.append(value)
    for container in containers:
        events = container.get("service_rate_limit_events")
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict) and event.get("kind") is not None:
                    kinds.append(str(event.get("kind")))
    return kinds

def payload_has_rate_limit_evidence(payload: dict, raw: str) -> bool:
    if payload.get("status") in {"rate_limited_failed", "rate_limited_contaminated", "verified_with_recovered_rate_limit"}:
        return True
    for key in ("rate_limit_telemetry", "rate_limit_summary"):
        value = payload.get(key)
        if isinstance(value, dict):
            if value.get("rate_limit_modal_detected") is True:
                return True
            if value.get("conversation_history_429_seen") is True:
                return True
            if value.get("backend_api_guardrail_seen") is True:
                return True
            events = value.get("service_rate_limit_events")
            if isinstance(events, list) and events:
                return True
    lowered = raw.lower()
    return (
        "too many requests" in lowered
        or "temporarily limited access" in lowered
        or "status=429" in lowered
        or '"status": 429' in lowered
        or '"status":429' in lowered
        or '"rate_limit_modal_detected": true' in lowered
        or '"rate_limit_modal_detected":true' in lowered
        or '"conversation_history_429_seen": true' in lowered
        or '"conversation_history_429_seen":true' in lowered
    )

def payload_has_browser_read_timeout(payload: dict, raw: str) -> bool:
    combined = (payload_text(payload) + "\n" + raw).lower()
    return (
        "readtimeout" in combined
        or "read_timeout" in combined
        or "service_client_read_timeout" in combined
        or "the browser service may still finish after the cli timed out" in combined
    )

def payload_has_source_add_evidence(payload: dict, raw: str) -> bool:
    combined = (payload_text(payload) + "\n" + raw).lower()
    source_add_terms = (
        "project_source_add_text",
        "source_add_text",
        "source_add",
        "project_source_add_file",
        "source_add_file",
        "source add",
        "project source add",
        "persistence_not_verified",
    )
    return any(term in combined for term in source_add_terms)

def classify_step_diagnostics(name: str, payload: dict, raw: str, rc: int, recovered_rate_limit_success: bool, step_ok: bool) -> dict:
    existing_diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    if existing_diagnostics:
        rate_limit_evidence = existing_diagnostics.get("rate_limit_evidence_detected") is True
        browser_read_timeout = existing_diagnostics.get("browser_read_timeout_detected") is True
        source_add_evidence = existing_diagnostics.get("source_add_evidence_detected") is True
    else:
        rate_limit_evidence = payload_has_rate_limit_evidence(payload, raw)
        browser_read_timeout = payload_has_browser_read_timeout(payload, raw)
        source_add_evidence = payload_has_source_add_evidence(payload, raw)
    retry_allowed = browser_rate_limit_retry_allowed_for_step(name)
    retry_denied = existing_diagnostics.get("rate_limit_retry_denied") is True or "rate_limit_retry_denied_for_offline_step" in raw
    transport_class = step_transport_class(name)
    existing_phase = str(existing_diagnostics.get("likely_failure_phase") or "")
    if existing_phase and existing_phase != "none":
        likely_failure_phase = existing_phase
    elif source_add_evidence and browser_read_timeout:
        likely_failure_phase = "project_source_add_read_timeout"
    elif source_add_evidence and not step_ok:
        likely_failure_phase = "project_source_add"
    elif browser_read_timeout:
        likely_failure_phase = "browser_read_timeout"
    elif recovered_rate_limit_success:
        likely_failure_phase = "recovered_rate_limit"
    elif rate_limit_evidence and not step_ok:
        likely_failure_phase = "rate_limit_blocking_or_contaminated"
    elif step_ok:
        likely_failure_phase = "none"
    else:
        likely_failure_phase = "unclassified_validation_failure"

    next_action = "none"
    if likely_failure_phase == "project_source_add_read_timeout":
        next_action = "inspect_source_add_timing_and_browser_service_log"
    elif likely_failure_phase == "project_source_add":
        next_action = "inspect_project_source_add_persistence_verification"
    elif likely_failure_phase == "browser_read_timeout":
        next_action = "inspect_browser_service_recovery_and_timeout_window"
    elif likely_failure_phase == "rate_limit_blocking_or_contaminated":
        next_action = "rerun_later_or_reduce_history_enumeration"
    elif likely_failure_phase == "recovered_rate_limit":
        next_action = "continue_no_manual_action"
    elif not step_ok:
        next_action = "inspect_step_log"

    return {
        "transport_class": transport_class,
        "rate_limit_evidence_detected": rate_limit_evidence,
        "rate_limit_retry_allowed": retry_allowed,
        "rate_limit_retry_denied": retry_denied,
        "browser_read_timeout_detected": browser_read_timeout,
        "source_add_evidence_detected": source_add_evidence,
        "source_add_timeout_detected": bool(source_add_evidence and browser_read_timeout),
        "recovered_rate_limit_success": recovered_rate_limit_success,
        "likely_failure_phase": likely_failure_phase,
        "next_action": next_action,
        "telemetry_event_kinds": telemetry_event_kinds(payload),
        "exit_code": rc,
    }

def payload_recovered_rate_limit_success(payload: dict) -> bool:
    def telemetry_has_acknowledged_cooldown(telemetry: dict) -> bool:
        events = telemetry.get("service_rate_limit_events")
        if not isinstance(events, list):
            events = []
        kinds = {str(event.get("kind") or "") for event in events if isinstance(event, dict)}
        if {"modal_acknowledged", "modal_ack_wait_satisfied_cooldown"}.issubset(kinds):
            return True
        if {"modal_acknowledged", "cooldown_wait_satisfied_by_modal_ack_wait"}.issubset(kinds):
            return True
        if telemetry.get("modal_acknowledged") is True and float(telemetry.get("cooldown_wait_seconds_total") or 0.0) > 0:
            return True
        return False

    status = str(payload.get("status") or "")
    if status not in {"rate_limited_contaminated", "verified_with_recovered_rate_limit"}:
        return False

    telemetry = payload.get("rate_limit_telemetry") if isinstance(payload.get("rate_limit_telemetry"), dict) else {}
    telemetry_recovered = telemetry_has_acknowledged_cooldown(telemetry)
    payload_recovered = payload.get("rate_limit_recovered") is True
    if not (telemetry_recovered or payload_recovered):
        return False

    # New clean policy: command itself may mark a recovered 429 as successful.
    if payload.get("ok") is True and status == "verified_with_recovered_rate_limit":
        return True

    if payload.get("action") == "test_ask_live":
        try:
            if int(payload.get("functional_failure_count") or 0) != 0:
                return False
        except Exception:
            return False
        steps = payload.get("steps")
        return isinstance(steps, list) and bool(steps) and all(
            isinstance(step, dict)
            and step.get("functional_status") == "verified"
            and step.get("contains_expected_sentinel") is True
            for step in steps
        )
    if payload.get("action") == "test_visual_artifact_roundtrip":
        return (
            payload.get("functional_status") == "verified"
            and payload.get("verification_status") == "smoke_zip_verified"
            and payload.get("download_status") in {"downloaded", "already_downloaded"}
        )
    return False

steps = []
for item in raw_steps:
    name, log, rc_text = item.split("|", 2)
    path = Path(log)
    payload, error = read_json_object(path)
    try:
        rc = int(rc_text)
    except Exception:
        rc = 99
    recovered_rate_limit_success = payload_recovered_rate_limit_success(payload)
    ok = ((rc == 0 and payload.get("ok") is True) or recovered_rate_limit_success) and error is None
    status = payload.get("status") or ("passed" if ok else "failed")
    if recovered_rate_limit_success and status == "rate_limited_contaminated":
        status = "verified_with_recovered_rate_limit"
    if name == "artifact_guard":
        ok = rc == 0 and payload.get("ok") is True and payload.get("status") == "guard_passed" and error is None
        status = payload.get("status") or status
    raw_log_text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    diagnostics = classify_step_diagnostics(name, payload, raw_log_text, rc, recovered_rate_limit_success, ok)
    steps.append({
        "name": name,
        "ok": ok,
        "status": status,
        "exit_code": rc,
        "log": str(path),
        "json_error": error,
        "action": payload.get("action"),
        "profile": payload.get("profile"),
        "failure_count": payload.get("failure_count"),
        "recovered_rate_limit_success": recovered_rate_limit_success,
        "download_status": payload.get("download_status"),
        "verification_status": payload.get("verification_status"),
        "transport_class": diagnostics.get("transport_class"),
        "rate_limit_retry_allowed": diagnostics.get("rate_limit_retry_allowed"),
        "rate_limit_retry_denied": diagnostics.get("rate_limit_retry_denied"),
        "rate_limit_evidence_detected": diagnostics.get("rate_limit_evidence_detected"),
        "diagnostics": diagnostics,
    })

ok = bool(steps) and all(step["ok"] for step in steps)
failed = [step for step in steps if not step["ok"]]
reused_groups = [
    step["name"]
    for step in steps
    if step.get("status") in {"reused_validation_evidence", "reused_browser_source_lifecycle"}
    or step.get("action") in {"reused_validation_evidence", "reused_browser_source_lifecycle"}
]
executed_groups = [step["name"] for step in steps if step["name"] not in reused_groups]
validation_reuse_summary = {
    "schema": "promptbranch.release_control.validation_reuse_summary",
    "schema_version": "1.1",
    "enabled": True,
    "policy": "reuse_only_when_artifact_hash_and_validation_dimensions_match",
    "proof_status": "reused" if reused_groups else "no_reusable_evidence",
    "reused_groups": reused_groups,
    "executed_groups": executed_groups,
    "invalidated_groups": [],
    "failed_groups": [step["name"] for step in failed],
    "expected_reuse_flow": {
        "first_command": "--run-tests --strict-source-kind-matrix",
        "second_command": "--run-all-tests --strict-source-kind-matrix",
        "reusable_group": "full_direct",
        "must_still_execute_groups": ["live_profile_preflight", "live_project_ensure", "ask_live", "visual_artifact_roundtrip", "release_live", "import_smoke", "artifact_guard"],
        "reusable_browser_source_lifecycle_groups": ["full_localhost"],
    },
}

localhost_steps = [step for step in steps if step.get("diagnostics", {}).get("transport_class") == "localhost"]
localhost_rate_limit_steps = [step["name"] for step in localhost_steps if step.get("diagnostics", {}).get("rate_limit_evidence_detected") is True]
localhost_retry_allowed_violations = [step["name"] for step in localhost_steps if step.get("diagnostics", {}).get("rate_limit_retry_allowed") is not False]
localhost_retry_denied_steps = [step["name"] for step in localhost_steps if step.get("diagnostics", {}).get("rate_limit_retry_denied") is True]
localhost_failed_steps = [step["name"] for step in localhost_steps if not step.get("ok")]
localhost_matrix_cooldown_audit = {
    "schema": "promptbranch.release_control.localhost_matrix_cooldown_audit",
    "schema_version": "1.0",
    "status": "clear" if not localhost_rate_limit_steps and not localhost_retry_allowed_violations and not localhost_failed_steps else "review",
    "localhost_steps": [step["name"] for step in localhost_steps],
    "rate_limit_evidence_steps": localhost_rate_limit_steps,
    "rate_limit_retry_allowed_violations": localhost_retry_allowed_violations,
    "rate_limit_retry_denied_steps": localhost_retry_denied_steps,
    "failed_steps": localhost_failed_steps,
    "policy": "localhost/offline matrix groups must not sleep/retry on browser cooldown evidence; they should fail closed or rerun only after operator review.",
    "recommendation": "If this audit reports review, inspect localhost logs before trusting repeated --run-all-tests runs.",
}

diagnostics_summary = {
    "schema": "promptbranch.release_control.live_validation_diagnostics",
    "schema_version": "1.0",
    "transport_classes": sorted({str(step.get("diagnostics", {}).get("transport_class") or "unknown") for step in steps}),
    "source_add_timeout_steps": [step["name"] for step in steps if step.get("diagnostics", {}).get("source_add_timeout_detected") is True],
    "browser_read_timeout_steps": [step["name"] for step in steps if step.get("diagnostics", {}).get("browser_read_timeout_detected") is True],
    "rate_limit_evidence_steps": [step["name"] for step in steps if step.get("diagnostics", {}).get("rate_limit_evidence_detected") is True],
    "rate_limit_retry_denied_steps": [step["name"] for step in steps if step.get("diagnostics", {}).get("rate_limit_retry_denied") is True],
    "likely_failure_phases": {step["name"]: step.get("diagnostics", {}).get("likely_failure_phase") for step in failed},
}
summary = {
    "schema": "promptbranch.release_control.all_tests_summary",
    "schema_version": "1.0",
    "source_kind": "release_control_all_tests_summary",
    "generated_by": "chatgpt_claudecode_workflow_release_control.sh",
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "ok": ok,
    "status": "go" if ok else "fix_required",
    "final_verdict": "GO" if ok else "FIX",
    "version": version,
    "artifact": artifact,
    "test_project": project_name,
    "cleanup_policy": "unique_project_delete_frozen_retained",
    "test_transport": test_transport,
    "continue_on_failure": True,
    "step_count": len(steps),
    "failure_count": len(failed),
    "service_health_json": service_health_json,
    "diagnostics": diagnostics_summary,
    "validation_reuse": validation_reuse_summary,
    "localhost_matrix_cooldown_audit": localhost_matrix_cooldown_audit,
    "steps": steps,
    "failed_steps": failed,
}
out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"all_tests_summary: {out}")
print(f"all_tests_final_verdict: {summary['final_verdict']}")
if failed:
    print("all_tests_failed_steps: " + ", ".join(step["name"] for step in failed))
INNERPY
}

write_all_test_json_step() {
  local step_name="$1"
  local step_log="$2"
  local step_status="$3"
  local step_ok="$4"
  local step_rc="$5"
  local raw_log="${6:-}"
  python3 - "$step_name" "$step_log" "$step_status" "$step_ok" "$step_rc" "$raw_log" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
name, log_path, status, ok_text, rc_text, raw_log = sys.argv[1:7]
ok = ok_text == "true"
try:
    rc = int(rc_text)
except Exception:
    rc = 99
payload = {
    "ok": ok,
    "action": "release_control_all_tests_step",
    "profile": name,
    "status": status,
    "exit_code": rc,
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}
if raw_log:
    payload["raw_log"] = raw_log
Path(log_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
INNERPY
  record_all_test_step "$step_name" "$step_log" "$step_rc"
}


run_all_sanitize_live_seed_profile() {
  local seed_dir="$1"
  [[ -d "${seed_dir}" ]] || return 0
  find "${seed_dir}" \
    \( -name 'SingletonLock' -o -name 'SingletonSocket' -o -name 'SingletonCookie' -o -name 'DevToolsActivePort' \) \
    -delete 2>/dev/null || true
}

run_all_write_live_profile_missing_json() {
  local out_path="$1"
  local status="$2"
  local profile_dir="$3"
  local label="$4"
  python3 - "${out_path}" "${status}" "${profile_dir}" "${label}" "${repo_root}" "${run_all_shared_project_url:-}" <<'INNERPY'
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
out = Path(sys.argv[1])
status = sys.argv[2]
profile_dir = sys.argv[3]
label = sys.argv[4]
repo_root = Path(sys.argv[5])
url = sys.argv[6] or "https://chatgpt.com/"
payload = {
    "ok": False,
    "action": "release_control_live_profile_preflight",
    "status": status,
    "profile_label": label,
    "profile_dir": profile_dir,
    "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "recommendation": "Bootstrap and authenticate the exact Docker live profile before running --run-all-tests.",
    "bootstrap_commands": [
        f"./scripts/pb-docker-browser-profile-bootstrap.sh --profile-dir {profile_dir} --url {url}",
        "./scripts/pb-docker-live-profile-bootstrap.sh",
    ],
}
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(payload, indent=2, sort_keys=True))
INNERPY
}

run_all_validate_live_profile_dir() {
  local profile_dir="$1"
  local status_json="$2"
  local label="$3"
  if [[ ! -d "${profile_dir}" ]]; then
    run_all_write_live_profile_missing_json "${status_json}" "${label}_missing" "${profile_dir}" "${label}"
    return 78
  fi
  if [[ ! -w "${profile_dir}" ]]; then
    run_all_write_live_profile_missing_json "${status_json}" "${label}_not_writable" "${profile_dir}" "${label}"
    return 77
  fi
  run_all_sanitize_live_seed_profile "${profile_dir}"
  return 0
}

run_all_validate_live_seed_profile() {
  local seed_dir="$1"
  local seed_status_json="$2"
  run_all_validate_live_profile_dir "${seed_dir}" "${seed_status_json}" "live_profile_seed"
}

run_all_validate_live_pool_slot_profile() {
  local slot_dir="$1"
  local status_json="$2"
  run_all_validate_live_profile_dir "${slot_dir}" "${status_json}" "live_profile_pool_slot"
}

run_all_login_check_profile() {
  local label="$1"
  local profile_dir="$2"
  local log_path="$3"
  local rc=0
  echo "+ CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb --profile-dir ${profile_dir} login-check 2>&1 | tee -a ${log_path}"
  CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb --profile-dir "${profile_dir}" login-check 2>&1 | tee -a "${log_path}"
  rc=${PIPESTATUS[0]}
  if [[ ${rc} -ne 0 ]]; then
    cat <<MSG | tee -a "${log_path}" >&2
ERROR: ${label} login-check failed with ${rc}.
Bootstrap this exact profile before rerunning --run-all-tests:
  ./scripts/pb-docker-browser-profile-bootstrap.sh --profile-dir "${profile_dir}" --url "${run_all_shared_project_url:-https://chatgpt.com/}"
MSG
  fi
  return ${rc}
}

run_all_live_profile_preflight() {
  local rc=0
  echo "== pb test-all step: live_profile_preflight =="
  echo "live_profile_seed_dir: ${live_profile_seed_display}"
  echo "live_profile_pool_name: ${live_profile_pool_name}"
  echo "live_profile_pool_size: ${live_profile_pool_size}"
  echo "live_profile_pool_slot_dir: ${live_profile_pool_slot_display}"
  echo "live_profile_strategy: explicit_bootstrapped_slot_single_actor_no_copy_no_refresh"
  run_all_live_seed_profile_missing=0
  : > "${live_profile_preflight_raw_log}"
  if [[ -d "${live_profile_seed_dir}" ]]; then
    run_all_validate_live_seed_profile "${live_profile_seed_dir}" "${live_profile_preflight_raw_log}" ||       echo "WARN: optional live seed profile is present but invalid; release-live uses the explicit slot profile as the actor." | tee -a "${live_profile_preflight_raw_log}" >&2
  else
    echo "optional_live_seed_profile_status: missing_not_blocking" | tee -a "${live_profile_preflight_raw_log}"
  fi
  run_all_validate_live_pool_slot_profile "${live_profile_pool_slot_dir}" "${live_profile_preflight_raw_log}"
  rc=$?
  if [[ ${rc} -ne 0 ]]; then
    echo "ERROR: live profile pool slot is missing or invalid; bootstrap the exact release-live slot instead of copying profiles." >&2
    write_all_test_json_step "live_profile_preflight" "${live_profile_preflight_json}" "live_profile_pool_slot_unavailable" "false" "${rc}" "${live_profile_preflight_raw_log}"
    workflow_rc=${rc}
    return ${rc}
  fi
  run_all_login_check_profile "live_profile_pool_slot" "${live_profile_pool_slot_dir}" "${live_profile_preflight_raw_log}"
  rc=$?
  if [[ ${rc} -ne 0 ]]; then
    write_all_test_json_step "live_profile_preflight" "${live_profile_preflight_json}" "live_profile_pool_slot_not_authenticated" "false" "${rc}" "${live_profile_preflight_raw_log}"
    workflow_rc=${rc}
    return ${rc}
  fi
  write_all_test_json_step "live_profile_preflight" "${live_profile_preflight_json}" "verified_explicit_live_profiles" "true" "0" "${live_profile_preflight_raw_log}"
  return 0
}

record_all_test_skipped_step() {
  local step_name="$1"
  local step_log="$2"
  local reason="$3"
  write_all_test_json_step "$step_name" "$step_log" "$reason" "false" "78" "${live_profile_preflight_raw_log}"
  workflow_rc=78
}

record_all_test_nonblocking_skipped_step() {
  local step_name="$1"
  local step_log="$2"
  local reason="$3"
  write_all_test_json_step "$step_name" "$step_log" "$reason" "true" "0" "${live_profile_preflight_raw_log}"
}

run_all_extract_project_url_from_log() {
  local log_path="$1"
  python3 - "$log_path" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import json
import sys

raw = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
decoder = json.JSONDecoder()
candidates: list[dict] = []
for idx, char in enumerate(raw):
    if char != "{":
        continue
    try:
        value, _end = decoder.raw_decode(raw[idx:])
    except Exception:
        continue
    if not isinstance(value, dict):
        continue
    url = value.get("project_url") or value.get("resolved_project_home_url") or value.get("project_home_url")
    if value.get("ok") is True and isinstance(url, str) and url.strip():
        # Prefer the intended project-ensure payload when present.  Do not use
        # the last JSON object blindly because browser telemetry may contain
        # nested objects after the successful project-ensure payload.
        action = str(value.get("action") or "")
        if action in {"ensure_project", "project_ensure"}:
            candidates.append(value)
        elif not candidates:
            candidates.append(value)
if not candidates:
    raise SystemExit(1)
last = candidates[-1]
url = last.get("project_url") or last.get("resolved_project_home_url") or last.get("project_home_url")
if not isinstance(url, str) or not url.strip():
    raise SystemExit(2)
print(url.strip())
INNERPY
}

run_all_url_is_conversation_url() {
  local url="$1"
  python3 - "$url" <<'INNERPY'
from __future__ import annotations
import sys
import urllib.parse
url = str(sys.argv[1] or "").strip()
if not url:
    raise SystemExit(1)
parsed = urllib.parse.urlparse(url)
parts = [part for part in parsed.path.split('/') if part]
raise SystemExit(0 if 'c' in parts else 1)
INNERPY
}

run_all_extract_conversation_url_from_log() {
  local log_path="$1"
  python3 - "$log_path" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import json
import sys
import urllib.parse

def is_conversation_url(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urllib.parse.urlparse(value.strip())
    return 'c' in [part for part in parsed.path.split('/') if part]

raw = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
decoder = json.JSONDecoder()
candidates: list[str] = []
for idx, char in enumerate(raw):
    if char != '{':
        continue
    try:
        value, _end = decoder.raw_decode(raw[idx:])
    except Exception:
        continue
    if not isinstance(value, dict):
        continue
    for key in ("conversation_url", "current_conversation_url"):
        url = value.get(key)
        if is_conversation_url(url):
            candidates.append(str(url).strip())
    response = value.get("response")
    if isinstance(response, dict):
        url = response.get("conversation_url")
        if is_conversation_url(url):
            candidates.append(str(url).strip())
if not candidates:
    raise SystemExit(1)
print(candidates[-1])
INNERPY
}

run_all_log_has_docker_live_profile_challenge() {
  local log_path="$1"
  [[ -f "${log_path}" ]] || return 1
  grep -Fqi "docker_live_profile_challenged" "${log_path}"
}

run_all_log_has_cloudflare_challenge() {
  local log_path="$1"
  [[ -f "${log_path}" ]] || return 1
  if run_all_log_has_docker_live_profile_challenge "${log_path}"; then
    return 0
  fi
  python3 - "${log_path}" <<'INNERPY'
from __future__ import annotations
from pathlib import Path
import json
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
lowered = text.lower()
fixed_markers = (
    "just a moment",
    "__cf_chl",
    "cloudflare",
    "auth_challenge_detected",
    "docker_live_profile_challenged",
)
if any(marker in lowered for marker in fixed_markers):
    raise SystemExit(0)
if "challenge_detected" in lowered and ("true" in lowered or "=true" in lowered or ": true" in lowered):
    raise SystemExit(0)

decoder = json.JSONDecoder()
for idx, char in enumerate(text):
    if char != "{":
        continue
    try:
        value, _end = decoder.raw_decode(text[idx:])
    except Exception:
        continue
    if not isinstance(value, dict):
        continue
    stack = [value]
    while stack:
        item = stack.pop()
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        challenge_type = str(item.get("challenge_type") or item.get("response_challenge_type") or "")
        if status == "docker_live_profile_challenged" or challenge_type == "docker_live_profile_challenged":
            raise SystemExit(0)
        if item.get("challenge_detected") is True:
            raise SystemExit(0)
        for nested in item.values():
            if isinstance(nested, dict):
                stack.append(nested)
            elif isinstance(nested, list):
                stack.extend(v for v in nested if isinstance(v, dict))
raise SystemExit(1)
INNERPY
}

run_all_ensure_shared_live_conversation() {
  local rc=0
  local command_rc=0
  local extracted_conversation_url=""
  local sentinel="LIVE_CONVERSATION_BOOTSTRAP_${ver_plain//./_}"

  if run_all_url_is_conversation_url "${run_all_shared_project_url}"; then
    run_all_shared_conversation_url="${run_all_shared_project_url}"
    echo "shared_live_conversation_url: ${run_all_shared_conversation_url}" | tee -a "${run_all_project_ensure_log}"
    return 0
  fi

  echo "live_conversation_strategy: create_new_task_inside_shared_live_project" | tee -a "${run_all_project_ensure_log}"
  echo "live_conversation_project_url: ${run_all_shared_project_url}" | tee -a "${run_all_project_ensure_log}"
  echo "+ pb --profile-dir ${live_profile_pool_slot_dir} use ${run_all_shared_project_url} --json 2>&1 | tee -a ${run_all_project_ensure_log}"
  CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb --profile-dir "${live_profile_pool_slot_dir}" use "${run_all_shared_project_url}" --json 2>&1 | tee -a "${run_all_project_ensure_log}"
  command_rc=${PIPESTATUS[0]}
  if [[ ${command_rc} -ne 0 ]]; then
    echo "ERROR: live_conversation_url_missing: failed to select shared live project before conversation bootstrap" | tee -a "${run_all_project_ensure_log}" >&2
    return ${command_rc}
  fi

  echo "+ pb --profile-dir ${live_profile_pool_slot_dir} ask --new-task --retries 0 <bootstrap prompt> 2>&1 | tee -a ${run_all_project_ensure_log}"
  PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1 CHATGPT_FAIL_FAST_ON_CHALLENGE=1 \
    pb --profile-dir "${live_profile_pool_slot_dir}" ask --new-task --retries 0 "Reply with exactly the single token ${sentinel} and nothing else." 2>&1 | tee -a "${run_all_project_ensure_log}"
  command_rc=${PIPESTATUS[0]}
  rc=${command_rc}

  if extracted_conversation_url="$(run_all_extract_conversation_url_from_log "${run_all_project_ensure_log}")"; then
    run_all_shared_conversation_url="${extracted_conversation_url}"
    echo "shared_live_conversation_url: ${run_all_shared_conversation_url}" | tee -a "${run_all_project_ensure_log}"
    rc=0
  else
    echo "ERROR: live_conversation_url_missing: live_project_ensure produced only /project and conversation bootstrap did not return /c/..." | tee -a "${run_all_project_ensure_log}" >&2
    rc=1
  fi

  if [[ ${rc} -ne 0 ]]; then
    if run_all_log_has_cloudflare_challenge "${run_all_project_ensure_log}"; then
      echo "status: docker_live_profile_challenged" | tee -a "${run_all_project_ensure_log}" >&2
    fi
    return ${rc}
  fi
  return 0
}

run_all_ensure_shared_live_project() {
  local rc=0
  local command_rc=0
  local extracted_url=""
  echo "== pb test-all step: live_project_ensure =="
  echo "release_test_project_name: ${release_test_project_name}"
  echo "reuse_policy: one_run_scoped_project_for_all_test_all_live_steps"
  : > "${run_all_project_ensure_log}"
  echo "+ pb --profile-dir ${live_profile_pool_slot_dir} project-ensure ${release_test_project_name} --memory-mode project-only --keep-open 2>&1 | tee -a ${run_all_project_ensure_log}"
  CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb --profile-dir "${live_profile_pool_slot_dir}" project-ensure "${release_test_project_name}" --memory-mode project-only --keep-open 2>&1 | tee -a "${run_all_project_ensure_log}"
  command_rc=${PIPESTATUS[0]}
  rc=${command_rc}

  if extracted_url="$(run_all_extract_project_url_from_log "${run_all_project_ensure_log}")"; then
    run_all_shared_project_url="${extracted_url}"
    echo "shared_live_project_url: ${run_all_shared_project_url}" | tee -a "${run_all_project_ensure_log}"
    if [[ ${command_rc} -ne 0 ]]; then
      if run_all_log_has_rate_limit_evidence "${run_all_project_ensure_log}"; then
        echo "WARN: recovered rate-limit evidence detected for live_project_ensure; project_url was verified, so release-control will continue without blocking the live phase." | tee -a "${run_all_project_ensure_log}" >&2
        echo "live_project_ensure_status: verified_with_recovered_rate_limit" | tee -a "${run_all_project_ensure_log}"
        rc=0
      else
        echo "WARN: live_project_ensure returned project_url but command exited with ${command_rc}; treating as failed because no recovered rate-limit evidence was found." | tee -a "${run_all_project_ensure_log}" >&2
        rc=${command_rc}
      fi
    fi
    if [[ ${rc} -eq 0 ]] && ! run_all_ensure_shared_live_conversation; then
      echo "WARN: live_project_ensure could not establish a /c/... conversation URL for ask/live steps." | tee -a "${run_all_project_ensure_log}" >&2
      rc=1
    fi
  else
    echo "WARN: live_project_ensure did not return a project URL." | tee -a "${run_all_project_ensure_log}" >&2
    if [[ ${rc} -eq 0 ]]; then
      rc=1
    fi
  fi

  if [[ ${rc} -ne 0 ]]; then
    echo "WARN: live_project_ensure failed with ${rc}; live browser steps will be skipped." >&2
    workflow_rc=${rc}
  fi
  record_all_test_step "live_project_ensure" "${run_all_project_ensure_log}" "${rc}"
  return ${rc}
}

run_all_finalize_summary() {
  run_all_finalize_summary
}

run_all_live_validation_steps() {
  local guard_zip="${artifact_zip}"
  if [[ ! -f "${guard_zip}" && -n "${download_zip:-}" && -f "${download_zip}" ]]; then
    guard_zip="${download_zip}"
  fi

  echo "== pb test all: live/artifact/import/guard steps =="
  echo "continue_on_failure: true"
  echo "release_test_project_name: ${release_test_project_name}"
  echo "cleanup_policy: unique_project_delete_frozen_retained"

  if [[ ${run_all_browser_guardrail_seen} -eq 1 ]]; then
    echo "ERROR: browser_backend_403_guardrail observed during full validation; skipping live browser phases to avoid using a poisoned browser/profile state." >&2
    record_all_test_skipped_step "live_profile_preflight" "${live_profile_preflight_json}" "skipped_browser_backend_403_guardrail"
    record_all_test_skipped_step "live_project_ensure" "${run_all_project_ensure_log}" "skipped_browser_backend_403_guardrail"
    record_all_test_skipped_step "ask_live" "${ask_live_log}" "skipped_browser_backend_403_guardrail"
    record_all_test_skipped_step "visual_artifact_roundtrip" "${visual_artifact_roundtrip_log}" "skipped_browser_backend_403_guardrail"
    record_all_test_skipped_step "release_live" "${release_live_log}" "skipped_browser_backend_403_guardrail"
    run_all_json_step "import_smoke" "${import_smoke_log}" pb test import-smoke --json
    run_all_json_step "artifact_guard" "${artifact_guard_log}" pb artifact guard --zip "${guard_zip}" --version "${ver}" --json
    write_all_tests_summary "${all_tests_summary_json}" "${all_test_step_specs[@]}"
    if ! python3 - "${all_tests_summary_json}" <<'INNERPY'
from pathlib import Path
import json
import sys
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if payload.get("ok") is True and payload.get("final_verdict") == "GO" else 1)
INNERPY
    then
      workflow_rc=1
    fi
    return 0
  fi

  if run_all_live_profile_preflight; then
    if run_all_ensure_shared_live_project; then
      if [[ -z "${run_all_shared_conversation_url}" ]] || ! run_all_url_is_conversation_url "${run_all_shared_conversation_url}"; then
        echo "ERROR: live_conversation_url_missing: refusing to run ask/live steps against a /project URL" | tee -a "${run_all_project_ensure_log}" >&2
        record_all_test_skipped_step "ask_live" "${ask_live_log}" "live_conversation_url_missing"
        record_all_test_skipped_step "visual_artifact_roundtrip" "${visual_artifact_roundtrip_log}" "live_conversation_url_missing"
        record_all_test_skipped_step "release_live" "${release_live_log}" "live_conversation_url_missing"
      else
        if ! run_all_json_step "ask_live" "${ask_live_log}" env PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1 CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb test ask-live --profile-dir "${live_profile_pool_slot_dir}" --profile-lease --conversation-url "${run_all_shared_conversation_url}" --keep-project --retries 0 --json; then
          if run_all_log_has_docker_live_profile_challenge "${ask_live_log}"; then
            echo "ERROR: ask_live returned docker_live_profile_challenged; skipping remaining live browser steps to avoid a challenged-profile cascade." | tee -a "${ask_live_log}" >&2
            record_all_test_skipped_step "visual_artifact_roundtrip" "${visual_artifact_roundtrip_log}" "skipped_ask_live_docker_live_profile_challenged"
            record_all_test_skipped_step "release_live" "${release_live_log}" "skipped_ask_live_docker_live_profile_challenged"
          else
            run_all_json_step "visual_artifact_roundtrip" "${visual_artifact_roundtrip_log}" env PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1 CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb test visual-artifact-roundtrip --profile-dir "${live_profile_pool_slot_dir}" --profile-lease --conversation-url "${run_all_shared_conversation_url}" --keep-project --retries 0 --json
            run_all_json_step "release_live" "${release_live_log}" env PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1 CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb test release-live --profile-dir "${live_profile_pool_slot_dir}" --profile-lease --conversation-url "${run_all_shared_conversation_url}" --keep-project --retries 0 --json
          fi
        else
          run_all_json_step "visual_artifact_roundtrip" "${visual_artifact_roundtrip_log}" env PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1 CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb test visual-artifact-roundtrip --profile-dir "${live_profile_pool_slot_dir}" --profile-lease --conversation-url "${run_all_shared_conversation_url}" --keep-project --retries 0 --json
          run_all_json_step "release_live" "${release_live_log}" env PROMPTBRANCH_RELEASE_LIVE_FAIL_FAST_ON_CHALLENGE=1 CHATGPT_FAIL_FAST_ON_CHALLENGE=1 pb test release-live --profile-dir "${live_profile_pool_slot_dir}" --profile-lease --conversation-url "${run_all_shared_conversation_url}" --keep-project --retries 0 --json
        fi
      fi
    else
      record_all_test_skipped_step "ask_live" "${ask_live_log}" "skipped_live_project_ensure_failed"
      record_all_test_skipped_step "visual_artifact_roundtrip" "${visual_artifact_roundtrip_log}" "skipped_live_project_ensure_failed"
      record_all_test_skipped_step "release_live" "${release_live_log}" "skipped_live_project_ensure_failed"
    fi
  else
    record_all_test_skipped_step "live_project_ensure" "${run_all_project_ensure_log}" "skipped_live_profile_preflight_failed"
    record_all_test_skipped_step "ask_live" "${ask_live_log}" "skipped_live_profile_preflight_failed"
    record_all_test_skipped_step "visual_artifact_roundtrip" "${visual_artifact_roundtrip_log}" "skipped_live_profile_preflight_failed"
    record_all_test_skipped_step "release_live" "${release_live_log}" "skipped_live_profile_preflight_failed"
  fi
  run_all_json_step "import_smoke" "${import_smoke_log}" pb test import-smoke --json
  run_all_json_step "artifact_guard" "${artifact_guard_log}" pb artifact guard --zip "${guard_zip}" --version "${ver}" --json

  write_all_tests_summary "${all_tests_summary_json}" "${all_test_step_specs[@]}"
  if ! python3 - "${all_tests_summary_json}" <<'INNERPY'
from pathlib import Path
import json
import sys
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if payload.get("ok") is True and payload.get("final_verdict") == "GO" else 1)
INNERPY
  then
    workflow_rc=1
  fi
}

if [[ ${skip_tests} -eq 0 ]]; then
  pb_auth_bootstrap "pre_tests" || fail "release-control auth bootstrap failed before tests"
  start_test_session_log
  set +e

  case "${test_transport}" in
    direct)
      run_full_test_transport "direct" "${service_base_url}" "${full_log}" "${report_json}" "${structured_summary_json}"
      ;;
    localhost)
      run_full_test_transport "localhost" "${localhost_base_url}" "${full_log}" "${report_json}" "${structured_summary_json}"
      ;;
    both)
      run_full_test_transport "direct" "${service_base_url}" "${direct_full_log}" "${direct_report_json}" "${structured_summary_json}"
      run_full_test_transport "localhost" "${localhost_base_url}" "${localhost_full_log}" "${localhost_report_json}" "${release_log_dir}/post_release_validation.localhost.${ver}.summary.json"
      ;;
  esac

  if [[ ${run_all_tests} -eq 1 ]]; then
    if [[ ${run_failing_tests} -eq 1 ]]; then
      echo "== pb test all: focused failing tests only =="
      echo "focused_failing_tests: text_source_add_compatibility"
      echo "skipped_steps: live_profile_preflight, ask_live, visual_artifact_roundtrip, release_live, import_smoke, artifact_guard"
      run_all_finalize_summary
    else
      run_all_live_validation_steps
    fi
  fi

  set -e
  stop_test_session_log
fi

if [[ ${auth_only_validation} -eq 1 ]]; then
  set +e
  run_auth_only_validation
  auth_only_validation_rc=$?
  set -e
  if [[ ${auth_only_validation_rc} -ne 0 ]]; then
    workflow_rc=${auth_only_validation_rc}
  fi
fi

if [[ ${skip_tests} -eq 1 && ${adopt_current} -eq 1 ]]; then
  adopt_current_artifact
fi

if [[ ${adopt_after_validation} -eq 1 ]]; then
  adopt_after_validation_if_green
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
    printf '%s\n' "${value}"
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
structured_summary: $(summary_value "${tests_summary_active}" "${structured_summary_json}")
adopt_current: ${adopt_current}
adopt_if_green: ${adopt_if_green}
adopt_after_validation: ${adopt_after_validation}
test_session:  $(summary_value "${tests_summary_active}" "${test_session_log}")
service_log:   $(summary_value "${docker_log_summary_active}" "${service_log}")
service_start: $(summary_value "${service_summary_active}" "${service_start_log}")
runtime_mode:   ${runtime_mode}
compose_name:   ${compose_project_name}
service_port:   ${service_port}
service_base:   ${service_base_url}
test_transport: ${test_transport}
run_all_tests:  ${run_all_tests}
run_failing_tests: ${run_failing_tests}
run_all_strict_source_kind_matrix: ${run_all_strict_source_kind_matrix}
all_tests_summary: $(summary_value "${run_all_tests}" "${all_tests_summary_json}")
test_project:   ${release_test_project_name}
test_cleanup:   unique_project_delete_frozen_retained
localhost_base: ${localhost_base_url}
direct_log: $(summary_value "${tests_summary_active}" "${direct_full_log}")
localhost_log: $(summary_value "${tests_summary_active}" "${localhost_full_log}")
service_health: $(summary_value "${service_summary_active}" "${service_health_json}")
compose_ps:     $(summary_value "${service_summary_active}" "${service_compose_ps_json}")
service_pid:   $(summary_value "${service_summary_active}" "${service_pid_file}")
exit_code:     ${workflow_rc}
DONE

exit "${workflow_rc}"
