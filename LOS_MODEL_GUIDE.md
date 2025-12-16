# 🏥 LOS Fakeeh KSA Model - Integration Guide

## Overview

The **Length of Stay (LOS) Prediction Model** for Fakeeh Hospital KSA is now integrated and ready to use!

- **Model ID:** `los_fakeeh_ksa`
- **Endpoint:** http://52934d5b-4a57-4ac8-ab56-8667f4a7a8d4.eastus.azurecontainer.io/score
- **Status:** ✅ **ENABLED**
- **Purpose:** Predict hospital length of stay based on patient data

## 🔀 How Request Routing Works

### The Magic of model_id

When you send a prediction request, the gateway uses the **`model_id`** field to determine:
1. Which Azure endpoint to call
2. Which input mapper to apply
3. Which output mapper to use

```json
{
  "model_id": "los_fakeeh_ksa",  ← THIS determines routing!
  "client_id": "your_client_id",
  "inputs": { ... }
}
```

### Routing Flow

```
Request with model_id="los_fakeeh_ksa"
    ↓
Gateway reads config/models.yaml
    ↓
Finds los_fakeeh_ksa configuration:
  - endpoint_url: http://52934d5b-...
  - input_mapper: los_fakeeh
  - output_mapper: los_fakeeh
    ↓
Applies los_fakeeh_input() to transform data
    ↓
Sends to Azure ML endpoint
    ↓
Receives Azure response
    ↓
Applies los_fakeeh_output() to standardize
    ↓
Returns to client
```

## 📋 Required Input Fields (60+ fields)

The model expects a comprehensive patient record:

### Patient Demographics
- `MRNO` - Medical Record Number
- `AGE` - Patient age
- `AGE_GROUP` - Age category (e.g., "Adult")
- `AGE_GROUP_encoded` - Encoded age group
- `NATIONALITY` - Patient nationality
- `MARITAL_STATUS` - Marital status
- `BMI` - Body Mass Index

### Admission Details
- `ADMISSION_TYPE` - Type of admission (e.g., "Regular Admission")
- `ADMISSION_TYPE_encoded` - Encoded admission type
- `ADMISSION_LEVEL` - Level of admission (e.g., "Delivery Room")
- `ADMISSION_LEVEL_encoded` - Encoded level
- `ROOM_TYPE` - Type of room (e.g., "Ward")
- `ROOM_TYPE_encoded` - Encoded room type
- `SOURCE_OF_ADMN` - Source (e.g., "ER")
- `SOURCE_OF_ADMN_encoded` - Encoded source

### Medical Information
- `PRIMARY` - Primary diagnosis
- `PRIMARY_encoded` - Encoded primary diagnosis
- `SECONDARY` - Secondary diagnosis
- `SURGERY_NAME` - Surgery name (if applicable)
- `PAYER` - Insurance/payer information
- `PREVIOUS_IP` - Previous inpatient visits

### Lab Tests & Values
- `SODIUM`, `SODIUM_available`
- `GLUCOSE`
- `BLOOD_UREA_NITROGEN`, `BLOOD_UREA_NITROGEN_available`
- `C_REACTIVE_PROTEIN`, `C_REACTIVE_PROTEIN_available`
- `CREATININE`, `CREATININE_available`
- `WBC`
- `PLATELETS_COUNT`, `PLATELETS_COUNT_available`

### Test Types Performed
- `HEMATOGY_TESTS` - Hematology tests (e.g., "CBC")
- `CHEMISTRY_TESTS` - Chemistry tests performed
- `IMMUNOLOGY_TESTS` - Immunology tests
- `CULTURE_TESTS` - Culture tests
- `RADIOLOGY_TESTS` - Radiology studies

### Vital Signs
- `OXYGEN_SATURATION` - O2 saturation (%)
- `TEMPERATURE` - Body temperature (°C)
- `BPSYSTOLIC` - Systolic BP
- `BPDIASTOLIC` - Diastolic BP
- `PULSE` - Heart rate
- `RESPIRATION` - Respiratory rate

### Medications & Warnings
- `TOTAL_MEDICINE_ORDERED` - Number of medications
- `MEDICATION_TYPE` - Type of medication
- `CLINICAL_WARNING` - Clinical warnings

### Outcomes & History
- `EXPIRED`, `EXPIRED_encoded` - Patient expiration status
- `LOS_GROUP`, `LOS_GROUP_encoded` - Actual LOS group (for training)
- `IP_IN_PREVIOUS_30_DAYS`, `IP_IN_PREVIOUS_30_DAYS_encoded` - Recent admissions
- `HOSPITALIZATION_PREVIOUS_YEAR` - Previous year admissions
- `Column1` - Additional column

## 🚀 API Request Example

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

## 📤 Response Format

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

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | string | Unique UUID for this prediction |
| `model_id` | string | Always "los_fakeeh_ksa" |
| `prediction` | string | LOS category (SHORT/MEDIUM/LONG) |
| `score` | float | Confidence score (0-1) |
| `latency_ms` | int | Processing time in milliseconds |
| `los_category` | string | Same as prediction |
| `confidence` | float | Same as score |

## 🧪 Testing

### Option 1: Automated Test Script
```bash
python test_los_model.py
```

### Option 2: Shell Script
```bash
./test_gateway.sh
```

### Option 3: Admin Dashboard
1. Navigate to http://localhost:8000/admin
2. Login with: krishna@pragyaa.ai / changeme123
3. Go to "🧪 Model Testing" tab
4. Select "los_fakeeh_ksa" from dropdown
5. Paste sample JSON
6. Click "Run Test Prediction"

## 📊 Monitoring

### View Predictions in Dashboard
- **Overview Tab:** See recent LOS predictions
- **Analytics Tab:** View prediction volume charts
- **Activity Tab:** Audit trail of all predictions

### OpenSearch Queries
```bash
# Search LOS predictions
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

## 🔧 Configuration

### Location
`config/models.yaml`

### Current Settings
```yaml
los_fakeeh_ksa:
  provider: azure_ml
  endpoint_url: http://52934d5b-4a57-4ac8-ab56-8667f4a7a8d4.eastus.azurecontainer.io/score
  auth_type: none
  api_key: null
  timeout_ms: 5000
  version: "1.0"
  input_mapper: los_fakeeh
  output_mapper: los_fakeeh
  enabled: true
```

### Adjustable Parameters
- `timeout_ms`: Increase if Azure endpoint is slow (default: 5000ms)
- `enabled`: Set to `false` to disable without removing config
- `auth_type`: Change to `key` if endpoint requires authentication

## 🔄 Adding Another Model

To add a second model (e.g., radiology prediction):

1. **Add to models.yaml:**
```yaml
radiology_model:
  provider: azure_ml
  endpoint_url: http://your-endpoint.azurecontainer.io/score
  auth_type: none
  timeout_ms: 3000
  version: "1.0"
  input_mapper: radiology
  output_mapper: radiology
  enabled: true
```

2. **Create mappers in adapters/mappers.py:**
```python
def radiology_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    return {"data": [inputs]}

def radiology_output(response: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "prediction": response.get("prediction"),
        "score": response.get("score")
    }

INPUT_MAPPERS["radiology"] = radiology_input
OUTPUT_MAPPERS["radiology"] = radiology_output
```

3. **Reload config:**
```bash
# Via dashboard
http://localhost:8000/admin → Settings → Reload Config

# Or restart
python main.py
```

4. **Use the new model:**
```json
{
  "model_id": "radiology_model",  ← Changed!
  "client_id": "hospital_x",
  "inputs": { ... }
}
```

## ⚠️ Important Notes

1. **All fields are required** - The model expects all 60+ fields even if some are empty strings or 0
2. **Case sensitive** - Field names must match exactly (e.g., "NATIONALITY" not "nationality")
3. **Boolean encoding** - Some boolean fields have both boolean and encoded versions
4. **Timeout** - Default is 5 seconds; increase if needed for slow endpoints
5. **No authentication** - Current endpoint doesn't require auth (auth_type: none)

## 🐛 Troubleshooting

### "Model 'los_fakeeh_ksa' not found"
- Check spelling of model_id in request
- Verify models.yaml has los_fakeeh_ksa entry
- Restart gateway or reload config

### Timeout Errors
- Increase timeout_ms in models.yaml
- Check Azure endpoint health
- Verify network connectivity

### Invalid Response
- Check Azure endpoint is responding correctly
- Review output mapper in adapters/mappers.py
- Enable debug logging

### Missing Fields
- Ensure all 60+ fields are in request
- Use sample data as template
- Check for typos in field names

## 📞 Support

- **Test Script:** `python test_los_model.py`
- **Shell Test:** `./test_gateway.sh`
- **Dashboard:** http://localhost:8000/admin
- **Health Check:** http://localhost:8000/health
- **API Docs:** http://localhost:8000/docs

---

**Model Status:** 🟢 READY  
**Last Updated:** December 16, 2024  
**Integration:** ✅ Complete
