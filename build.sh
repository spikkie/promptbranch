#!/bin/bash

set -e

# CONFIG
REGISTRY="dockerregistry.spikkies-it.nl"
IMAGE_NAME="bonnetjes-app-backend"
# TAG="0.0.16"
TAG="latest"
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"

echo "🟩 Building Docker image: $FULL_IMAGE"
docker build -t $FULL_IMAGE .
# docker build --no-cache -t $FULL_IMAGE .

echo "🟩 Pushing Docker image to $REGISTRY"
docker push $FULL_IMAGE
