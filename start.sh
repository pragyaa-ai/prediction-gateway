#!/bin/bash
# ML Inference Gateway - Local / Dev Quick Start
# Usage: bash start.sh

set -euo pipefail

echo "ML Inference Gateway - Quick Start"
echo "==================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed. Please install Python 3.9+."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python $PYTHON_VERSION detected"

# Virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
# shellcheck disable=SC1091
source venv/bin/activate

# Dependencies – show output so errors are visible
echo "Installing/updating dependencies..."
pip install --upgrade pip wheel
pip install -r requirements.txt
echo "Dependencies ready."
echo ""

# .env file
if [ ! -f ".env" ]; then
    echo "No .env file found – copying from .env.example..."
    cp .env.example .env
    echo "Created .env – edit it to set credentials before going to production."
else
    echo ".env file exists."
fi
echo ""

# OpenSearch connectivity (non-fatal)
OPENSEARCH_HOST="${OPENSEARCH_HOST:-localhost}"
OPENSEARCH_PORT="${OPENSEARCH_PORT:-9200}"
echo "Checking OpenSearch at $OPENSEARCH_HOST:$OPENSEARCH_PORT..."
if curl -sf "http://$OPENSEARCH_HOST:$OPENSEARCH_PORT" > /dev/null 2>&1; then
    echo "OpenSearch is reachable."
else
    echo "WARNING: OpenSearch not detected – request logging will be disabled."
    echo "         Start it with: docker-compose up -d opensearch"
fi
echo ""

echo "Starting ML Inference Gateway..."
echo "  API      : http://localhost:8000"
echo "  Docs     : http://localhost:8000/docs"
echo "  Admin UI : http://localhost:8000/admin"
echo "  Health   : http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop."
echo ""

exec python main.py
