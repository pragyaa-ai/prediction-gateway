#!/bin/bash

# ML Inference Gateway - Quick Start Script

set -e

echo "🚀 ML Inference Gateway - Quick Start"
echo "======================================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION detected"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file - please edit if needed"
else
    echo "✅ .env file exists"
fi
echo ""

# Check OpenSearch
echo "🔍 Checking OpenSearch connectivity..."
if curl -s -u admin:Admin@123 http://localhost:9200 > /dev/null 2>&1; then
    echo "✅ OpenSearch is running"
else
    echo "⚠️  OpenSearch not detected on localhost:9200"
    echo ""
    echo "To start OpenSearch with Docker:"
    echo "  docker-compose up -d opensearch"
    echo ""
    echo "Or continue without OpenSearch (logging will be disabled)"
fi
echo ""

# Start gateway
echo "🚀 Starting ML Inference Gateway..."
echo "======================================"
echo ""
echo "Gateway will be available at:"
echo "  - API: http://localhost:8000"
echo "  - Admin UI: http://localhost:8000/admin"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python main.py
