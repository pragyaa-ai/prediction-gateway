# Quick Reference - ML Inference Gateway

## 🚀 Quick Start Commands

```bash
# Start gateway (easy way)
./start.sh

# Or manually
python main.py

# With Docker Compose (includes OpenSearch)
docker-compose up -d
```

## 📡 API Endpoints

### Make a Prediction
```bash
curl -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "credit_risk_v2",
    "inputs": {
      "age": 42,
      "income": 70000,
      "credit_score": 680
    },
    "client_id": "bank_123"
  }'
```

### Health Check
```bash
curl http://localhost:8000/health
```

### List All Models
```bash
curl http://localhost:8000/models
```

### Reload Configuration
```bash
curl -X POST http://localhost:8000/admin/reload-config
```

### Stop/Start a Model (via API)
```bash
# Toggle model state
curl -X POST http://localhost:8000/admin/toggle-model/credit_risk_v2

# Or use the Admin UI buttons (recommended)
```

## 🎯 Access Points

- **API Endpoint**: http://localhost:8000/v1/predict
- **Admin Dashboard**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/docs
- **OpenSearch**: http://localhost:9200
- **OpenSearch Dashboards**: http://localhost:5601

## 🔧 Adding a New Model

1. Edit `config/models.yaml`:
```yaml
your_model_id:
  provider: azure_ml
  endpoint_url: https://your-endpoint.azurecontainer.io/score
  auth_type: key
  api_key: your-key-here
  timeout_ms: 3000
  version: "1.0"
  input_mapper: your_model_mapper
  output_mapper: your_model_mapper
  enabled: true
```

2. Add mappers to `adapters/mappers.py`:
```python
def your_model_mapper_input(inputs):
    return {"data": [[inputs["field1"], inputs["field2"]]]}

def your_model_mapper_output(response):
    return {
        "prediction": response["prediction"],
        "score": response.get("score")
    }

INPUT_MAPPERS["your_model_mapper"] = your_model_mapper_input
OUTPUT_MAPPERS["your_model_mapper"] = your_model_mapper_output
```

3. Reload config (or restart gateway)

## 🐛 Troubleshooting

### Gateway won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Check Python version (needs 3.9+)
python3 --version

# Verify dependencies
pip list
```

### OpenSearch not connecting
```bash
# Check if OpenSearch is running
curl http://localhost:9200

# Start with Docker
docker-compose up -d opensearch

# Check logs
docker logs opensearch
```

### Prediction fails
```bash
# Check model configuration
curl http://localhost:8000/models

# Test health
curl http://localhost:8000/health

# Check gateway logs
# (look at terminal output)
```

## 📊 Testing

```bash
# Run test suite
python test_gateway.py

# Manual test with cURL
curl -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "credit_risk_v2",
    "inputs": {"age": 42, "income": 70000, "credit_score": 680},
    "client_id": "test"
  }'
```

## 🔐 Environment Variables

Edit `.env` file:

```bash
# Gateway
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8000

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=Admin@123

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `main.py` | FastAPI application |
| `config/models.yaml` | Model registry |
| `adapters/mappers.py` | Input/output transformations |
| `.env` | Environment configuration |
| `docker-compose.yml` | Full stack deployment |

## 🎨 Example Requests

### Credit Risk
```json
{
  "model_id": "credit_risk_v2",
  "inputs": {
    "age": 42,
    "income": 70000,
    "credit_score": 680
  },
  "client_id": "bank_123"
}
```

### Fraud Detection (if configured)
```json
{
  "model_id": "fraud_detection_v1",
  "inputs": {
    "transaction_amount": 1500.00,
    "merchant_id": "MERCH_12345",
    "user_age": 35,
    "transaction_hour": 14
  },
  "client_id": "payment_gateway"
}
```

## 🚢 Deployment

### Development
```bash
python main.py
```

### Production with Docker
```bash
docker-compose up -d
```

### Production with Systemd
```ini
[Unit]
Description=ML Inference Gateway
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/ml-gateway
Environment="PATH=/opt/ml-gateway/venv/bin"
ExecStart=/opt/ml-gateway/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📈 Performance Tips

- Use connection pooling (already implemented)
- Set appropriate timeouts per model
- Monitor OpenSearch disk usage
- Use Docker for consistent deployments
- Enable caching for model registry (optional)

---

For full documentation, see README.md
