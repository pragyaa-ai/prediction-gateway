# 📚 API Usage Guide - ML Inference Gateway

## 🔀 How Request Routing Works

The gateway uses **model_id** in the request to determine which model to route to. Here's how it works:

### Request Flow:
```
1. Client sends request with "model_id": "los_fakeeh_ksa"
2. Gateway looks up "los_fakeeh_ksa" in models.yaml
3. Finds endpoint_url, input_mapper, output_mapper
4. Applies input_mapper to transform your data
5. Sends to Azure ML endpoint
6. Receives response from Azure
7. Applies output_mapper to standardize response
8. Returns to client
```

## 🏥 Length of Stay (LOS) Model - Fakeeh KSA

### Model Configuration
```yaml
Model ID: los_fakeeh_ksa
Endpoint: http://52934d5b-4a57-4ac8-ab56-8667f4a7a8d4.eastus.azurecontainer.io/score
Type: Length of Stay Prediction
Version: 1.0
Enabled: ✅ Yes
```

### API Request Example

```bash
curl -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "los_fakeeh_ksa",
    "client_id": "fakeeh_hospital",
    "inputs": {
      "MARITAL_STATUS": "",
      "NATIONALITY": "BRITISH",
      "Column1": 0,
      "BMI": 35.841,
      "MRNO": 12345678,
      "AGE": 38,
      "AGE_GROUP": "Adult",
      "AGE_GROUP_encoded": 1,
      "ADMISSION_TYPE": "Regular Admission",
      "ADMISSION_TYPE_encoded": 2,
      "ADMISSION_LEVEL": "Delivery Room",
      "ADMISSION_LEVEL_encoded": 3,
      "ROOM_TYPE": "Ward",
      "ROOM_TYPE_encoded": 1,
      "SOURCE_OF_ADMN": "ER",
      "SOURCE_OF_ADMN_encoded": 1,
      "PRIMARY": "R10.3-Pain localised to other parts of lower abdomen",
      "PRIMARY_encoded": 5,
      "SECONDARY": "O34.2-Maternal care due to uterine scar from previous surgery",
      "SURGERY_NAME": "",
      "PAYER": "Saudi Enaya Cooperative Insurance/CLASS A+ - Suite Room",
      "PREVIOUS_IP": 0,
      "SODIUM": 0,
      "SODIUM_available": 1,
      "GLUCOSE": "",
      "BLOOD_UREA_NITROGEN": 0,
      "BLOOD_UREA_NITROGEN_available": 1,
      "C_REACTIVE_PROTEIN": 0,
      "C_REACTIVE_PROTEIN_available": 1,
      "CREATININE": 0,
      "CREATININE_available": 1,
      "WBC": "",
      "PLATELETS_COUNT": 206,
      "PLATELETS_COUNT_available": 1,
      "HEMATOGY_TESTS": "CBC",
      "CHEMISTRY_TESTS": "ORAL GLUCOSE TOLERANCE TEST (FASTING)  ;  ORAL GLUCOSE TOLERANCE TEST (FIRST HOUR)  ;  GLYCOSYLATED HEMOGLOBIN.(HBA1C)  ;  ORAL GLUCOSE TOLERANCE TEST (SECOND HOUR)",
      "IMMUNOLOGY_TESTS": "",
      "CULTURE_TESTS": "PRENATAL VAGINAL SWAB ( GROUP - B STREPTOCOCCUS -  CULTURE & SENSITIVITY )",
      "OXYGEN_SATURATION": 100,
      "TEMPERATURE": 36.9,
      "BPSYSTOLIC": 118,
      "BPDIASTOLIC": 79,
      "PULSE": 85,
      "RESPIRATION": 20,
      "RADIOLOGY_TESTS": "US- Obstetrical Targeted Obstetric Ultrasound  ;  US- Obstetrical Routine Scan",
      "TOTAL_MEDICINE_ORDERED": 0,
      "MEDICATION_TYPE": "",
      "CLINICAL_WARNING": "",
      "EXPIRED": false,
      "EXPIRED_encoded": 0,
      "LOS_GROUP": "LONG",
      "LOS_GROUP_encoded": 2,
      "IP_IN_PREVIOUS_30_DAYS": false,
      "IP_IN_PREVIOUS_30_DAYS_encoded": 0,
      "HOSPITALIZATION_PREVIOUS_YEAR": 0
    }
  }'
```

### Expected Response

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "model_id": "los_fakeeh_ksa",
  "prediction": "LONG",
  "score": 0.85,
  "latency_ms": 142,
  "los_category": "LONG",
  "confidence": 0.85
}
```

### Response Fields Explained

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | string | Unique identifier for this prediction |
| `model_id` | string | Model used (los_fakeeh_ksa) |
| `prediction` | string | Predicted LOS category (SHORT/MEDIUM/LONG) |
| `score` | float | Confidence score (0-1) |
| `latency_ms` | int | Processing time in milliseconds |
| `los_category` | string | Same as prediction (for clarity) |
| `confidence` | float | Same as score (for clarity) |

## 🔄 How to Add Another Model

### Step 1: Add to `config/models.yaml`

```yaml
new_model_name:
  provider: azure_ml
  endpoint_url: http://your-azure-endpoint.azurecontainer.io/score
  auth_type: none
  timeout_ms: 5000
  version: "1.0"
  input_mapper: new_model_mapper
  output_mapper: new_model_mapper
  enabled: true
```

### Step 2: Create mappers in `adapters/mappers.py`

```python
def new_model_mapper_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "data": [{
            "field1": inputs.get("field1"),
            "field2": inputs.get("field2"),
            # ... map all required fields
        }]
    }

def new_model_mapper_output(response: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "prediction": response.get("prediction"),
        "score": response.get("score")
    }

# Register in dictionaries
INPUT_MAPPERS["new_model_mapper"] = new_model_mapper_input
OUTPUT_MAPPERS["new_model_mapper"] = new_model_mapper_output
```

### Step 3: Reload Configuration

**Option 1: Via Admin Dashboard**
1. Login to http://localhost:8000/admin
2. Go to Settings tab
3. Click "Reload Config from YAML"

**Option 2: Via API**
```bash
# Get auth token first
TOKEN=$(curl -X POST http://localhost:8000/admin/login \
  -d "username=krishna@pragyaa.ai&password=changeme123" | jq -r '.access_token')

# Reload config
curl -X POST http://localhost:8000/admin/reload-config \
  -H "Authorization: Bearer $TOKEN"
```

**Option 3: Restart Server**
```bash
# Simply restart the gateway
python main.py
```

### Step 4: Test the New Model

```bash
curl -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "new_model_name",
    "client_id": "test_client",
    "inputs": {
      "field1": "value1",
      "field2": 123
    }
  }'
```

## 🔑 Available Models

### 1. LOS Fakeeh KSA (Length of Stay)
- **Model ID:** `los_fakeeh_ksa`
- **Status:** ✅ Enabled
- **Use Case:** Predict hospital length of stay for patients
- **Input:** Patient demographics, vitals, tests, admission details
- **Output:** LOS category (SHORT/MEDIUM/LONG) with confidence

### 2. Credit Risk v2
- **Model ID:** `credit_risk_v2`
- **Status:** ⚠️ Disabled (demo only)
- **Use Case:** Assess credit risk
- **Input:** Age, income, credit_score
- **Output:** Risk level (low_risk/high_risk) with score

### 3. Fraud Detection v1
- **Model ID:** `fraud_detection_v1`
- **Status:** ⚠️ Disabled (demo only)
- **Use Case:** Detect fraudulent transactions
- **Input:** Transaction details
- **Output:** Fraud likelihood

## 🎯 Testing via Admin Dashboard

1. **Navigate to Testing Tab**
   - URL: http://localhost:8000/admin
   - Tab: 🧪 Model Testing

2. **Select Model**
   - Choose "los_fakeeh_ksa" from dropdown

3. **Paste Sample Input**
   ```json
   {
     "NATIONALITY": "BRITISH",
     "BMI": 35.841,
     "AGE": 38,
     "ADMISSION_TYPE": "Regular Admission",
     ...
   }
   ```

4. **Click "Run Test Prediction"**
   - View results in real-time
   - See latency metrics
   - Check prediction confidence

## 📊 Monitor Predictions

### Via Admin Dashboard
- **Overview Tab:** See recent predictions in real-time
- **Analytics Tab:** View prediction volume charts
- **Activity Tab:** Audit trail of all predictions

### Via OpenSearch
```bash
# Search predictions for LOS model
curl http://localhost:9200/ml-predictions-v1-*/_search \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "match": {
        "model_id": "los_fakeeh_ksa"
      }
    }
  }'
```

## 🔐 Authentication

The `/v1/predict` endpoint is **public** (no auth required).

Admin endpoints require JWT authentication:

```bash
# 1. Login
curl -X POST http://localhost:8000/admin/login \
  -d "username=krishna@pragyaa.ai&password=changeme123"

# Response includes token
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {...}
}

# 2. Use token for admin API calls
curl http://localhost:8000/admin/analytics/timeline \
  -H "Authorization: Bearer eyJhbGc..."
```

## 🚨 Error Handling

### Model Not Found
```json
{
  "detail": "Model 'invalid_model' not found in registry"
}
```
**Solution:** Check model_id matches exactly what's in models.yaml

### Model Disabled
```json
{
  "detail": "Model 'los_fakeeh_ksa' is disabled"
}
```
**Solution:** Enable via admin dashboard or set `enabled: true` in YAML

### Timeout
```json
{
  "detail": "Gateway timeout: ..."
}
```
**Solution:** Increase `timeout_ms` in models.yaml or check Azure endpoint

### Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "model_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
**Solution:** Ensure all required fields are present

## 📞 Support

- **Health Check:** http://localhost:8000/health
- **List Models:** http://localhost:8000/models
- **API Docs:** http://localhost:8000/docs
- **Admin Dashboard:** http://localhost:8000/admin

---

**Last Updated:** 2024-12-16  
**Gateway Version:** 1.0.0
