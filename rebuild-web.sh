#!/bin/bash
#
# Rebuild and push only the web service with OpenTelemetry gRPC fix
# Usage: ./rebuild-web.sh [version]
#

set -e

DOCKER_REGISTRY="gihong96"
VERSION="${1:-2.1}"

echo "=========================================="
echo "Rebuilding Web Service"
echo "Registry: ${DOCKER_REGISTRY}"
echo "Version: ${VERSION}"
echo "=========================================="
echo ""

echo "Building and pushing web image..."
docker buildx build --platform linux/amd64 \
  -t ${DOCKER_REGISTRY}/robot-shop-web:${VERSION} \
  --push ./web

echo ""
echo "=========================================="
echo "Web image built and pushed successfully!"
echo "=========================================="
echo ""
echo "Image: ${DOCKER_REGISTRY}/robot-shop-web:${VERSION}"
echo ""
echo "Next steps:"
echo "  1. Restart the web deployment:"
echo "     kubectl rollout restart deployment/web -n robot-shop2"
echo ""
echo "  2. Wait for rollout to complete:"
echo "     kubectl rollout status deployment/web -n robot-shop2"
echo ""
echo "  3. Verify no gRPC errors:"
echo "     kubectl logs -n robot-shop2 deployment/web --tail=50 | grep -i otel"
echo ""
echo "  4. Run k6 tests, extract data, and analyze again"
echo ""
