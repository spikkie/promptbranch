#!/bin/bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-chatgpt-docker-service}"
IMAGE_TAG="${IMAGE_TAG:-0.0.48}"
FULL_IMAGE="${FULL_IMAGE:-${IMAGE_NAME}:${IMAGE_TAG}}"

echo "Building ${FULL_IMAGE}"
docker build -t "${FULL_IMAGE}" .
