#!/bin/bash
# Docker-based deployment script for ML Inference Gateway.
# Run from the repository root on any machine with Docker + Docker Compose.

set -euo pipefail

echo "ML Inference Gateway - Docker Deploy"
echo "======================================"

# 1. Environment file
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Edit .env to set credentials, then re-run this script."
fi

# 2. Build and start
echo "Building Docker image..."
docker-compose build --no-cache

echo "Starting services..."
docker-compose up -d

echo ""
echo "Waiting for gateway to become healthy (up to 120s)..."
for i in $(seq 1 24); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo ""
        echo "======================================"
        echo " Deployment successful!"
        echo "======================================"
        echo " Gateway API  : http://localhost:8000"
        echo " Health check : http://localhost:8000/health"
        echo " API docs     : http://localhost:8000/docs"
        echo " Admin Panel  : http://localhost:8000/admin"
        echo " OpenSearch   : http://localhost:9200"
        echo " Dashboards   : http://localhost:5601"
        echo "======================================"
        echo ""
        echo "View logs: docker-compose logs -f gateway"
        exit 0
    fi
    echo "  ($((i * 5))s) not ready yet..."
    sleep 5
done

echo "WARNING: Gateway did not become healthy within 120s."
echo "Check logs: docker-compose logs --tail=50 gateway"
exit 1
