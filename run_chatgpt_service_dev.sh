#!/usr/bin/env bash
set -euo pipefail

export PROMPTBRANCH_DOCKER_UID="${PROMPTBRANCH_DOCKER_UID:-$(id -u)}"
export PROMPTBRANCH_DOCKER_GID="${PROMPTBRANCH_DOCKER_GID:-$(id -g)}"

export CHATGPT_PASSWORD_SECRET_FILE="${CHATGPT_PASSWORD_SECRET_FILE:-${HOME}/.config/chatgpt/password.txt}"
export COMPOSE_PROJECT_NAME="chatgpt_claudecode_workflow"
export PROMPTBRANCH_SERVICE_PORT="8000"
export CHATGPT_SERVICE_BASE_URL="http://localhost:8000"
export CHATGPT_UVICORN_RELOAD="${CHATGPT_UVICORN_RELOAD:-1}"
unset CHATGPT_PASSWORD_FILE

if [[ ! -f "${CHATGPT_PASSWORD_SECRET_FILE}" ]]; then
  echo "Password file not found: ${CHATGPT_PASSWORD_SECRET_FILE}" >&2
  echo "Set CHATGPT_PASSWORD_SECRET_FILE to the correct host path before starting the service." >&2
  exit 1
fi

exec docker compose -p chatgpt_claudecode_workflow -f docker-compose.chatgpt-service.yml up --build --watch "$@"
