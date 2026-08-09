#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${repo_root}/scripts/promptbranch-docker-build-metadata.sh"
promptbranch_export_docker_build_metadata "${repo_root}"

export PROMPTBRANCH_DOCKER_UID="${PROMPTBRANCH_DOCKER_UID:-$(id -u)}"
export PROMPTBRANCH_DOCKER_GID="${PROMPTBRANCH_DOCKER_GID:-$(id -g)}"

release_version_plain_from_version_file() {
  local version_file="${1:-VERSION}"
  [[ -f "${version_file}" ]] || return 1
  local value
  value="$(tr -d '\r\n[:space:]' < "${version_file}")"
  value="${value#v}"
  [[ -n "${value}" ]] || return 1
  printf '%s\n' "${value}"
}

export PROMPTBRANCH_SERVICE_IMAGE_TAG="${PROMPTBRANCH_SERVICE_IMAGE_TAG:-$(release_version_plain_from_version_file VERSION)}"

if [[ "${PROMPTBRANCH_ALLOW_SERVICE_IMAGE_OVERRIDE:-0}" != "1" ]]; then
  export PROMPTBRANCH_SERVICE_IMAGE="promptbranch-service:${PROMPTBRANCH_SERVICE_IMAGE_TAG}"
fi

export CHATGPT_PASSWORD_SECRET_FILE="${CHATGPT_PASSWORD_SECRET_FILE:-${HOME}/.config/chatgpt/password.txt}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-chatgpt_claudecode_workflow}"
export PROMPTBRANCH_SERVICE_PORT="${PROMPTBRANCH_SERVICE_PORT:-8000}"
export CHATGPT_SERVICE_BASE_URL="${CHATGPT_SERVICE_BASE_URL:-http://localhost:${PROMPTBRANCH_SERVICE_PORT}}"
unset CHATGPT_PASSWORD_FILE

if [[ ! -f "${CHATGPT_PASSWORD_SECRET_FILE}" ]]; then
  echo "Password file not found: ${CHATGPT_PASSWORD_SECRET_FILE}" >&2
  echo "Set CHATGPT_PASSWORD_SECRET_FILE to the correct host path before starting the service." >&2
  exit 1
fi

exec docker compose -p "${COMPOSE_PROJECT_NAME}" -f docker-compose.chatgpt-service.yml up --build --force-recreate "$@"
