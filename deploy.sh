#!/bin/bash

# Deployment script for ML Inference Gateway
echo "🚀 Starting Deployment of ML Inference Gateway..."

# 1. Setup Environment Variables
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Update OpenSearch credentials in .env
sed -i.bak 's/OPENSEARCH_PASSWORD=.*/OPENSEARCH_PASSWORD=Adm!9Kq7Zx@42/' .env
sed -i.bak 's/OPENSEARCH_USER=.*/OPENSEARCH_USER=admin/' .env
rm .env.bak

echo "✅ Environment configured."

# 2. Build and Start Services
echo "📦 Building and starting Docker containers..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

echo "------------------------------------------------------------"
echo "✅ Deployment Successful!"
echo "📍 Gateway API: http://localhost:8000"
echo "📊 OpenSearch: http://localhost:9200 (Credentials: admin / Adm!9Kq7Zx@42)"
echo "🎨 Admin Panel: http://localhost:8000/admin"
echo "📈 Dashboards:  http://localhost:5601"
echo "------------------------------------------------------------"
echo "Use 'docker-compose logs -f' to view logs."
