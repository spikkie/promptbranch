#!/usr/bin/env bash
set -euo pipefail

# One-shot standard browser Cloudflare/auth validation workflow.
#
# This is intentionally KISS and operator-visible:
#   1. Optionally install a Promptbranch ZIP candidate.
#   2. Open the standard host Chrome profile for manual login if requested.
#   3. Run Docker Cloudflare parity check against the same bind-mounted profile.
#   4. Validate the final summary strictly.
#
# It never calls /v1/project-sources, /v1/login-check, or any Google/login
# automation path. Project Source mutation remains disabled.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

standard_profile_dir="${repo_root}/.pb_profile/browser/default"
install_artifact="${PROMPTBRANCH_VALIDATION_INSTALL_ARTIFACT:-}"
install_version="${PROMPTBRANCH_VALIDATION_INSTALL_VERSION:-}"
profile_dir="${PROMPTBRANCH_HOST_PROFILE_DIR:-${standard_profile_dir}}"
fresh_profile=0
skip_bootstrap=0
bootstrap_mode="${PROMPTBRANCH_BROWSER_BOOTSTRAP_MODE:-docker}"
target_url="${PROMPTBRANCH_BROWSER_VALIDATION_URL:-${CHATGPT_PROJECT_URL:-}}"
bootstrap_url="${PROMPTBRANCH_BROWSER_BOOTSTRAP_URL:-}"
max_wait_seconds="${PROMPTBRANCH_CLOUDFLARE_CHECK_MAX_WAIT_SECONDS:-300}"
poll_seconds="${PROMPTBRANCH_CLOUDFLARE_CHECK_POLL_SECONDS:-10}"
allow_project_page_ready="${PROMPTBRANCH_BROWSER_VALIDATION_ALLOW_PROJECT_PAGE_READY:-0}"

usage() {
  cat <<'HELP'
Usage: pb-browser-cloudflare-validation.sh [options]

One-shot standard browser Cloudflare validation phase:
  1. optional install of a candidate ZIP
  2. visible Docker Chrome login/bootstrap using .pb_profile/browser/default by default
  3. Docker standard-browser Cloudflare parity check against that profile
  4. strict validation of the resulting summary.json

Options:
  --install-artifact ZIP     Optional candidate ZIP to install first.
  --install-version VERSION  Version used with --install-artifact, for example v0.1.103.10.5.
  --profile-dir PATH         Browser profile directory. Default: ./.pb_profile/browser/default.
  --fresh-profile            Delete and recreate the selected profile before browser bootstrap.
  --reuse-profile            Reuse selected profile. This is the default.
  --skip-bootstrap           Do not open a browser; use an already logged-in profile.
  --docker-bootstrap         Open Chrome inside Docker on the host display. Default.
  --url URL                  URL for auth-readiness validation. Default: current state conversation/project URL.
  --bootstrap-url URL        URL for visible browser bootstrap. Default: https://chatgpt.com/.
  --host-bootstrap           Compatibility mode: open host Chrome directly.
  --max-wait-seconds N       Cloudflare check timeout. Default: 300.
  --poll-seconds N           Cloudflare check polling interval. Default: 10.
  --help                     Show this help.

Environment equivalents:
  PROMPTBRANCH_VALIDATION_INSTALL_ARTIFACT
  PROMPTBRANCH_VALIDATION_INSTALL_VERSION
  PROMPTBRANCH_HOST_PROFILE_DIR
  PROMPTBRANCH_CLOUDFLARE_CHECK_MAX_WAIT_SECONDS
  PROMPTBRANCH_CLOUDFLARE_CHECK_POLL_SECONDS
  PROMPTBRANCH_BROWSER_BOOTSTRAP_MODE=docker|host
  PROMPTBRANCH_BROWSER_VALIDATION_URL
  PROMPTBRANCH_BROWSER_BOOTSTRAP_URL

Success criteria:
  - docker profile mode is standard-browser
  - profile is bind-mounted as /app/profile
  - Cloudflare challenge is not detected
  - logged_in=true
  - composer_visible=true
  - release_blocking=false

  Release-control may set PROMPTBRANCH_BROWSER_VALIDATION_ALLOW_PROJECT_PAGE_READY=1
  for pre_source_add bootstrap only. In that mode, a logged-in /project page with
  Cloudflare clear may satisfy source-add preflight even when no chat composer is
  visible. Normal ask/live/conversation validation still requires a composer.
  - Project Source mutation remains disabled
HELP
}

resolve_state_url() {
  python3 - "${repo_root}/.pb_profile/.promptbranch_state.json" <<'PY_RESOLVE_URL'
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

path = Path(sys.argv[1])
if not path.exists():
    print('https://chatgpt.com/')
    raise SystemExit(0)
try:
    payload = json.loads(path.read_text(encoding='utf-8'))
except Exception:
    print('https://chatgpt.com/')
    raise SystemExit(0)
current = payload.get('current') if isinstance(payload.get('current'), dict) else {}
for key in ('conversation_url', 'current_conversation_url'):
    value = current.get(key) if isinstance(current, dict) else None
    if isinstance(value, str) and value.startswith('https://chatgpt.com/'):
        print(value)
        raise SystemExit(0)
for key in ('conversation_url', 'current_conversation_url'):
    value = payload.get(key)
    if isinstance(value, str) and value.startswith('https://chatgpt.com/'):
        print(value)
        raise SystemExit(0)
for key in ('project_home_url', 'current_project_home_url'):
    value = current.get(key) if isinstance(current, dict) else None
    if isinstance(value, str) and value.startswith('https://chatgpt.com/'):
        print(value)
        raise SystemExit(0)
for key in ('project_home_url', 'current_project_home_url'):
    value = payload.get(key)
    if isinstance(value, str) and value.startswith('https://chatgpt.com/'):
        print(value)
        raise SystemExit(0)
print('https://chatgpt.com/')
PY_RESOLVE_URL
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
    --fresh-profile|--fresh)
      fresh_profile=1
      shift
      ;;
    --reuse-profile|--reuse)
      fresh_profile=0
      shift
      ;;
    --skip-bootstrap)
      skip_bootstrap=1
      shift
      ;;
    --docker-bootstrap)
      bootstrap_mode="docker"
      shift
      ;;
    --url)
      target_url="${2:-}"
      shift 2
      ;;
    --bootstrap-url)
      bootstrap_url="${2:-}"
      shift 2
      ;;
    --host-bootstrap)
      bootstrap_mode="host"
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

if [[ -z "${target_url}" ]]; then
  target_url="$(resolve_state_url)"
fi
if [[ -z "${bootstrap_url}" ]]; then
  # Manual Docker/host bootstrap is only used to establish the browser trust/session state.
  # Keep this default stable and generic; project/conversation scope is validated later by
  # docker-browser-parity-cloudflare-check against target_url.  Direct project URLs can
  # still be tested explicitly with --bootstrap-url or PROMPTBRANCH_BROWSER_BOOTSTRAP_URL.
  bootstrap_url="https://chatgpt.com/"
fi

case "${max_wait_seconds}" in
  ''|*[!0-9]*) echo "ERROR: max wait must be an integer: ${max_wait_seconds}" >&2; exit 64 ;;
esac
case "${poll_seconds}" in
  ''|*[!0-9]*) echo "ERROR: poll seconds must be an integer: ${poll_seconds}" >&2; exit 64 ;;
esac

if [[ -z "${profile_dir}" ]]; then
  profile_dir="${standard_profile_dir}"
elif [[ "${profile_dir}" != /* ]]; then
  profile_dir="${repo_root}/${profile_dir}"
fi

run_ts="$(date -u +%Y%m%dT%H%M%SZ)"
validation_dir="debug_artifacts/docker-browser-parity/standard-validation/${run_ts}"
mkdir -p "${validation_dir}"

log() {
  printf '%s\n' "$*" | tee -a "${validation_dir}/validation.log"
}

log "== Promptbranch standard browser Cloudflare validation =="
log "validation_dir=${validation_dir}"
log "profile_dir=${profile_dir}"
log "max_wait_seconds=${max_wait_seconds}"
log "poll_seconds=${poll_seconds}"
log "skip_bootstrap=${skip_bootstrap}"
log "bootstrap_mode=${bootstrap_mode}"
log "target_url=${target_url}"
log "bootstrap_url=${bootstrap_url}"
log "fresh_profile=${fresh_profile}"
log "allow_project_page_ready=${allow_project_page_ready}"

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
  pb release install \
    --artifact "${install_artifact}" \
    --version "${install_version}" \
    --json \
    | tee "${validation_dir}/install.json"
fi

if [[ "${skip_bootstrap}" == "0" ]]; then
  bootstrap_args=(--profile-dir "${profile_dir}" --url "${bootstrap_url}")
  if [[ "${fresh_profile}" == "1" ]]; then
    bootstrap_args+=(--fresh)
  else
    bootstrap_args+=(--reuse)
  fi

  case "${bootstrap_mode}" in
    docker)
      log "== visible Docker Chrome login bootstrap =="
      ./scripts/pb-docker-browser-profile-bootstrap.sh "${bootstrap_args[@]}" \
        2>&1 | tee "${validation_dir}/bootstrap.log"
      ;;
    host)
      log "== visible host Chrome login bootstrap =="
      ./scripts/pb-browser-profile-bootstrap.sh "${bootstrap_args[@]}" \
        2>&1 | tee "${validation_dir}/bootstrap.log"
      ;;
    *)
      echo "ERROR: unsupported bootstrap mode: ${bootstrap_mode}. Use docker or host." >&2
      exit 64
      ;;
  esac
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

log "== Docker standard browser Cloudflare check =="
check_start_epoch="$(date +%s)"
check_rc=0
CHATGPT_PROJECT_URL="${target_url}" \
PROMPTBRANCH_DOCKER_BROWSER_PROFILE=standard-browser \
PROMPTBRANCH_HOST_PROFILE_DIR="${profile_dir}" \
PROMPTBRANCH_PROFILE_DIR=/app/profile \
PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS="${PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS:-${max_wait_seconds}}" \
./scripts/docker-browser-parity-cloudflare-check.sh \
  --max-wait-seconds "${max_wait_seconds}" \
  --poll-seconds "${poll_seconds}" \
  2>&1 | tee "${validation_dir}/cloudflare-check.log" || check_rc=$?
printf '%s\n' "${check_rc}" > "${validation_dir}/cloudflare-check.exit_code"

summary_path="$(python3 - "${repo_root}" "${check_start_epoch}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

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
python3 - "${validation_dir}" "${profile_dir}" "${summary_path}" "${check_rc}" "${allow_project_page_ready}" "${target_url}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

validation_dir = Path(sys.argv[1])
profile_dir = sys.argv[2]
summary_path = Path(sys.argv[3])
check_rc = int(sys.argv[4])
allow_project_page_ready = sys.argv[5].strip().lower() in {'1', 'true', 'yes'}
target_url = sys.argv[6]
payload = json.loads(summary_path.read_text(encoding='utf-8'))
runtime = payload.get('runtime') or {}
last = payload.get('last_session_status') or {}
errors: list[str] = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

require(check_rc == 0, f'cloudflare check exit code was {check_rc}')
require(payload.get('ok') is True, 'cloudflare summary ok is not true')
require(payload.get('cloudflare_cleared') is True, 'cloudflare_cleared is not true')
require(payload.get('auth_ready') is True, 'auth_ready is not true')
require(payload.get('release_blocking') is False, 'release_blocking is not false')
require(runtime.get('docker_browser_profile') == 'standard-browser', f"docker_browser_profile is {runtime.get('docker_browser_profile')!r}")
require(runtime.get('standard_browser_mode') is True, 'standard_browser_mode is not true')
require(runtime.get('docker_browser_parity_mode') is True, 'docker_browser_parity_mode is not true')
require(runtime.get('profile_dir') == '/app/profile', f"profile_dir is {runtime.get('profile_dir')!r}")
require(runtime.get('project_source_mutation_allowed') is False, 'project_source_mutation_allowed is not false')
require(last.get('challenge_detected') is False, 'challenge_detected is not false')
require(last.get('logged_in') is True, 'logged_in is not true')

parsed_target = urlparse(target_url)
target_is_project_page = parsed_target.path.rstrip('/').endswith('/project')
project_page_ready_accepted = (
    allow_project_page_ready
    and target_is_project_page
    and last.get('project_page_visible') is True
    and last.get('logged_in') is True
    and last.get('challenge_detected') is False
)
composer_ready = last.get('composer_visible') is True
if not composer_ready and not project_page_ready_accepted:
    errors.append('composer_visible is not true')
require(last.get('release_blocking') is False, 'last release_blocking is not false')
result = {
    'ok': not errors,
    'status': 'passed' if not errors else 'failed',
    'action': 'pb_browser_cloudflare_validation',
    'host_profile_dir': profile_dir,
    'cloudflare_summary_path': str(summary_path),
    'checks': {
        'cloudflare_cleared': payload.get('cloudflare_cleared'),
        'auth_ready': payload.get('auth_ready'),
        'logged_in': last.get('logged_in'),
        'challenge_detected': last.get('challenge_detected'),
        'composer_visible': last.get('composer_visible'),
        'project_page_visible': last.get('project_page_visible'),
        'allow_project_page_ready': allow_project_page_ready,
        'target_is_project_page': target_is_project_page,
        'project_page_ready_accepted': project_page_ready_accepted,
        'project_source_mutation_allowed': runtime.get('project_source_mutation_allowed'),
        'standard_browser_mode': runtime.get('standard_browser_mode'),
    },
    'errors': errors,
}
(validation_dir / 'validation-summary.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2, sort_keys=True))
if errors:
    raise SystemExit(2)
PY

log "== validation passed =="
log "validation_summary=${validation_dir}/validation-summary.json"
