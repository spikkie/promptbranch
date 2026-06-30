#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the Docker-mounted Promptbranch browser profile with a normal host Chrome session.
# This seeds ./.pb_profile_docker, which docker-compose mounts into the service container as /app/profile.
# Close Chrome cleanly after ChatGPT is fully loaded.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

profile_dir="${PROMPTBRANCH_DOCKER_HOST_PROFILE_DIR:-${repo_root}/.pb_profile_docker}"
url="${CHATGPT_PROJECT_URL:-https://chatgpt.com/}"
mkdir -p "${profile_dir}"

echo "== Promptbranch Docker browser profile bootstrap =="
echo "profile_dir=${profile_dir}"
echo "url=${url}"
echo "Close Chrome cleanly after ChatGPT is fully loaded."

exec google-chrome \
  --user-data-dir="${profile_dir}" \
  --profile-directory=Default \
  --ozone-platform=x11 \
  --disable-gpu \
  --disable-vulkan \
  --password-store=basic \
  --use-mock-keychain \
  --disable-sync \
  --no-first-run \
  --no-default-browser-check \
  "${url}"
