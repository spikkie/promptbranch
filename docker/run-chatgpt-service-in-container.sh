#!/usr/bin/env bash
set -euo pipefail

app_module="${CHATGPT_UVICORN_APP:-promptbranch_container_api:app}"
port="${PORT:-8000}"
reload_setting="${CHATGPT_UVICORN_RELOAD:-0}"

cmd=(
  xvfb-run
  -a
  -s
  "-screen 0 1920x1080x24"
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
