#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the standard Promptbranch browser profile with Chrome running inside
# the Promptbranch Docker image but displayed on the host X11 display.
#
# Purpose: Cloudflare/session trust can differ between host Chrome and Docker
# Chrome. This script lets the operator clear Cloudflare and log in using the
# same Docker browser fingerprint that later runs /v1/auth-readiness and pb ask.
#
# It does not call /v1/project-sources, /v1/login-check, or automate login.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

standard_profile_dir="${repo_root}/.pb_profile/browser/default"
profile_dir="${PROMPTBRANCH_HOST_PROFILE_DIR:-${standard_profile_dir}}"
fresh=0
url="${PROMPTBRANCH_BROWSER_BOOTSTRAP_URL:-${CHATGPT_PROJECT_URL:-}}"
image="${PROMPTBRANCH_SERVICE_IMAGE:-promptbranch-service:${PROMPTBRANCH_SERVICE_IMAGE_TAG:-local}}"
container_profile_dir="/app/profile"
container_name="promptbranch-docker-browser-bootstrap-$(date -u +%Y%m%dT%H%M%SZ)-$$"

usage() {
  cat <<'HELP'
Usage: pb-docker-browser-profile-bootstrap.sh [options]

Open a visible Docker-launched Chrome window using the standard Promptbranch
browser profile bind-mounted as /app/profile. Use this when a host-created
profile clears Cloudflare locally but Docker/Patchright still receives
"Just a moment...".

Options:
  --profile-dir PATH  Host browser profile directory. Default: ./.pb_profile/browser/default.
  --fresh             Delete/recreate selected profile before opening Docker Chrome.
  --reuse             Reuse selected profile. Default.
  --url URL           URL to open. Default: current state conversation/project URL, CHATGPT_PROJECT_URL, or https://chatgpt.com/.
  --image IMAGE       Docker image. Default: promptbranch-service:local.
  --help              Show this help.

Requirements:
  - Linux host with DISPLAY set for X11/Xwayland.
  - Docker image built from this repo.
  - Xauthority available, or host X server configured to allow this container user.

Manual steps in the Chrome window:
  1. Clear Cloudflare.
  2. Log in if needed.
  3. Confirm the ChatGPT composer is visible.
  4. Close Chrome completely.
HELP
}

resolve_state_url() {
  python3 - "${repo_root}/.pb_profile/.promptbranch_state.json" <<'PY_RESOLVE_URL'
from __future__ import annotations

import json
import sys
from pathlib import Path

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
    --profile-dir)
      profile_dir="${2:-}"
      shift 2
      ;;
    --fresh|--fresh-profile)
      fresh=1
      shift
      ;;
    --reuse|--reuse-profile)
      fresh=0
      shift
      ;;
    --url)
      url="${2:-}"
      shift 2
      ;;
    --image)
      image="${2:-}"
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

if [[ -z "${url}" ]]; then
  url="$(resolve_state_url)"
fi

if [[ -z "${profile_dir}" ]]; then
  profile_dir="${standard_profile_dir}"
elif [[ "${profile_dir}" != /* ]]; then
  profile_dir="${repo_root}/${profile_dir}"
fi

prepare_profile_dir_for_docker_chrome() {
  local dir="$1"
  local parent
  parent="$(dirname "${dir}")"
  mkdir -p -- "${parent}"

  if [[ -e "${dir}" && ! -d "${dir}" ]]; then
    echo "ERROR: browser profile path exists but is not a directory: ${dir}" >&2
    exit 66
  fi

  if [[ "${fresh}" == "1" ]]; then
    if ! rm -rf -- "${dir}"; then
      cat >&2 <<MSG
ERROR: cannot remove browser profile for --fresh: ${dir}
Repair ownership first, for example:
  sudo chown -R $(id -u):$(id -g) "${dir}"
MSG
      exit 21
    fi
  fi

  if [[ -d "${dir}" && ! -w "${dir}" ]]; then
    if rmdir -- "${dir}" 2>/dev/null; then
      echo "Repaired empty non-writable browser profile placeholder: ${dir}"
    else
      cat >&2 <<MSG
ERROR: browser profile directory is not writable: ${dir}
Docker Chrome must be able to write session/cookie state through the bind mount.
Repair ownership first, for example:
  sudo chown -R $(id -u):$(id -g) "${dir}"
MSG
      exit 21
    fi
  fi

  mkdir -p -- "${dir}"
  chmod 700 "${dir}" || true
  rm -f \
    "${dir}/SingletonLock" \
    "${dir}/SingletonCookie" \
    "${dir}/SingletonSocket" \
    2>/dev/null || true
}

require_x11() {
  if [[ -z "${DISPLAY:-}" ]]; then
    cat >&2 <<'MSG'
ERROR: DISPLAY is not set. Docker visual browser bootstrap requires a visible X11/Xwayland display.
Run from your desktop terminal, not a headless SSH session, or use the host bootstrap script instead.
MSG
    exit 69
  fi
  if [[ ! -d /tmp/.X11-unix ]]; then
    echo "ERROR: /tmp/.X11-unix is missing; cannot mount host X11 socket into Docker." >&2
    exit 69
  fi
}

prepare_profile_dir_for_docker_chrome "${profile_dir}"
require_x11
mkdir -p "${repo_root}/.pb_profile" "${repo_root}/debug_artifacts"

if ! docker image inspect "${image}" >/dev/null 2>&1; then
  echo "== build Promptbranch service image for Docker browser bootstrap =="
  PROMPTBRANCH_VERSION="$(cat VERSION 2>/dev/null || echo unknown)" \
    docker compose -f docker-compose.chatgpt-service.yml build chatgpt-service
fi

xauth_file="${XAUTHORITY:-${HOME:-}/.Xauthority}"
xauth_args=()
if [[ -n "${xauth_file}" && -f "${xauth_file}" ]]; then
  xauth_args=(-e XAUTHORITY=/tmp/.docker.xauth -v "${xauth_file}:/tmp/.docker.xauth:ro")
else
  echo "WARN: no XAUTHORITY file found; Docker Chrome may be refused by the X server." >&2
  echo "WARN: If it fails, allow local Docker X11 access temporarily, then rerun." >&2
fi

network_args=()
if docker network inspect chatgpt_claudecode_workflow_default >/dev/null 2>&1; then
  network_args=(--network chatgpt_claudecode_workflow_default)
fi

cat <<MSG
== Promptbranch Docker browser profile bootstrap ==
profile_dir=${profile_dir}
container_profile_dir=${container_profile_dir}
image=${image}
display=${DISPLAY}
url=${url}
fresh=${fresh}

A Docker-launched Chrome window will open on your host display.
In that window:
  1. Confirm Cloudflare clears.
  2. Log in manually if needed.
  3. Confirm the ChatGPT composer is visible.
  4. Close Chrome completely.

After Chrome closes, run:

PROMPTBRANCH_DOCKER_BROWSER_PROFILE=standard-browser \\
PROMPTBRANCH_HOST_PROFILE_DIR="${profile_dir}" \\
PROMPTBRANCH_PROFILE_DIR=/app/profile \\
PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS=300 \\
./scripts/docker-browser-parity-cloudflare-check.sh --max-wait-seconds 300 --poll-seconds 10
MSG

docker run --rm -it \
  --name "${container_name}" \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp/promptbranch-home \
  -e XDG_CACHE_HOME=/tmp/promptbranch-cache \
  -e XDG_CONFIG_HOME=/tmp/promptbranch-config \
  -e DISPLAY="${DISPLAY}" \
  "${xauth_args[@]}" \
  "${network_args[@]}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "${profile_dir}:${container_profile_dir}" \
  -v "${repo_root}/.pb_profile:/app/.pb_profile" \
  -v "${repo_root}/debug_artifacts:/app/debug_artifacts" \
  "${image}" \
  bash -lc '
    set -euo pipefail
    mkdir -p "$HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" /app/profile /app/debug_artifacts
    rm -f /app/profile/SingletonLock /app/profile/SingletonCookie /app/profile/SingletonSocket 2>/dev/null || true
    exec google-chrome \
      --user-data-dir=/app/profile \
      --profile-directory=Default \
      --ozone-platform=x11 \
      --disable-gpu \
      --disable-vulkan \
      --password-store=basic \
      --use-mock-keychain \
      --disable-sync \
      --no-first-run \
      --no-default-browser-check \
      --no-sandbox \
      --disable-setuid-sandbox \
      ${PROMPTBRANCH_DOCKER_BOOTSTRAP_EXTRA_ARGS:-} \
      "$0"
  ' "${url}"
