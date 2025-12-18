# AWS API Gateway Setup for No-Show Model

## Architecture

```
Client Request → Your Gateway (FastAPI) → AWS API Gateway → Lambda → SageMaker Endpoint
```

**Current Status**: Waiting for API Gateway details from Nilanchal

---

## ℹ️ Information Needed from Nilanchal

Please request the following information:

### 1. API Gateway URL
The HTTP endpoint URL for the no-show model prediction.

**Format example**:
```
https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/predict
https://abc123xyz.execute-api.us-east-1.amazonaws.com/v1/noshow
```

**Questions to ask**:
- What is the complete API Gateway URL for the no-show prediction endpoint?
- What is the stage name? (dev, staging, prod, etc.)
- What is the resource path? (/predict, /invoke, /noshow, etc.)

### 2. Authentication Method

**Questions to ask**:
- Does the API Gateway require authentication?
- If yes, is it:
  - API Key (x-api-key header)?
  - IAM authentication?
  - Custom authorizer?
  - Public (no auth)?

### 3. API Key (if required)

**Questions to ask**:
- What is the API key value?
- What header name should be used? (usually `x-api-key`)

### 4. Request Format

**Questions to ask**:
- What JSON format does the Lambda expect?
- Is it the same 21 features we already have?
- Example request body format?

**Current format we're using**:
```json
{
  "instances": [
    {
      "features": [
        "PROVIDER_NAME",
        "DEPARTMENT",
        "ALLOCATION_DATE_TIME",
        ... (21 features total)
      ]
    }
  ]
}
```

### 5. Response Format

**Questions to ask**:
- What does the Lambda return?
- Example response body?

**Expected format**:
```json
{
  "predictions": [
    {
      "predicted_label": "NO_SHOW",
      "score": 0.85
    }
  ]
}
```

---

## 📝 Configuration Steps

Once you receive the information from Nilanchal:

### Step 1: Update models.yaml

Edit `config/models.yaml` and update the `no_show_fakeeh_ksa` section:

```yaml
no_show_fakeeh_ksa:
  provider: azure_ml
  endpoint_url: https://YOUR_API_GATEWAY_URL  # Replace with actual URL
  auth_type: key  # or 'none' if no auth required
  api_key: YOUR_API_KEY  # Replace with actual key, or null if no auth
  timeout_ms: 5000
  version: "1.0"
  input_mapper: no_show_fakeeh
  output_mapper: no_show_fakeeh
  enabled: true  # Change to true after configuration
```

### Step 2: Test the Configuration

Run the test script:
```bash
venv/bin/python test_noshow_model.py
```

### Step 3: Verify via curl

Direct test to API Gateway:
```bash
curl -X POST https://YOUR_API_GATEWAY_URL \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "instances": [{
      "features": [
        "Dr. Ahmed Al-Rashid",
        "Cardiology",
        "2025-12-20 10:00:00",
        "Friday",
        "MR123456",
        ... (remaining features)
      ]
    }]
  }'
```

---

## 🔍 Example API Gateway URLs

Here are some common AWS API Gateway URL patterns:

1. **REST API**:
   ```
   https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/predict
   https://abc123xyz.execute-api.us-east-1.amazonaws.com/v1/sagemaker/invoke
   ```

2. **HTTP API**:
   ```
   https://abc123xyz.execute-api.us-east-1.amazonaws.com/predict
   https://abc123xyz.execute-api.us-east-1.amazonaws.com/invoke
   ```

3. **Custom Domain**:
   ```
   https://api.pragyaa.ai/ml/noshow/predict
   https://ml-api.fakeeh.com/predict
   ```

---

## 🎯 Quick Setup Checklist

- [ ] Get API Gateway URL from Nilanchal
- [ ] Get API Key (if required)
- [ ] Confirm request/response format
- [ ] Update `config/models.yaml` with:
  - `endpoint_url`
  - `api_key` (or set to null)
  - `auth_type` (key or none)
- [ ] Set `enabled: true`
- [ ] Restart gateway server
- [ ] Run test: `venv/bin/python test_noshow_model.py`
- [ ] Verify prediction works

---

## 💡 Benefits of API Gateway Architecture

✅ **No AWS Credentials Needed** - Gateway handles auth  
✅ **Simpler Setup** - Just HTTP calls like Azure ML  
✅ **Rate Limiting** - API Gateway can throttle requests  
✅ **Monitoring** - CloudWatch logs for the API  
✅ **Caching** - API Gateway can cache responses  
✅ **Security** - API keys, IAM, or custom auth  

---

## 📧 Email Template for Nilanchal

Hi Nilanchal,

For the KSA No-Show model deployment, we need the following information about the AWS API Gateway setup:

1. **API Gateway URL**: Complete endpoint URL for predictions
2. **Authentication**: API key or other auth method required
3. **API Key**: If applicable
4. **Request Format**: JSON structure the Lambda expects
5. **Response Format**: JSON structure the Lambda returns

Current endpoint info:
- SageMaker Endpoint: `canvas-FH-KSA-NO-Show-15-10-25`
- Region: `us-east-1`
- Features: 21 fields (PROVIDER_NAME, DEPARTMENT, etc.)

This will allow Krishna to configure the prediction gateway on the KSA VM.

Thanks!

---

## 🚀 After Setup

Once configured, the no-show model will work exactly like the LOS model:

```bash
# Via gateway
curl -X POST http://localhost:8000/predict/no_show_fakeeh_ksa \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "PROVIDER_NAME": "Dr. Ahmed",
      "DEPARTMENT": "Cardiology",
      ... (all 21 fields)
    }
  }'
```

The gateway will:
1. Receive your request
2. Transform it to API Gateway format
3. Call AWS API Gateway with API key
4. API Gateway invokes Lambda
5. Lambda calls SageMaker endpoint
6. Response flows back through the chain
7. Gateway returns standardized prediction
