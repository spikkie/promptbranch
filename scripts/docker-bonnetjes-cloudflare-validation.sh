#!/usr/bin/env bash
set -euo pipefail

# One-shot Bonnetjes Cloudflare validation workflow.
#
# This is intentionally KISS and operator-visible:
#   1. Optionally install a Promptbranch ZIP candidate.
#   2. Create/open one fresh host Chrome profile for manual login.
#   3. After Chrome closes, run the Docker Bonnetjes Cloudflare parity check
#      against the exact same profile as a bind mount.
#   4. Validate the final summary strictly.
#
# It never calls /v1/project-sources, /v1/login-check, or any Google/login
# automation path. The only manual step is the visible host Chrome login.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

install_artifact="${PROMPTBRANCH_VALIDATION_INSTALL_ARTIFACT:-}"
install_version="${PROMPTBRANCH_VALIDATION_INSTALL_VERSION:-}"
profile_dir="${PROMPTBRANCH_HOST_PROFILE_DIR:-}"
reuse_profile=0
skip_bootstrap=0
max_wait_seconds="${PROMPTBRANCH_CLOUDFLARE_CHECK_MAX_WAIT_SECONDS:-300}"
poll_seconds="${PROMPTBRANCH_CLOUDFLARE_CHECK_POLL_SECONDS:-10}"

usage() {
  cat <<'HELP'
Usage: docker-bonnetjes-cloudflare-validation.sh [options]

One-shot Bonnetjes Cloudflare validation phase:
  1. optional install of a candidate ZIP
  2. visible host Chrome clean-profile login bootstrap
  3. Docker Bonnetjes Cloudflare parity check against that profile
  4. strict validation of the resulting summary.json

Options:
  --install-artifact ZIP     Optional candidate ZIP to install first.
  --install-version VERSION  Version used with --install-artifact, for example v0.1.103.10.1.
  --profile-dir PATH         Profile directory to create/reuse. Default: ./.pb_profile_bonnetjes_manual_<UTC timestamp>.
  --reuse-profile            Do not remove the profile before opening host Chrome.
  --skip-bootstrap           Do not open host Chrome; use an already logged-in profile from --profile-dir/PROMPTBRANCH_HOST_PROFILE_DIR.
  --max-wait-seconds N       Cloudflare check timeout. Default: 300.
  --poll-seconds N           Cloudflare check polling interval. Default: 10.
  --help                     Show this help.

Environment equivalents:
  PROMPTBRANCH_VALIDATION_INSTALL_ARTIFACT
  PROMPTBRANCH_VALIDATION_INSTALL_VERSION
  PROMPTBRANCH_HOST_PROFILE_DIR
  PROMPTBRANCH_CLOUDFLARE_CHECK_MAX_WAIT_SECONDS
  PROMPTBRANCH_CLOUDFLARE_CHECK_POLL_SECONDS

Success criteria:
  - docker profile mode is bonnetjes-cloudflare-parity
  - profile is bind-mounted as /app/profile
  - Cloudflare challenge is not detected
  - logged_in=true
  - composer_visible=true
  - release_blocking=false
  - Project Source mutation remains disabled
HELP
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-artifact)
      install_artifact="${2:-}"
      shift 2
      ;;
    --install-version)
      install_version="${2:-}"
      shift 2
      ;;
    --profile-dir)
      profile_dir="${2:-}"
      shift 2
      ;;
    --reuse-profile)
      reuse_profile=1
      shift
      ;;
    --skip-bootstrap)
      skip_bootstrap=1
      shift
      ;;
    --max-wait-seconds)
      max_wait_seconds="${2:-}"
      shift 2
      ;;
    --poll-seconds)
      poll_seconds="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

case "${max_wait_seconds}" in
  ''|*[!0-9]*) echo "ERROR: max wait must be an integer: ${max_wait_seconds}" >&2; exit 64 ;;
esac
case "${poll_seconds}" in
  ''|*[!0-9]*) echo "ERROR: poll seconds must be an integer: ${poll_seconds}" >&2; exit 64 ;;
esac

if [[ -z "${profile_dir}" ]]; then
  profile_dir="${repo_root}/.pb_profile_bonnetjes_manual_$(date -u +%Y%m%dT%H%M%SZ)"
elif [[ "${profile_dir}" != /* ]]; then
  profile_dir="${repo_root}/${profile_dir}"
fi

run_ts="$(date -u +%Y%m%dT%H%M%SZ)"
validation_dir="debug_artifacts/docker-browser-parity/bonnetjes-validation/${run_ts}"
mkdir -p "${validation_dir}"

log() {
  printf '%s\n' "$*" | tee -a "${validation_dir}/validation.log"
}

log "== Bonnetjes Cloudflare one-shot validation =="
log "validation_dir=${validation_dir}"
log "profile_dir=${profile_dir}"
log "max_wait_seconds=${max_wait_seconds}"
log "poll_seconds=${poll_seconds}"
log "skip_bootstrap=${skip_bootstrap}"
log "reuse_profile=${reuse_profile}"

if [[ -n "${install_artifact}" ]]; then
  if [[ -z "${install_version}" ]]; then
    echo "ERROR: --install-version is required with --install-artifact" >&2
    exit 64
  fi
  if [[ ! -f "${install_artifact}" ]]; then
    echo "ERROR: install artifact not found: ${install_artifact}" >&2
    exit 66
  fi
  log "== install candidate =="
  # Use the release installer used by this project line. Keep output as evidence.
  pb release install \
    --artifact "${install_artifact}" \
    --version "${install_version}" \
    --json \
    | tee "${validation_dir}/install.json"
fi

if [[ "${skip_bootstrap}" == "0" ]]; then
  log "== visible host Chrome login bootstrap =="
  bootstrap_args=(--profile-dir "${profile_dir}")
  if [[ "${reuse_profile}" == "1" ]]; then
    bootstrap_args+=(--reuse)
  fi
  ./scripts/docker-bonnetjes-clean-login-profile-bootstrap.sh "${bootstrap_args[@]}" \
    2>&1 | tee "${validation_dir}/bootstrap.log"
else
  log "== skip bootstrap; using existing profile =="
  if [[ ! -d "${profile_dir}" ]]; then
    echo "ERROR: --skip-bootstrap profile does not exist: ${profile_dir}" >&2
    exit 66
  fi
fi

log "== ensure host Chrome released the profile =="
if ps -ef | grep -F "${profile_dir}" | grep -v grep > "${validation_dir}/profile-processes.txt"; then
  cat "${validation_dir}/profile-processes.txt" >&2
  echo "ERROR: Chrome still appears to be using the profile. Close Chrome and rerun with --skip-bootstrap --profile-dir '${profile_dir}'." >&2
  exit 75
fi
rm -f \
  "${profile_dir}/SingletonLock" \
  "${profile_dir}/SingletonCookie" \
  "${profile_dir}/SingletonSocket" \
  2>/dev/null || true

log "== Docker Bonnetjes Cloudflare check =="
check_start_epoch="$(date +%s)"
check_rc=0
PROMPTBRANCH_DOCKER_BROWSER_PROFILE=bonnetjes-cloudflare-parity \
PROMPTBRANCH_HOST_PROFILE_DIR="${profile_dir}" \
PROMPTBRANCH_PROFILE_DIR=/app/profile \
PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS="${max_wait_seconds}" \
./scripts/docker-browser-parity-cloudflare-check.sh \
  --max-wait-seconds "${max_wait_seconds}" \
  --poll-seconds "${poll_seconds}" \
  2>&1 | tee "${validation_dir}/cloudflare-check.log" || check_rc=$?
printf '%s\n' "${check_rc}" > "${validation_dir}/cloudflare-check.exit_code"

summary_path="$(python3 - "${repo_root}" "${check_start_epoch}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

repo = Path(sys.argv[1])
start_epoch = int(sys.argv[2])
base = repo / 'debug_artifacts' / 'docker-browser-parity' / 'cloudflare-check'
candidates = []
if base.exists():
    for path in base.glob('*/summary.json'):
        try:
            if int(path.stat().st_mtime) >= start_epoch - 2:
                candidates.append(path)
        except OSError:
            pass
if not candidates:
    print('')
else:
    candidates.sort(key=lambda p: p.stat().st_mtime)
    print(str(candidates[-1]))
PY
)"

if [[ -z "${summary_path}" || ! -f "${summary_path}" ]]; then
  echo "ERROR: no Cloudflare check summary.json found after validation run" >&2
  exit 2
fi
printf '%s\n' "${summary_path}" > "${validation_dir}/cloudflare-summary.path"
cp "${summary_path}" "${validation_dir}/cloudflare-summary.json"

log "== strict validation =="
python3 - "${validation_dir}" "${profile_dir}" "${summary_path}" "${check_rc}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

validation_dir = Path(sys.argv[1])
host_profile_dir = sys.argv[2]
summary_path = Path(sys.argv[3])
check_rc = int(sys.argv[4])
summary = json.loads(summary_path.read_text(encoding='utf-8'))
runtime = summary.get('runtime') or {}
initial = summary.get('initial_auth_readiness') or {}
last = summary.get('last_session_status') or {}
errors: list[str] = []

if check_rc != 0:
    errors.append(f'cloudflare check exit code is {check_rc}')
if summary.get('ok') is not True:
    errors.append('summary ok is not true')
if summary.get('status') != 'cloudflare_cleared_auth_ready':
    errors.append(f"summary status is {summary.get('status')!r}")
if summary.get('cloudflare_cleared') is not True:
    errors.append('cloudflare_cleared is not true')
if summary.get('auth_ready') is not True:
    errors.append('auth_ready is not true')
if summary.get('release_blocking') is not False:
    errors.append('release_blocking is not false')
if runtime.get('docker_browser_profile') != 'bonnetjes-cloudflare-parity':
    errors.append(f"docker_browser_profile is {runtime.get('docker_browser_profile')!r}")
if runtime.get('bonnetjes_cloudflare_parity_mode') is not True:
    errors.append('bonnetjes_cloudflare_parity_mode is not true')
if runtime.get('profile_dir') != '/app/profile':
    errors.append(f"runtime profile_dir is {runtime.get('profile_dir')!r}")
if runtime.get('service_under_xvfb') is not True:
    errors.append('service_under_xvfb is not true')
if runtime.get('headless') is not False:
    errors.append('headless is not false')
if runtime.get('use_patchright') is not True:
    errors.append('use_patchright is not true')
if runtime.get('disable_fedcm') is not True:
    errors.append('disable_fedcm is not true')
if runtime.get('filter_no_sandbox') is not False:
    errors.append('filter_no_sandbox is not false')
if runtime.get('project_source_mutation_allowed') is not False:
    errors.append('project_source_mutation_allowed is not false')
if last.get('status') != 'auth_preflight_ready':
    errors.append(f"last status is {last.get('status')!r}")
if last.get('logged_in') is not True:
    errors.append('last logged_in is not true')
if last.get('challenge_detected') is not False:
    errors.append('last challenge_detected is not false')
if last.get('composer_visible') is not True:
    errors.append('last composer_visible is not true')
if last.get('release_blocking') is not False:
    errors.append('last release_blocking is not false')
if initial.get('logged_in') is not True:
    errors.append('initial logged_in is not true')

validation = {
    'ok': not errors,
    'action': 'docker_bonnetjes_cloudflare_validation',
    'status': 'passed' if not errors else 'failed',
    'host_profile_dir': host_profile_dir,
    'cloudflare_summary_path': str(summary_path),
    'checks': {
        'cloudflare_cleared': summary.get('cloudflare_cleared'),
        'auth_ready': summary.get('auth_ready'),
        'logged_in': last.get('logged_in'),
        'challenge_detected': last.get('challenge_detected'),
        'composer_visible': last.get('composer_visible'),
        'project_source_mutation_allowed': runtime.get('project_source_mutation_allowed'),
    },
    'errors': errors,
}
(validation_dir / 'validation-summary.json').write_text(json.dumps(validation, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(validation, indent=2, sort_keys=True))
if errors:
    raise SystemExit(2)
PY

log "== validation passed =="
log "validation_summary=${validation_dir}/validation-summary.json"
