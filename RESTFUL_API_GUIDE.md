# 🔥 RESTful API - Quick Start Guide

## 🎯 NEW Simplified Endpoint Format

Instead of putting `model_id` in the request body, **put it in the URL**!

### Before (Old Way)
```bash
POST /v1/predict
{
  "model_id": "los_fakeeh_ksa",  ← Redundant!
  "client_id": "hospital",       ← Not needed for on-prem!
  "inputs": { ... }
}
```

### After (New RESTful Way) ✨
```bash
POST /predict/los_fakeeh_ksa  ← Model in URL!
{
  "inputs": { ... }  ← Just your data! That's it!
}
```

**Perfect for on-prem deployments!** No client_id, no model_id in body - just pure data.

## 🚀 Quick Examples

### LOS Prediction (Fakeeh KSA)
```bash
curl -X POST http://localhost:8000/predict/los_fakeeh_ksa \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "NATIONALITY": "BRITISH",
      "BMI": 35.841,
      "AGE": 38,
      "ADMISSION_TYPE": "Regular Admission",
      ... (all other fields)
    }
  }'
```

### Credit Risk Prediction
```bash
curl -X POST http://localhost:8000/predict/credit_risk_v2 \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "age": 42,
      "income": 70000,
      "credit_score": 680
    }
  }'
```

### Fraud Detection
```bash
curl -X POST http://localhost:8000/predict/fraud_detection_v1 \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "transaction_amount": 599.99,
      "merchant_id": "MERCH_12345"
    }
  }'
```

## 📋 Available Endpoints

### RESTful Inference (Recommended)
- `POST /predict/{model_id}`
- `POST /v1/predict/{model_id}`

### Legacy Inference (Still Supported)
- `POST /v1/predict` (with model_id in body)

### System Endpoints
- `GET /` - API overview
- `GET /health` - Health check
- `GET /models` - List all models
- `GET /docs` - Interactive API documentation

## 🎨 Request Format

### Minimal Request (client_id is optional)
```json
{
  "inputs": {
    "field1": "value1",
    "field2": 123
  }
}
```

### With Client ID
```json
{
  "client_id": "your_client_id",
  "inputs": {
    "field1": "value1",
    "field2": 123
  }
}
```

## 📤 Response Format

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "model_id": "los_fakeeh_ksa",
  "prediction": "LONG",
  "score": 0.85,
  "latency_ms": 142
}
```

## 🔑 Model-Specific Endpoints

| Model | Endpoint | Status |
|-------|----------|--------|
| LOS Fakeeh | `/predict/los_fakeeh_ksa` | ✅ Enabled |
| Credit Risk | `/predict/credit_risk_v2` | ⚠️ Demo |
| Fraud Detection | `/predict/fraud_detection_v1` | ⚠️ Demo |

## 🧪 Testing

### Python Test Script
```bash
python test_restful_api.py
```

### Curl Examples
```bash
# LOS Prediction
curl -X POST http://localhost:8000/predict/los_fakeeh_ksa \
  -H "Content-Type: application/json" \
  -d '{"inputs": {...}}'

# Get available models
curl http://localhost:8000/models
```

### Using httpie
```bash
http POST localhost:8000/predict/los_fakeeh_ksa \
  client_id=hospital \
  inputs:='{"AGE": 38, "BMI": 35.841, ...}'
```

## 📊 Interactive Documentation

Access Swagger UI for interactive testing:
```
http://localhost:8000/docs
```

Try out endpoints directly in your browser!

## 🌐 Python Client Example

```python
import requests

def predict_los(patient_data: dict, client_id: str = "hospital"):
    """Call LOS prediction API"""
    
    response = requests.post(
        "http://localhost:8000/predict/los_fakeeh_ksa",
        json={
            "client_id": client_id,
            "inputs": patient_data
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        return result['prediction'], result['score']
    else:
        raise Exception(f"API error: {response.text}")

# Usage
patient = {
    "NATIONALITY": "BRITISH",
    "BMI": 35.841,
    "AGE": 38,
    # ... all other fields
}

prediction, confidence = predict_los(patient)
print(f"LOS Prediction: {prediction} (confidence: {confidence})")
```

## 🔧 JavaScript/Node.js Example

```javascript
async function predictLOS(patientData, clientId = 'hospital') {
  const response = await fetch('http://localhost:8000/predict/los_fakeeh_ksa', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      client_id: clientId,
      inputs: patientData
    })
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  const result = await response.json();
  return {
    prediction: result.prediction,
    score: result.score,
    latency: result.latency_ms
  };
}

// Usage
const patient = {
  NATIONALITY: 'BRITISH',
  BMI: 35.841,
  AGE: 38,
  // ... all other fields
};

const result = await predictLOS(patient);
console.log(`Prediction: ${result.prediction}`);
```

## ⚡ Benefits of RESTful Style

### ✅ Cleaner API
- Model is part of the resource URL
- Request body only contains actual data
- More intuitive and semantic

### ✅ Better Routing
- Easy to add rate limiting per model
- Simple to set up model-specific logging
- Natural fit for API gateways

### ✅ URL-based Versioning
```bash
/predict/los_fakeeh_ksa/v1
/predict/los_fakeeh_ksa/v2
```

### ✅ Easier Documentation
```
GET  /models              → List all models
POST /predict/model_x     → Predict with model_x
POST /predict/model_y     → Predict with model_y
```

## 🔄 Migration Guide

### From Old Style
```python
# OLD
requests.post("/v1/predict", json={
    "model_id": "los_fakeeh_ksa",
    "inputs": data
})

# NEW
requests.post("/predict/los_fakeeh_ksa", json={
    "inputs": data
})
```

### Backward Compatibility
Both styles work! The old `/v1/predict` endpoint still accepts `model_id` in the body for backward compatibility.

## 🐛 Error Responses

### Model Not Found
```json
{
  "detail": "Model 'invalid_model' not found in registry"
}
```
**HTTP Status:** 400

### Model Disabled
```json
{
  "detail": "Model 'los_fakeeh_ksa' is disabled"
}
```
**HTTP Status:** 400

### Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "inputs"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
**HTTP Status:** 422

### Timeout
```json
{
  "detail": "Gateway timeout: ..."
}
```
**HTTP Status:** 504

## 📞 Support

- **Test Script:** `python test_restful_api.py`
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Dashboard:** http://localhost:8000/admin

---

**API Version:** 1.0.0  
**Style:** RESTful  
**Status:** ✅ Production Ready
