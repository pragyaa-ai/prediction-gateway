#!/bin/bash

# Start OpenSearch in background
echo "Starting OpenSearch..."
su - opensearch -c "/usr/share/opensearch/bin/opensearch -d -p /tmp/opensearch.pid" &

# Wait for OpenSearch to be ready
echo "Waiting for OpenSearch to be ready..."
until curl -s http://localhost:9200/_cluster/health > /dev/null; do
  sleep 2
done

echo "OpenSearch is ready!"

# Start the ML Gateway
echo "Starting ML Gateway..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload