#!/usr/bin/env bash
set -euo pipefail

app_module="${CHATGPT_UVICORN_APP:-promptbranch_container_api:app}"
port="${PORT:-8000}"
reload_setting="${CHATGPT_UVICORN_RELOAD:-0}"
container_home="${HOME:-/tmp/promptbranch-home}"
container_cache="${XDG_CACHE_HOME:-/tmp/promptbranch-cache}"
container_config="${XDG_CONFIG_HOME:-/tmp/promptbranch-config}"
docker_browser_profile="${PROMPTBRANCH_DOCKER_BROWSER_PROFILE:-standard-browser}"
xvfb_screen="${PROMPTBRANCH_DOCKER_XVFB_SCREEN:-1920x1080x24}"

mkdir -p "${container_home}" "${container_cache}" "${container_config}" /app/.pb_profile /app/profile /app/debug_artifacts

if [[ -z "${PROMPTBRANCH_PROFILE_DIR:-}" ]]; then
  export PROMPTBRANCH_PROFILE_DIR="/app/profile"
fi

bonnetjes_cloudflare_parity=0
standard_browser_mode=0
if [[ "${docker_browser_profile}" == "bonnetjes-cloudflare-parity" ]]; then
  bonnetjes_cloudflare_parity=1
fi
if [[ "${docker_browser_profile}" == "standard-browser" ]]; then
  standard_browser_mode=1
fi

# Docker browser parity is a diagnostic launch envelope based on a working
# Docker browser service pattern: one service process under xvfb-run,
# Patchright + Chrome, FedCM disabled, default Docker no-sandbox behavior
# preserved, and an isolated /app/profile browser profile.
if [[ "${docker_browser_profile}" == "docker-browser-parity" || "${docker_browser_profile}" == "bonnetjes-cloudflare-parity" || "${docker_browser_profile}" == "standard-browser" ]]; then
  if [[ -z "${PROMPTBRANCH_PROFILE_DIR:-}" || "${PROMPTBRANCH_PROFILE_DIR}" == "/app/.pb_profile" ]]; then
    export PROMPTBRANCH_PROFILE_DIR="/app/profile"
  fi
  export CHATGPT_USE_PATCHRIGHT="${CHATGPT_USE_PATCHRIGHT:-1}"
  export CHATGPT_BROWSER_CHANNEL="${CHATGPT_BROWSER_CHANNEL:-chrome}"
  export CHATGPT_HEADLESS="${CHATGPT_HEADLESS:-0}"
  export CHATGPT_DISABLE_FEDCM="${CHATGPT_DISABLE_FEDCM:-0}"
  export CHATGPT_FILTER_NO_SANDBOX="${CHATGPT_FILTER_NO_SANDBOX:-0}"
  export CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS="${CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS:-1}"
  export CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS="${CHATGPT_CHALLENGE_WAIT_TIMEOUT_MS:-20000}"
fi

# Standard browser mode keeps the Cloudflare-safe launch envelope discovered
# during the Bonnetjes investigation while using a neutral product name and the
# shared .pb_profile/browser/default host profile. The compatibility Bonnetjes
# profile mode uses the same launch envelope.
if [[ "${bonnetjes_cloudflare_parity}" == "1" || "${standard_browser_mode}" == "1" ]]; then
  export PROMPTBRANCH_PROFILE_DIR="/app/profile"
  export CHATGPT_USE_PATCHRIGHT="1"
  export CHATGPT_BROWSER_CHANNEL="chrome"
  export CHATGPT_HEADLESS="0"
  export CHATGPT_DISABLE_FEDCM="${CHATGPT_DISABLE_FEDCM:-0}"
  export CHATGPT_FILTER_NO_SANDBOX="0"
  export CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS="${CHATGPT_CLEAR_PROFILE_SINGLETON_LOCKS:-1}"
  export CHATGPT_PATCHRIGHT_HEADED_SAFE_ARGS="0"
  export CHATGPT_BROWSER_EXTRA_ARGS=""
  export CHATGPT_CONVERSATION_HISTORY_REQUEST_SHIELD_MODE="disabled"
fi

export PROMPTBRANCH_DOCKER_SERVICE_DISPLAY_MODE="xvfb-run"
export PROMPTBRANCH_DOCKER_SERVICE_UNDER_XVFB="1"
export PROMPTBRANCH_DOCKER_XVFB_SCREEN="${xvfb_screen}"

cmd=(
  xvfb-run
  -a
  -s
  "-screen 0 ${xvfb_screen}"
  uvicorn
  "$app_module"
  --host
  0.0.0.0
  --port
  "$port"
)

shopt -s nocasematch
if [[ "$reload_setting" == "1" || "$reload_setting" == "true" || "$reload_setting" == "yes" || "$reload_setting" == "on" ]]; then
  cmd+=(
    --reload
    --reload-dir
    /app
    --reload-exclude
    '/app/.pb_profile/*'
    --reload-exclude
    '/app/debug_artifacts/*'
    --reload-exclude
    '/app/.pytest_cache/*'
  )
fi
shopt -u nocasematch

exec "${cmd[@]}"
