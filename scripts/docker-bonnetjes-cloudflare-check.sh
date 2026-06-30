#!/usr/bin/env bash
set -euo pipefail

# Bonnetjes exact Cloudflare parity runner. It only runs the Cloudflare
# settle-loop in two profile states: the existing seeded Docker profile and a
# clean one-shot profile. It does not click login, start Google auth, mutate
# Project Sources, or copy /app/debug_artifacts wholesale.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

run_seeded=1
run_clean=1
pass_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seeded-only)
      run_seeded=1
      run_clean=0
      shift
      ;;
    --clean-only)
      run_seeded=0
      run_clean=1
      shift
      ;;
    --no-recreate|--max-wait-seconds|--poll-seconds|--no-export)
      pass_args+=("$1")
      if [[ "$1" == "--max-wait-seconds" || "$1" == "--poll-seconds" ]]; then
        pass_args+=("${2:-}")
        shift 2
      else
        shift
      fi
      ;;
    --help|-h)
      cat <<'HELP'
Usage: docker-bonnetjes-cloudflare-check.sh [--seeded-only|--clean-only] [cloudflare-check options]

Runs exact Bonnetjes Cloudflare parity only:
  - PROMPTBRANCH_DOCKER_BROWSER_PROFILE=bonnetjes-cloudflare-parity
  - /app/profile inside the container
  - Xvfb + headed Patchright Chrome
  - CHATGPT_DISABLE_FEDCM=1
  - CHATGPT_FILTER_NO_SANDBOX=0
  - CHATGPT_PATCHRIGHT_HEADED_SAFE_ARGS=0
  - CHATGPT_BROWSER_EXTRA_ARGS empty

By default it runs:
  1. seeded profile: host ./.pb_profile_docker -> /app/profile
  2. clean profile: host ./.pb_profile_bonnetjes_clean -> /app/profile

It never calls /v1/project-sources or /v1/login-check.

Clean logged-in workflow:
  1. Run scripts/docker-bonnetjes-clean-login-profile-bootstrap.sh
  2. Log in in the visible Chrome window and close Chrome.
  3. Run docker-browser-parity-cloudflare-check.sh with the printed PROMPTBRANCH_HOST_PROFILE_DIR.
HELP
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 64
      ;;
  esac
done

run_case() {
  local case_name="$1"
  local host_profile_dir="$2"
  shift 2

  mkdir -p "${host_profile_dir}"
  printf '== Bonnetjes Cloudflare parity case: %s ==\n' "${case_name}"
  printf 'host_profile_dir=%s\n' "${host_profile_dir}"

  PROMPTBRANCH_DOCKER_BROWSER_PROFILE=bonnetjes-cloudflare-parity \
  PROMPTBRANCH_HOST_PROFILE_DIR="${host_profile_dir}" \
  PROMPTBRANCH_PROFILE_DIR=/app/profile \
  CHATGPT_USE_PATCHRIGHT=1 \
  CHATGPT_BROWSER_CHANNEL=chrome \
  CHATGPT_HEADLESS=0 \
  CHATGPT_DISABLE_FEDCM=1 \
  CHATGPT_FILTER_NO_SANDBOX=0 \
  CHATGPT_PATCHRIGHT_HEADED_SAFE_ARGS=0 \
  CHATGPT_BROWSER_EXTRA_ARGS= \
  CHATGPT_CONVERSATION_HISTORY_REQUEST_SHIELD_MODE=disabled \
  ./scripts/docker-browser-parity-cloudflare-check.sh "$@"
}

status=0

if [[ "${run_seeded}" == "1" ]]; then
  if ! run_case seeded ./.pb_profile_docker "${pass_args[@]}"; then
    status=2
  fi
fi

if [[ "${run_clean}" == "1" ]]; then
  rm -rf ./.pb_profile_bonnetjes_clean
  mkdir -p ./.pb_profile_bonnetjes_clean
  # A clean profile must recreate the container so the compose volume points to
  # ./.pb_profile_bonnetjes_clean rather than the seeded profile.
  filtered_args=()
  for arg in "${pass_args[@]}"; do
    if [[ "${arg}" != "--no-recreate" ]]; then
      filtered_args+=("${arg}")
    fi
  done
  if ! run_case clean ./.pb_profile_bonnetjes_clean "${filtered_args[@]}"; then
    status=2
  fi
fi

exit "${status}"
