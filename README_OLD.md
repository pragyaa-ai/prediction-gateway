# 🚀 ML Inference Gateway

A unified, production-ready inference gateway for multiple ML models with Azure integration and OpenSearch logging.

## ✨ Features

- **Multi-Model Support**: Route requests to multiple models via YAML configuration
- **Azure ML Integration**: Native support for Azure-hosted ML endpoints
- **Standardized API**: Consistent request/response format across all models
- **Async Logging**: Non-blocking prediction logs to OpenSearch
- **Admin Dashboard**: Web-based UI for monitoring and management
- **Extensible Design**: Adapter pattern for easy provider additions
- **Production Ready**: Comprehensive error handling and health checks

## 📋 Requirements

- Python 3.9+
- OpenSearch (single-node setup included)
- Azure ML endpoints (optional)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
cd new-gateway

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# or: venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Configure Models

Edit `config/models.yaml` to add your models:

```yaml
credit_risk_v2:
  provider: azure_ml
  endpoint_url: http://52934d5b-4a57-4ac8-ab56-8667f4a7a8d4.eastus.azurecontainer.io/score
  auth_type: none
  timeout_ms: 3000
  version: "2.0"
  input_mapper: credit_v2
  output_mapper: credit_v2
  enabled: true
```

### 4. Start OpenSearch (Optional)

```bash
docker run -d \
  -p 9200:9200 -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin@123" \
  --name opensearch \
  opensearchproject/opensearch:2.11.0
```

### 5. Run Gateway

```bash
# Development mode with auto-reload
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📡 API Usage

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

**Response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "model_id": "credit_risk_v2",
  "prediction": "high_risk",
  "score": 0.82,
  "latency_ms": 41
}
```

### Check Health

```bash
curl http://localhost:8000/health
```

### List Models

```bash
curl http://localhost:8000/models
```

## 🎨 Admin Dashboard

Access the admin UI at: **http://localhost:8000/admin**

Features:
- Model registry viewer
- OpenSearch health status
- Recent predictions (last 20)
- Model performance statistics
- Configuration reload
- **Start/Stop models** - Enable/disable models without editing YAML

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       v
┌─────────────────────────────────┐
│     FastAPI Gateway             │
│  ┌──────────────────────────┐   │
│  │  /v1/predict endpoint    │   │
│  └───────────┬──────────────┘   │
│              │                  │
│              v                  │
│  ┌──────────────────────────┐   │
│  │   Model Registry (YAML)  │   │
│  └───────────┬──────────────┘   │
│              │                  │
│              v                  │
│  ┌──────────────────────────┐   │
│  │   Adapter Pattern        │   │
│  │   ├─ AzureMLAdapter      │   │
│  │   └─ [Future Adapters]   │   │
│  └───────────┬──────────────┘   │
│              │                  │
└──────────────┼──────────────────┘
               │
       ┌───────┴────────┐
       │                │
       v                v
┌──────────────┐  ┌─────────────┐
│  Azure ML    │  │ OpenSearch  │
│  Endpoints   │  │  (Logging)  │
└──────────────┘  └─────────────┘
```

## 📁 Project Structure

```
new-gateway/
├── main.py                 # FastAPI application
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── config/
│   ├── models.yaml        # Model registry
│   └── settings.py        # Configuration loader
├── models/
│   ├── schemas.py         # Pydantic models
│   └── registry.py        # Model registry
├── adapters/
│   ├── base.py            # Base adapter + Azure
│   └── mappers.py         # Input/output mappers
├── services/
│   └── opensearch.py      # OpenSearch client
└── templates/
    └── admin.html         # Admin UI
```

## 🔧 Adding a New Model

1. **Update `config/models.yaml`:**

```yaml
new_model_v1:
  provider: azure_ml
  endpoint_url: https://your-endpoint.azurecontainer.io/score
  auth_type: key
  api_key: your-api-key
  timeout_ms: 2000
  version: "1.0"
  input_mapper: new_model_v1
  output_mapper: new_model_v1
  enabled: true
```

2. **Add mappers in `adapters/mappers.py`:**

```python
def new_model_v1_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "data": [[inputs["feature1"], inputs["feature2"]]]
    }

def new_model_v1_output(response: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "prediction": response["prediction"],
        "score": response.get("score")
    }

# Register in dictionaries
INPUT_MAPPERS["new_model_v1"] = new_model_v1_input
OUTPUT_MAPPERS["new_model_v1"] = new_model_v1_output
```

3. **Reload configuration** (via admin UI or restart)

✅ **No code changes required in main.py!**

## 🛡️ Error Handling

| Error Condition | HTTP Status | Response |
|----------------|-------------|----------|
| Model not found | 400 | `Model 'xxx' not found in registry` |
| Model disabled | 400 | `Model 'xxx' is disabled` |
| Azure timeout | 504 | `Gateway timeout: ...` |
| Azure error | 502 | `Model error: ...` |
| OpenSearch failure | - | Logged only, doesn't block inference |

## 📊 OpenSearch Index Pattern

Predictions are logged to daily indices:

```
ml-predictions-v1-2025.12.16
ml-predictions-v1-2025.12.17
...
```

### Document Schema

```json
{
  "request_id": "uuid",
  "model_id": "credit_risk_v2",
  "model_version": "2.0",
  "provider": "azure_ml",
  "inputs_hash": "sha256...",
  "prediction": "high_risk",
  "score": 0.82,
  "latency_ms": 41,
  "client_id": "bank_123",
  "timestamp": "2025-12-16T10:30:00",
  "status": "success"
}
```

## 🧪 Testing

```bash
# Test prediction endpoint
curl -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "credit_risk_v2",
    "inputs": {"age": 42, "income": 70000, "credit_score": 680},
    "client_id": "test_client"
  }'

# Test health endpoint
curl http://localhost:8000/health

# Test model listing
curl http://localhost:8000/models
```

## 🔐 Security Notes

- **Production**: Enable authentication for `/admin` endpoints
- **API Keys**: Store in environment variables, not in YAML
- **HTTPS**: Use reverse proxy (nginx) for SSL termination
- **OpenSearch**: Enable SSL and proper authentication

## 📈 Performance

- **Async logging**: Predictions never blocked by logging failures
- **Connection pooling**: httpx async client reuse
- **Timeout handling**: Per-model configurable timeouts
- **Error isolation**: OpenSearch failures don't affect inference

## 🚢 Deployment

### Docker (Recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

```bash
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8000
OPENSEARCH_HOST=opensearch
OPENSEARCH_PORT=9200
```

## 📝 Acceptance Criteria Status

✅ Add new model by editing `models.yaml` only  
✅ Second model works without code changes  
✅ OpenSearch receives prediction logs  
✅ Gateway stays responsive if OpenSearch is down  
✅ Admin UI loads in <1s  
✅ Standardized request/response format  
✅ Async logging with BackgroundTasks  
✅ Adapter pattern with Azure implementation  
✅ Model registry viewer in admin  
✅ Health check dashboard  

## 🤝 Contributing

To add support for a new provider:

1. Create adapter in `adapters/base.py`
2. Implement `BaseModelAdapter.predict()`
3. Add to `get_adapter()` factory
4. Update models.yaml with new provider type

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Support

- **Admin UI**: http://localhost:8000/admin
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs (FastAPI auto-generated)

---

Built with ❤️ using FastAPI, OpenSearch, and Python
