#!/bin/bash
#
# Build and push all robot-shop Docker images to DockerHub
# Usage: ./build-all-images.sh
#

set -e

# Configuration
DOCKER_REGISTRY="${1:-gihong96}"
VERSION="${2:-1.1}"

dmultibuild() {
  docker buildx build --platform linux/amd64 -t "$1" --push "$2"
}

echo "=========================================="
echo "Building all robot-shop Docker images"
echo "Registry: ${DOCKER_REGISTRY}"
echo "Version: ${VERSION}"
echo "=========================================="
echo ""

# Build all services
echo "Building Web (Nginx)..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-web:${VERSION} ./web

echo "Building Catalogue (Node.js)..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-catalogue:${VERSION} ./catalogue

echo "Building User (Node.js)..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-user:${VERSION} ./user

echo "Building Cart (Node.js)..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-cart:${VERSION} ./cart

echo "Building Shipping (Java)..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-shipping:${VERSION} ./shipping

echo "Building Payment (Python)..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-payment:${VERSION} ./payment

echo "Building Ratings (PHP)..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-ratings:${VERSION} ./ratings

echo "Building Dispatch (Go)..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-dispatch:${VERSION} ./dispatch

# Build databases
echo "Building MongoDB..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-mongodb:${VERSION} ./mongo

echo "Building MySQL..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-mysql:${VERSION} ./mysql

# Build supporting services
echo "Building Load Generator..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-load:${VERSION} ./load-gen

echo "Building Fluentd..."
dmultibuild ${DOCKER_REGISTRY}/robot-shop-fluentd:${VERSION} ./fluentd

echo ""
echo "=========================================="
echo "All images built and pushed successfully!"
echo "=========================================="
echo ""
echo "Images built:"
echo "  ${DOCKER_REGISTRY}/robot-shop-web:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-catalogue:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-user:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-cart:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-shipping:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-payment:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-ratings:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-dispatch:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-mongodb:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-mysql:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-load:${VERSION}"
echo "  ${DOCKER_REGISTRY}/robot-shop-fluentd:${VERSION}"
echo ""
echo "To use these images, update your Helm values.yaml:"
echo "  image:"
echo "    repo: ${DOCKER_REGISTRY}"
echo "    version: ${VERSION}"
