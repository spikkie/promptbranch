#!/usr/bin/env bash
set -euo pipefail

# Compatibility wrapper. The standard browser Cloudflare check uses
# PROMPTBRANCH_DOCKER_BROWSER_PROFILE=standard-browser and the shared profile:
#   .pb_profile/browser/default -> /app/profile

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --seeded-only|--clean-only)
      # Legacy selector. The standard flow has one reusable default profile.
      shift
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

export PROMPTBRANCH_DOCKER_BROWSER_PROFILE="${PROMPTBRANCH_DOCKER_BROWSER_PROFILE:-standard-browser}"
export PROMPTBRANCH_HOST_PROFILE_DIR="${PROMPTBRANCH_HOST_PROFILE_DIR:-${repo_root}/.pb_profile/browser/default}"
export PROMPTBRANCH_PROFILE_DIR="${PROMPTBRANCH_PROFILE_DIR:-/app/profile}"
export PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS="${PROMPTBRANCH_AUTH_READINESS_KEEP_OPEN_SECONDS:-300}"

exec "${repo_root}/scripts/docker-browser-parity-cloudflare-check.sh" "${args[@]}"
