# OpenSearch Setup Guide

## Quick Start (Docker - Recommended)

### 1. Start OpenSearch with Docker Compose

```bash
docker-compose up -d opensearch
```

This will start:
- OpenSearch on port 9200
- OpenSearch Dashboards on port 5601 (optional UI)

### 2. Verify Installation

```bash
# Check OpenSearch is running
curl -X GET "http://localhost:9200" -u admin:Admin@123

# Check cluster health
curl -X GET "http://localhost:9200/_cluster/health?pretty" -u admin:Admin@123
```

### 3. Access OpenSearch Dashboards (Optional)

Open browser: http://localhost:5601

- Username: `admin`
- Password: `Admin@123`

## Manual Installation (Alternative)

### macOS

```bash
# Install via Homebrew
brew tap opensearch-project/opensearch
brew install opensearch

# Start service
brew services start opensearch
```

### Linux

```bash
# Download OpenSearch
wget https://artifacts.opensearch.org/releases/bundle/opensearch/2.11.0/opensearch-2.11.0-linux-x64.tar.gz

# Extract
tar -xzf opensearch-2.11.0-linux-x64.tar.gz
cd opensearch-2.11.0

# Set initial admin password
export OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin@123

# Start single-node cluster
./opensearch-tar-install.sh
```

### Windows

```powershell
# Download from https://opensearch.org/downloads.html
# Extract and run
.\opensearch-windows-install.bat
```

## Configuration for Gateway

Update `.env` file:

```bash
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=Admin@123
OPENSEARCH_USE_SSL=false
OPENSEARCH_VERIFY_CERTS=false
```

## Index Management

### View Indices

```bash
curl -X GET "http://localhost:9200/_cat/indices?v" -u admin:Admin@123
```

### View Index Mapping

```bash
curl -X GET "http://localhost:9200/ml-predictions-v1-*/_mapping?pretty" -u admin:Admin@123
```

### Search Predictions

```bash
curl -X GET "http://localhost:9200/ml-predictions-v1-*/_search?pretty" \
  -u admin:Admin@123 \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "match": {
        "model_id": "credit_risk_v2"
      }
    },
    "size": 10,
    "sort": [{"timestamp": {"order": "desc"}}]
  }'
```

### Delete Old Indices (Cleanup)

```bash
# Delete indices older than 30 days
curl -X DELETE "http://localhost:9200/ml-predictions-v1-2025.11.*" -u admin:Admin@123
```

## Index Lifecycle Management (Production)

Create an ISM policy to automatically delete old indices:

```bash
curl -X PUT "http://localhost:9200/_plugins/_ism/policies/ml-predictions-retention" \
  -u admin:Admin@123 \
  -H 'Content-Type: application/json' \
  -d '{
    "policy": {
      "description": "Delete ML prediction indices after 90 days",
      "default_state": "hot",
      "states": [
        {
          "name": "hot",
          "actions": [],
          "transitions": [
            {
              "state_name": "delete",
              "conditions": {
                "min_index_age": "90d"
              }
            }
          ]
        },
        {
          "name": "delete",
          "actions": [
            {
              "delete": {}
            }
          ],
          "transitions": []
        }
      ]
    }
  }'
```

## Performance Tuning

### For Development (Low Resource)

```yaml
# docker-compose.yml
environment:
  - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
```

### For Production (Recommended)

```yaml
environment:
  - "OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g"
  - "bootstrap.memory_lock=true"
```

## Security (Production)

### Enable SSL

1. Generate certificates:

```bash
docker run -v $(pwd)/certs:/tmp opensearchproject/opensearch:2.11.0 \
  /bin/bash -c "cd /usr/share/opensearch && \
  ./plugins/opensearch-security/tools/install_demo_configuration.sh -y"
```

2. Update `.env`:

```bash
OPENSEARCH_USE_SSL=true
OPENSEARCH_VERIFY_CERTS=true
```

### Change Default Password

```bash
curl -X PUT "http://localhost:9200/_plugins/_security/api/internalusers/admin" \
  -u admin:Admin@123 \
  -H 'Content-Type: application/json' \
  -d '{
    "password": "YourNewSecurePassword@2025"
  }'
```

## Monitoring

### Check Disk Usage

```bash
curl -X GET "http://localhost:9200/_cat/allocation?v" -u admin:Admin@123
```

### Check Index Stats

```bash
curl -X GET "http://localhost:9200/ml-predictions-v1-*/_stats?pretty" -u admin:Admin@123
```

### Check Cluster Stats

```bash
curl -X GET "http://localhost:9200/_cluster/stats?pretty" -u admin:Admin@123
```

## Troubleshooting

### OpenSearch won't start

```bash
# Check logs
docker logs opensearch

# Increase vm.max_map_count (Linux/macOS)
sudo sysctl -w vm.max_map_count=262144
```

### Connection refused

```bash
# Verify port is open
netstat -an | grep 9200

# Check firewall
sudo ufw allow 9200
```

### Out of memory

```bash
# Reduce heap size
export OPENSEARCH_JAVA_OPTS="-Xms256m -Xmx256m"
```

## Backup & Restore

### Create Snapshot Repository

```bash
curl -X PUT "http://localhost:9200/_snapshot/ml_predictions_backup" \
  -u admin:Admin@123 \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "fs",
    "settings": {
      "location": "/mnt/backups/opensearch"
    }
  }'
```

### Take Snapshot

```bash
curl -X PUT "http://localhost:9200/_snapshot/ml_predictions_backup/snapshot_1" \
  -u admin:Admin@123
```

## Resources

- [OpenSearch Documentation](https://opensearch.org/docs/latest/)
- [Docker Hub - OpenSearch](https://hub.docker.com/r/opensearchproject/opensearch)
- [OpenSearch Dashboards](https://opensearch.org/docs/latest/dashboards/index/)

---

For gateway-specific OpenSearch integration, see the main README.md
