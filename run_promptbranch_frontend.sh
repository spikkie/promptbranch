#!/usr/bin/env bash
set -euo pipefail
HOST="${PROMPTBRANCH_UI_HOST:-127.0.0.1}"
PORT="${PROMPTBRANCH_UI_PORT:-8000}"
exec python -m uvicorn promptbranch_container_api:app --host "$HOST" --port "$PORT"
