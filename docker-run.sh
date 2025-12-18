#!/bin/bash

# Build and run the ML Gateway with embedded OpenSearch

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check for docker-compose or docker compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo "❌ Docker Compose is not installed. Please install Docker Compose:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "Building Docker image..."
$DOCKER_COMPOSE_CMD build

echo "Starting services..."
$DOCKER_COMPOSE_CMD up -d

echo "Waiting for services to be ready..."
sleep 10

echo "Checking gateway health..."
curl -s http://localhost:8000/health | python3 -c "import sys, json; data=json.load(sys.stdin); print('Gateway:', data.get('gateway', 'unknown')); print('OpenSearch:', data.get('opensearch', 'unknown')); print('Models loaded:', data.get('models_loaded', 0))"

echo ""
echo "Services are running:"
echo "- Gateway API: http://localhost:8000"
echo "- OpenSearch: http://localhost:9200"
echo "- Admin panel: http://localhost:8000/admin"
echo ""
echo "To stop: $DOCKER_COMPOSE_CMD down"
echo "To view logs: $DOCKER_COMPOSE_CMD logs -f"