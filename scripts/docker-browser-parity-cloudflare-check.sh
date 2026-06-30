#!/usr/bin/env bash
set -euo pipefail

# KISS Cloudflare settle-loop diagnostic for the Promptbranch Docker browser
# parity envelope and Bonnetjes exact Cloudflare parity envelope. It does not click login, does not start Google auth, does
# not mutate Project Sources, and does not copy /app/debug_artifacts wholesale.
# It keeps one Docker browser session alive and polls that same session until
# the challenge clears, the held session is lost, or the timeout expires.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

no_recreate="${PROMPTBRANCH_DOCKER_BROWSER_NO_RECREATE:-0}"
max_wait_seconds="${PROMPTBRANCH_CLOUDFLARE_CHECK_MAX_WAIT_SECONDS:-300}"
poll_seconds="${PROMPTBRANCH_CLOUDFLARE_CHECK_POLL_SECONDS:-10}"
export_evidence=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-recreate)
      no_recreate=1
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
    --no-export)
      export_evidence=0
      shift
      ;;
    --help|-h)
      cat <<'HELP'
Usage: docker-browser-parity-cloudflare-check.sh [--no-recreate] [--max-wait-seconds N] [--poll-seconds N] [--no-export]

Cloudflare challenge settle-loop diagnostic only. This script:
  - starts or reuses the Docker parity browser service
  - supports PROMPTBRANCH_DOCKER_BROWSER_PROFILE=docker-browser-parity
    and PROMPTBRANCH_DOCKER_BROWSER_PROFILE=bonnetjes-cloudflare-parity
  - requires docker_browser_parity_mode=true and profile_dir=/app/profile
  - opens one keep-open browser session through /v1/auth-readiness
  - polls /v1/auth-readiness/session/status for the same held session
  - exits success only when the Cloudflare challenge clears
  - exports bounded auth_readiness_auth_challenge_detected_* evidence through
    scripts/docker-browser-parity-export-challenge-artifacts.sh

It never calls /v1/project-sources, /v1/login-check, or any Google login flow.
HELP
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
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
if (( max_wait_seconds < 1 || max_wait_seconds > 3600 )); then
  echo "ERROR: max wait out of range: ${max_wait_seconds}" >&2
  exit 64
fi
if (( poll_seconds < 1 || poll_seconds > 300 )); then
  echo "ERROR: poll seconds out of range: ${poll_seconds}" >&2
  exit 64
fi

mkdir -p debug_artifacts/docker-browser-parity/cloudflare-check

ts="$(date -u +%Y%m%dT%H%M%SZ)"
out_dir="debug_artifacts/docker-browser-parity/cloudflare-check/${ts}"
mkdir -p "${out_dir}/polls"

export PROMPTBRANCH_DOCKER_BROWSER_PROFILE="${PROMPTBRANCH_DOCKER_BROWSER_PROFILE:-docker-browser-parity}"
export PROMPTBRANCH_PROFILE_DIR="${PROMPTBRANCH_PROFILE_DIR:-/app/profile}"
export CHATGPT_USE_PATCHRIGHT="${CHATGPT_USE_PATCHRIGHT:-1}"
export CHATGPT_BROWSER_CHANNEL="${CHATGPT_BROWSER_CHANNEL:-chrome}"
export CHATGPT_HEADLESS="${CHATGPT_HEADLESS:-0}"
export CHATGPT_DISABLE_FEDCM="${CHATGPT_DISABLE_FEDCM:-1}"
export CHATGPT_FILTER_NO_SANDBOX="${CHATGPT_FILTER_NO_SANDBOX:-0}"
export CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS="${CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS:-1}"
export CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS="${CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS:-20000}"
export PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS="${PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS:-300}"

if [[ "${PROMPTBRANCH_DOCKER_BROWSER_PROFILE}" == "bonnetjes-cloudflare-parity" ]]; then
  export CHATGPT_USE_PATCHRIGHT="1"
  export CHATGPT_BROWSER_CHANNEL="chrome"
  export CHATGPT_HEADLESS="0"
  export CHATGPT_DISABLE_FEDCM="1"
  export CHATGPT_FILTER_NO_SANDBOX="0"
  export CHATGPT_PATCHRIGHT_HEADED_SAFE_ARGS="0"
  export CHATGPT_BROWSER_EXTRA_ARGS=""
  export CHATGPT_CONVERSATION_HISTORY_REQUEST_SHIELD_MODE="disabled"
fi

{
  printf '== docker browser parity Cloudflare check ==\n'
  printf 'no_recreate=%s\n' "${no_recreate}"
  printf 'max_wait_seconds=%s\n' "${max_wait_seconds}"
  printf 'poll_seconds=%s\n' "${poll_seconds}"
  printf 'export_evidence=%s\n' "${export_evidence}"
  env | sort | grep -E '^(PROMPTBRANCH_DOCKER_BROWSER_PROFILE|PROMPTBRANCH_PROFILE_DIR|PROMPTBRANCH_HOST_PROFILE_DIR|PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS|CHATGPT_USE_PATCHRIGHT|CHATGPT_BROWSER_CHANNEL|CHATGPT_HEADLESS|CHATGPT_DISABLE_FEDCM|CHATGPT_FILTER_NO_SANDBOX|CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS|CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS|CHATGPT_PATCHRIGHT_HEADED_SAFE_ARGS|CHATGPT_BROWSER_EXTRA_ARGS|CHATGPT_CONVERSATION_HISTORY_REQUEST_SHIELD_MODE)='
} | tee "${out_dir}/run.log"

mkdir -p .pb_profile .pb_profile_docker debug_artifacts

if [[ "${no_recreate}" =~ ^(1|true|yes|on)$ ]]; then
  if curl -fsS http://localhost:8000/healthz > "${out_dir}/healthz.preexisting.json"; then
    echo 'Using existing healthy Docker service (--no-recreate).' | tee -a "${out_dir}/run.log"
  else
    echo 'ERROR: --no-recreate requested but existing service is not healthy' | tee -a "${out_dir}/run.log"
    exit 1
  fi
else
  docker compose -f docker-compose.chatgpt-service.yml up -d --build | tee -a "${out_dir}/run.log"
fi

for _ in $(seq 1 60); do
  if curl -fsS http://localhost:8000/healthz > "${out_dir}/healthz.json"; then
    break
  fi
  sleep 2
done

if [[ ! -s "${out_dir}/healthz.json" ]]; then
  echo 'ERROR: service healthz did not become ready' | tee -a "${out_dir}/run.log"
  docker compose -f docker-compose.chatgpt-service.yml logs --tail=240 chatgpt-service > "${out_dir}/docker-service.log" || true
  exit 1
fi

TOKEN="${CHATGPT_SERVICE_TOKEN:-}"
if [[ -z "${TOKEN}" && -f .env ]]; then
  TOKEN="$(grep '^CHATGPT_SERVICE_TOKEN=' .env | tail -1 | cut -d= -f2- || true)"
fi

auth_header=()
if [[ -n "${TOKEN}" ]]; then
  auth_header=(-H "Authorization: Bearer ${TOKEN}")
fi

dump_chrome_argv() {
  local label="$1"
  local dest="${out_dir}/chrome-argv-${label}.txt"
  local cid
  cid="$(docker ps --filter name=chatgpt_claudecode_workflow-chatgpt-service-1 -q | head -1)"
  if [[ -z "${cid}" ]]; then
    printf 'no running container\n' > "${dest}"
    return 0
  fi
  docker exec "${cid}" sh -lc '
    ps -eo pid,ppid,stat,args | grep -E "chrome|chromium" | grep -v grep || true
  ' > "${dest}" 2>&1 || true
}

runtime_http_code="$(curl -sS -o "${out_dir}/docker-browser-runtime.json" -w '%{http_code}' \
  "${auth_header[@]}" \
  http://localhost:8000/v1/docker/browser-runtime || true)"
printf '%s\n' "${runtime_http_code}" > "${out_dir}/docker-browser-runtime.http_code"

python3 - "${out_dir}/docker-browser-runtime.json" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
errors = []
if not payload.get('ok'):
    errors.append('runtime ok=false')
profile = payload.get('docker_browser_profile')
if payload.get('docker_browser_parity_mode') is not True:
    errors.append('docker_browser_parity_mode is not true')
if profile not in {'docker-browser-parity', 'bonnetjes-cloudflare-parity'}:
    errors.append(f'docker_browser_profile is {profile!r}')
if payload.get('profile_dir') != '/app/profile':
    errors.append(f"profile_dir is {payload.get('profile_dir')!r}, expected '/app/profile'")
if payload.get('service_under_xvfb') is not True:
    errors.append('service_under_xvfb is not true')
if payload.get('headless') is not False:
    errors.append('headless is not false')
if payload.get('use_patchright') is not True:
    errors.append('use_patchright is not true')
if profile == 'bonnetjes-cloudflare-parity':
    if payload.get('bonnetjes_cloudflare_parity_mode') is not True:
        errors.append('bonnetjes_cloudflare_parity_mode is not true')
    if payload.get('browser_extra_args') not in ([], None):
        errors.append(f"browser_extra_args is {payload.get('browser_extra_args')!r}, expected []")
    if str(payload.get('patchright_headed_safe_args')) != '0':
        errors.append(f"patchright_headed_safe_args is {payload.get('patchright_headed_safe_args')!r}, expected '0'")
if errors:
    print(json.dumps({'ok': False, 'status': 'runtime_parity_preflight_failed', 'errors': errors, 'runtime': payload}, indent=2, sort_keys=True))
    raise SystemExit(2)
print(json.dumps({'ok': True, 'status': 'runtime_parity_preflight_passed'}, indent=2, sort_keys=True))
PY

start_http_code="$(curl -sS -o "${out_dir}/auth-readiness-start.json" -w '%{http_code}' \
  -X POST http://localhost:8000/v1/auth-readiness \
  "${auth_header[@]}" \
  -H 'Content-Type: application/json' \
  -d '{"keep_open": true}' || true)"
printf '%s\n' "${start_http_code}" > "${out_dir}/auth-readiness-start.http_code"
dump_chrome_argv "after-start"

status="cloudflare_waiting"
exit_code=2
last_status_file="${out_dir}/auth-readiness-start.json"
start_epoch="$(date +%s)"
iteration=0

while true; do
  now_epoch="$(date +%s)"
  elapsed=$(( now_epoch - start_epoch ))
  if (( elapsed > max_wait_seconds )); then
    status="cloudflare_timeout"
    exit_code=2
    break
  fi

  poll_file="${out_dir}/polls/session-status-$(printf '%04d' "${iteration}").json"
  poll_http_code="$(curl -sS -o "${poll_file}" -w '%{http_code}' \
    "${auth_header[@]}" \
    http://localhost:8000/v1/auth-readiness/session/status || true)"
  printf '%s\n' "${poll_http_code}" > "${poll_file%.json}.http_code"
  last_status_file="${poll_file}"

  decision="$(python3 - "${poll_file}" "${elapsed}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
elapsed = int(sys.argv[2])
payload = json.loads(path.read_text(encoding='utf-8'))
challenge = bool(payload.get('challenge_detected'))
held_active = bool((payload.get('held_session') or {}).get('active'))
logged_in = bool(payload.get('logged_in'))
composer_visible = bool(payload.get('composer_visible'))
title = payload.get('title')
state = payload.get('status')
if state == 'no_held_auth_readiness_session' or not held_active:
    decision = 'held_session_lost'
elif not challenge:
    decision = 'cloudflare_cleared_auth_ready' if (logged_in or composer_visible) else 'cloudflare_cleared_not_auth_ready'
else:
    decision = 'cloudflare_waiting'
print(json.dumps({
    'decision': decision,
    'elapsed_seconds': elapsed,
    'state': state,
    'title': title,
    'challenge_detected': challenge,
    'held_session_active': held_active,
    'logged_in': logged_in,
    'composer_visible': composer_visible,
}, sort_keys=True))
PY
)"
  printf '%s\n' "${decision}" | tee -a "${out_dir}/poll-decisions.jsonl"
  decision_name="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["decision"])' "${decision}")"
  case "${decision_name}" in
    cloudflare_cleared_auth_ready|cloudflare_cleared_not_auth_ready)
      status="${decision_name}"
      exit_code=0
      break
      ;;
    held_session_lost)
      status="held_session_lost"
      exit_code=2
      break
      ;;
  esac

  iteration=$(( iteration + 1 ))
  sleep "${poll_seconds}"
done

evidence_export_json="${out_dir}/challenge-artifact-export.json"
if [[ "${export_evidence}" == "1" ]]; then
  export_dest="/tmp/promptbranch-docker-browser-parity-challenge-artifacts/${ts}"
  if PROMPTBRANCH_CHALLENGE_ARTIFACT_EXPORT_DEST="${export_dest}" \
      ./scripts/docker-browser-parity-export-challenge-artifacts.sh > "${evidence_export_json}"; then
    printf 'evidence_export_status=ok\n' | tee -a "${out_dir}/run.log"
  else
    printf 'evidence_export_status=failed\n' | tee -a "${out_dir}/run.log"
  fi
fi

dump_chrome_argv "final"
docker compose -f docker-compose.chatgpt-service.yml logs --tail=500 chatgpt-service > "${out_dir}/docker-service.log" || true

python3 - "${out_dir}" "${status}" "${last_status_file}" "${evidence_export_json}" "${max_wait_seconds}" "${poll_seconds}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
status = sys.argv[2]
last_status_path = Path(sys.argv[3])
export_path = Path(sys.argv[4])
max_wait_seconds = int(sys.argv[5])
poll_seconds = int(sys.argv[6])

def load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return {'ok': False, 'error': str(exc), 'path': str(path)}

runtime = load(out / 'docker-browser-runtime.json')
start = load(out / 'auth-readiness-start.json')
last = load(last_status_path)
export_payload = load(export_path)
cloudflare_cleared = status.startswith('cloudflare_cleared')
auth_ready = bool(last.get('logged_in') or last.get('composer_visible'))
summary = {
    'ok': cloudflare_cleared,
    'action': 'docker_browser_parity_cloudflare_check',
    'status': status,
    'cloudflare_cleared': cloudflare_cleared,
    'auth_ready': auth_ready,
    'release_blocking': not auth_ready,
    'output_dir': str(out),
    'max_wait_seconds': max_wait_seconds,
    'poll_seconds': poll_seconds,
    'runtime': runtime,
    'initial_auth_readiness': start,
    'last_session_status': last,
    'evidence_export': export_payload,
}
(out / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2, sort_keys=True))
PY

exit "${exit_code}"
