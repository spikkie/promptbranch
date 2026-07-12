#!/bin/bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${repo_root}/scripts/promptbranch-docker-build-metadata.sh"
promptbranch_export_docker_build_metadata "${repo_root}"

IMAGE_NAME="${IMAGE_NAME:-promptbranch-service}"
IMAGE_TAG="${IMAGE_TAG:-$(sed -e 's/^v//' VERSION)}"
FULL_IMAGE="${FULL_IMAGE:-${IMAGE_NAME}:${IMAGE_TAG}}"

echo "Building ${FULL_IMAGE}"
docker build \
  --build-arg "PROMPTBRANCH_VERSION=${PROMPTBRANCH_VERSION}" \
  --build-arg "PROMPTBRANCH_ARTIFACT_SHA256=${PROMPTBRANCH_ARTIFACT_SHA256}" \
  --build-arg "PROMPTBRANCH_SOURCE_FINGERPRINT=${PROMPTBRANCH_SOURCE_FINGERPRINT}" \
  -t "${FULL_IMAGE}" .
