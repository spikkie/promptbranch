#!/usr/bin/env bash
set -Eeuo pipefail

# ChatGPT Claude Code Workflow release ZIP / compare / commit / install / source-control workflow.
# Run from the repository root: /home/spikkie/git/chatgpt_claudecode_workflow
#
# Version precedence, highest first:
#   1. --version / -v / first positional argument
#   2. PB_RELEASE_VERSION environment variable
#   3. VERSION file in the repo root
#
# This script uses real commands instead of shell aliases:
#   bc      -> bcompare
#   ga .    -> git add .
#   gcm ... -> git commit -m ...
#   gp      -> git push
#   zip_it  -> ~/scripts/zip_with_not_to_zip.sh, with Python fallback
#   pbsa    -> promptbranch src add ...
#
# Important fix: ./run_chatgpt_service.sh is started DETACHED by default so this
# workflow does not hang forever on a foreground service process.

project_name="chatgpt_claudecode_workflow"
repo_root="$(pwd)"
version_file="${repo_root}/VERSION"
downloads_dir="${DOWNLOADS_DIR:-${HOME}/Downloads}"
work_parent="${TMPDIR:-/tmp}/${project_name}_release_import"
container_id="${PROMPTBRANCH_CONTAINER_ID:-}"
owner_user="${PROMPTBRANCH_OWNER_USER:-${SUDO_USER:-${USER}}}"
owner_group="${PROMPTBRANCH_OWNER_GROUP:-${owner_user}}"
version_arg="${PB_RELEASE_VERSION:-}"

skip_compare=0
skip_commit=0
skip_push=0
skip_source_add=0
skip_install=0
skip_chown=0
skip_service=0
skip_tests=1
skip_docker_logs=0
keep_workdir=0

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
  $(basename "$0") --version v0.0.190 [options]
  $(basename "$0") v0.0.190 [options]

Options:
  -v, --version VERSION       Highest-precedence release version override.
                              Accepts v0.0.190, 0.0.190, or ${project_name}_v0.0.190.zip.
      --downloads-dir DIR     Directory containing the downloaded baseline ZIP. Default: ~/Downloads.
      --container-id ID       Docker container id/name for service logs. Auto-detected if omitted.
      --owner USER[:GROUP]    Owner for .pb_profile after install. Default: ${owner_user}:${owner_group}.
      --packager PATH         Packaging helper. Default: ${default_packager}.
      --skip-compare          Skip Beyond Compare import comparison.
      --skip-commit           Skip git add/commit/push.
      --no-push               Commit but do not git push.
      --skip-source-add       Skip promptbranch src add.
      --skip-install          Skip pipx reinstall from generated ZIP.
      --skip-chown            Skip chown of .pb_profile.
      --skip-service          Skip ./run_chatgpt_service.sh.
      --service-mode MODE     detached or foreground. Default: detached.
                              detached mode starts ./run_chatgpt_service.sh with nohup and continues.
      --service-timeout SEC   Seconds to wait for service readiness. Default: 90.
      --test-timeout SEC      Max seconds for pb test full. Default: 3600.
      --run-tests             Run pb test full/report. Disabled by default.
                              The test block is wrapped in startlog/stoplog when available,
                              or an internal tee-based session log fallback otherwise.
      --skip-tests            Explicitly skip pb test full/report.
      --skip-docker-logs      Skip docker logs capture.
      --keep-workdir          Keep temporary extracted comparison directory.
  -h, --help                  Show this help.

Version precedence:
  CLI argument > PB_RELEASE_VERSION > VERSION file

Typical use:
  $(basename "$0") --version v0.0.190
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
  raw="${raw#_}"
  if [[ "${raw}" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    raw="${raw#v}"
    printf 'v%s\n' "${raw}"
    return 0
  fi
  return 1
}

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
    --skip-compare) skip_compare=1; shift ;;
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

if [[ -z "${version_arg}" ]]; then
  [[ -f "${version_file}" ]] || fail "VERSION file not found and no --version supplied: ${version_file}"
  version_arg="$(head -n 1 "${version_file}" | tr -d '[:space:]')"
fi

ver="$(normalize_version "${version_arg}")" || fail "version must look like v0.0.190, 0.0.190, or ${project_name}_v0.0.190.zip; got '${version_arg}'"
ver_plain="${ver#v}"
artifact_zip="${project_name}_${ver}.zip"
download_zip="${downloads_dir}/${artifact_zip}"
work_dir="${work_parent}/${project_name}_${ver}"
full_log="pb_test.full.${ver}.log"
report_json="pb_test.full.${ver}.report.json"
test_session_log="${PROMPTBRANCH_TEST_SESSION_LOG:-session_$(date +%Y%m%d_%H%M%S).log}"
test_session_logging_mode="none"
service_log="promptbranch-service:${ver_plain}.log"
service_start_log="promptbranch-service-start:${ver_plain}.log"
service_pid_file=".promptbranch-service-start.${ver_plain}.pid"

[[ -f "${download_zip}" ]] || fail "Download ZIP not found: ${download_zip}"

need_cmd unzip
need_cmd git
need_cmd python3
need_cmd pipx
need_cmd promptbranch
if [[ ${skip_tests} -eq 0 || ${skip_service} -eq 0 ]]; then
  need_cmd timeout
fi
if [[ ${skip_compare} -eq 0 ]]; then
  need_cmd bcompare
fi
if [[ ${skip_docker_logs} -eq 0 ]]; then
  need_cmd docker
fi

printf '\n== Release control ==\n'
printf 'repo_root:      %s\n' "${repo_root}"
printf 'version:        %s\n' "${ver}"
printf 'artifact_zip:   %s\n' "${artifact_zip}"
printf 'download_zip:   %s\n' "${download_zip}"
printf 'work_dir:       %s\n' "${work_dir}"
printf 'service_mode:   %s\n' "${service_mode}"
printf 'service_wait:   %ss\n' "${service_timeout_seconds}"
printf 'test_timeout:   %ss\n' "${test_timeout_seconds}"
printf '\n'

# Import downloaded baseline ZIP into a temporary directory and visually compare it to the repo.
rm -rf "${work_dir}"
mkdir -p "${work_dir}"
cp "${download_zip}" "${work_dir}/${artifact_zip}"
(
  cd "${work_dir}"
  unzip -q "${artifact_zip}"
  rm -f "${artifact_zip}"
)

if [[ ${skip_compare} -eq 0 ]]; then
  # Beyond Compare may return non-zero for differences; differences are the point here.
  bcompare "${work_dir}" "${repo_root}" || true
fi

if [[ ${keep_workdir} -eq 0 ]]; then
  rm -rf "${work_dir}"
fi

# Commit current working tree with the release ZIP name as commit message.
if [[ ${skip_commit} -eq 0 ]]; then
  git add .
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

# Normalize possible packager output names to canonical artifact name.
for candidate in \
  "source_${ver}.zip" \
  "source_${ver_plain}.zip" \
  "source_${project_name}_${ver}.zip" \
  "source_${project_name}_${ver_plain}.zip" \
  "${project_name}_${ver}.zip"
do
  if [[ -f "${candidate}" ]]; then
    if [[ "${candidate}" != "${artifact_zip}" ]]; then
      mv -f "${candidate}" "${artifact_zip}"
    fi
    break
  fi
done

[[ -f "${artifact_zip}" ]] || fail "could not find packaging output for version ${ver}; expected ${artifact_zip} or source_* variants"

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

# Restore ownership of Promptbranch profile if needed.
if [[ ${skip_chown} -eq 0 && -d "${repo_root}/.pb_profile" ]]; then
  sudo chown -R "${owner_user}:${owner_group}" "${repo_root}/.pb_profile/"
fi


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
  echo "Logging started: ${repo_root}/${test_session_log}"
  echo "Run completed test logging will restore normal stdout/stderr automatically."
}

stop_test_session_log() {
  case "${test_session_logging_mode}" in
    external)
      stoplog || true
      ;;
    internal)
      echo "Logging stopped: ${repo_root}/${test_session_log}"
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

wait_for_promptbranch_service() {
  local deadline=$((SECONDS + service_timeout_seconds))
  local detected=""
  echo "Waiting up to ${service_timeout_seconds}s for Promptbranch service to be observable..."
  while (( SECONDS < deadline )); do
    if command -v docker >/dev/null 2>&1; then
      detected="$(docker ps --format '{{.ID}} {{.Image}} {{.Names}}' | awk '/promptbranch|chatgpt/ {print $1; exit}' || true)"
      if [[ -n "${detected}" ]]; then
        container_id="${container_id:-${detected}}"
        echo "Detected service container: ${container_id}"
        return 0
      fi
    fi
    # Service may run without a recognizable Docker name. Probe the common local port gently.
    if python3 - <<'PY' >/dev/null 2>&1
import urllib.request
for path in ("/healthz", "/health", "/"):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000" + path, timeout=1.0) as response:
            if response.status < 500:
                raise SystemExit(0)
    except Exception:
        pass
raise SystemExit(1)
PY
    then
      echo "Promptbranch service responded on http://127.0.0.1:8000"
      return 0
    fi
    sleep 2
  done
  echo "WARN: service readiness was not confirmed within ${service_timeout_seconds}s; continuing." >&2
  echo "WARN: inspect ${service_start_log} if later commands fail." >&2
  return 0
}

# Start/restart ChatGPT service using repo script.
if [[ ${skip_service} -eq 0 ]]; then
  [[ -x "./run_chatgpt_service.sh" ]] || fail "service script not executable: ./run_chatgpt_service.sh"
  if [[ "${service_mode}" == "detached" ]]; then
    echo "Starting ./run_chatgpt_service.sh detached; output -> ${service_start_log}"
    rm -f "${service_pid_file}"
    nohup ./run_chatgpt_service.sh >"${service_start_log}" 2>&1 &
    service_pid=$!
    echo "${service_pid}" > "${service_pid_file}"
    disown "${service_pid}" 2>/dev/null || true
    echo "Service start process PID: ${service_pid}"
    echo "PID file: ${service_pid_file}"
    wait_for_promptbranch_service
  else
    echo "Running ./run_chatgpt_service.sh in foreground with ${service_timeout_seconds}s timeout."
    if ! timeout --foreground "${service_timeout_seconds}" ./run_chatgpt_service.sh; then
      echo "WARN: service foreground command exited non-zero or timed out." >&2
      workflow_rc=1
    fi
  fi
fi

# Run full suite and parsed report. Always try to create a report, even if the suite fails.
if [[ ${skip_tests} -eq 0 ]]; then
  start_test_session_log
  test_rc=0
  report_rc=0
  set +e

  echo "+ timeout --foreground ${test_timeout_seconds} pb test full --json 2>&1 | tee ${full_log}"
  timeout --foreground "${test_timeout_seconds}" pb test full --json 2>&1 | tee "${full_log}"
  test_rc=${PIPESTATUS[0]}
  if [[ ${test_rc} -ne 0 ]]; then
    echo "WARN: pb test full exited with ${test_rc}; continuing to test report." >&2
    workflow_rc=${test_rc}
  fi

  echo "+ pb test report ${full_log} --json"
  pb test report "${full_log}" --json | tee "${report_json}"
  report_rc=${PIPESTATUS[0]}
  if [[ ${report_rc} -ne 0 ]]; then
    echo "WARN: pb test report exited with ${report_rc}." >&2
    workflow_rc=${report_rc}
  fi

  set -e
  stop_test_session_log
fi

# Capture service logs.
if [[ ${skip_docker_logs} -eq 0 ]]; then
  if [[ -z "${container_id}" ]]; then
    container_id="$(docker ps --format '{{.ID}} {{.Image}} {{.Names}}' | awk '/promptbranch|chatgpt/ {print $1; exit}')"
  fi
  if [[ -z "${container_id}" ]]; then
    echo "WARN: no promptbranch/chatgpt docker container auto-detected; skipping docker logs" >&2
  else
    docker logs "${container_id}" > "${service_log}"
    echo "Service log written: ${service_log}"
  fi
fi

cat <<DONE

Release workflow completed.
version:       ${ver}
artifact:      ${artifact_zip}
full_log:      ${full_log}
report_json:   ${report_json}
test_session:  ${test_session_log}
service_log:   ${service_log}
service_start: ${service_start_log}
service_pid:   ${service_pid_file}
exit_code:     ${workflow_rc}
DONE

exit "${workflow_rc}"
