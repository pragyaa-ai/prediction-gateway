# 🎛️ Admin UI Guide - Model Management

## ✨ NEW Feature: Start/Stop Models

You can now **enable/disable models** directly from the Admin UI without editing YAML files!

## 🎯 How to Use

### 1. Access Admin Dashboard
```
http://localhost:8000/admin
```

### 2. View Model Registry
You'll see all your models with:
- Model ID
- Provider (Azure ML, etc.)
- Version
- Endpoint URL
- Timeout
- **Status** (ENABLED/DISABLED)
- **Actions** (Start/Stop buttons) ⭐ NEW!

### 3. Stop a Model

**When to use:**
- ❌ Model endpoint is down for maintenance
- 🐛 Model has a bug and you need to temporarily disable it
- 💰 Cost control - pause unused models
- 🔧 Testing - isolate issues

**How to stop:**
1. Find the model in the registry table
2. Click the **"⏸ Stop"** button next to it
3. Confirm the action
4. ✅ Model is now disabled - prediction requests will return 400 error

**What happens:**
```bash
# Before (model enabled)
curl -X POST http://localhost:8000/v1/predict \
  -d '{"model_id": "credit_risk_v2", ...}'

# Response: 200 OK with prediction

# After (model stopped)
curl -X POST http://localhost:8000/v1/predict \
  -d '{"model_id": "credit_risk_v2", ...}'

# Response: 400 Bad Request
# {"detail": "Model 'credit_risk_v2' is disabled"}
```

### 4. Start a Model

**How to start:**
1. Find the disabled model (shows "DISABLED" badge)
2. Click the **"▶ Start"** button
3. Confirm the action
4. ✅ Model is now active and accepting requests

## 🎨 Visual Guide

### Model Registry Table

```
┌──────────────────┬──────────┬─────────┬──────────────────┬─────────┬──────────┬───────────┐
│ Model ID         │ Provider │ Version │ Endpoint         │ Timeout │ Status   │ Actions   │
├──────────────────┼──────────┼─────────┼──────────────────┼─────────┼──────────┼───────────┤
│ credit_risk_v2   │ azure_ml │ 2.0     │ http://52934... │ 3000ms  │ ENABLED  │ ⏸ Stop    │
│ fraud_detect_v1  │ azure_ml │ 1.1     │ https://fraud... │ 2000ms  │ DISABLED │ ▶ Start   │
└──────────────────┴──────────┴─────────┴──────────────────┴─────────┴──────────┴───────────┘
```

### Button States

**Enabled Model:**
- Badge: 🟢 **ENABLED** (green)
- Button: **⏸ Stop** (green button)
- Click → Disables model immediately

**Disabled Model:**
- Badge: 🔴 **DISABLED** (red)
- Button: **▶ Start** (gray button)
- Click → Enables model immediately

## 🔧 Use Cases

### 1. Emergency Model Shutdown
```
Scenario: Azure endpoint is returning errors
Action: Click "Stop" button in admin UI
Result: All requests fail fast with 400, no backend calls
```

### 2. A/B Testing
```
Scenario: Testing model v2 vs v3
Action: 
  1. Stop credit_risk_v2
  2. Enable credit_risk_v3
  3. Monitor results
  4. Switch back if needed
```

### 3. Cost Control
```
Scenario: Non-business hours, pause expensive models
Action: Stop all models at 6 PM
Result: No Azure ML calls = no cost
```

### 4. Maintenance Window
```
Scenario: Azure endpoint maintenance scheduled
Before: Stop model in admin UI
During: Maintenance happens
After: Start model again
```

## 🔄 State Persistence

**Important Notes:**

⚠️ **Memory-based** - Model state is toggled in memory
- ✅ Changes take effect immediately
- ⚠️ State is lost on gateway restart
- 💡 On restart, state reloads from `models.yaml`

**To make changes permanent:**
1. Toggle model in admin UI (temporary)
2. Edit `config/models.yaml` and set `enabled: false`
3. Click "Reload Config" button (optional)

## 📊 Monitoring Impact

### Before Stopping Model
```json
{
  "status": "healthy",
  "gateway": "ok",
  "opensearch": "ok",
  "models_loaded": 2  // All models
}
```

### After Stopping Model
```json
{
  "status": "healthy",
  "gateway": "ok", 
  "opensearch": "ok",
  "models_loaded": 2  // Still loaded, but disabled
}
```

**Check model status:**
```bash
curl http://localhost:8000/models
```

Response:
```json
{
  "count": 2,
  "models": {
    "credit_risk_v2": {
      "provider": "azure_ml",
      "version": "2.0",
      "enabled": false,  // ← Disabled!
      "timeout_ms": 3000
    },
    "fraud_detection_v1": {
      "provider": "azure_ml", 
      "version": "1.1",
      "enabled": true,
      "timeout_ms": 2000
    }
  }
}
```

## 🔐 API Access (Advanced)

You can also toggle models via API:

```bash
# Stop a model
curl -X POST http://localhost:8000/admin/toggle-model/credit_risk_v2

# Response
{
  "status": "success",
  "model_id": "credit_risk_v2",
  "enabled": false,
  "message": "Model 'credit_risk_v2' disabled"
}

# Toggle again to start
curl -X POST http://localhost:8000/admin/toggle-model/credit_risk_v2

# Response
{
  "status": "success",
  "model_id": "credit_risk_v2",
  "enabled": true,
  "message": "Model 'credit_risk_v2' enabled"
}
```

## 🚨 Error Handling

### Client tries to use disabled model

**Request:**
```bash
curl -X POST http://localhost:8000/v1/predict \
  -d '{
    "model_id": "credit_risk_v2",
    "inputs": {"age": 42, "income": 70000, "credit_score": 680},
    "client_id": "test"
  }'
```

**Response:**
```json
{
  "detail": "Model 'credit_risk_v2' is disabled"
}
```
**HTTP Status:** 400 Bad Request

### Try to toggle non-existent model

**Request:**
```bash
curl -X POST http://localhost:8000/admin/toggle-model/fake_model
```

**Response:**
```json
{
  "detail": "Model 'fake_model' not found"
}
```
**HTTP Status:** 404 Not Found

## ✅ Best Practices

1. **Graceful Degradation**
   - Stop models before maintenance windows
   - Notify clients before disabling models

2. **Testing**
   - Test in dev environment first
   - Use health endpoint to verify state

3. **Documentation**
   - Document why a model was disabled
   - Set calendar reminders to re-enable

4. **Monitoring**
   - Watch OpenSearch logs for 400 errors
   - Monitor client impact after disabling

5. **Permanent Changes**
   - Update `models.yaml` for permanent disable
   - Use admin toggle for temporary changes

## 📈 What Gets Logged

**When you stop a model:**
- ✅ Admin action is logged to stdout
- ✅ Future prediction attempts log 400 errors
- ❌ No prediction sent to Azure (cost savings!)

**OpenSearch logs will show:**
```json
{
  "status": "error",
  "error_message": "Model disabled",
  // ... other fields
}
```

## 🎯 Quick Reference

| Action | Where | Effect | Persistent? |
|--------|-------|--------|-------------|
| Stop model | Admin UI button | Immediate disable | No (memory only) |
| Start model | Admin UI button | Immediate enable | No (memory only) |
| Disable in YAML | Edit `models.yaml` | After restart | Yes |
| Reload config | Admin UI button | Reload from YAML | Yes |

## 🔄 Workflow Examples

### Temporary Disable (Quick Fix)
```
1. Admin UI → Click "Stop" on model
2. Issue is fixed on Azure side
3. Admin UI → Click "Start" on model
✅ No file edits needed!
```

### Permanent Disable
```
1. Edit config/models.yaml → Set enabled: false
2. Admin UI → Click "Reload Config"
✅ Persists across restarts
```

### Controlled Rollout
```
1. Add model_v3 to YAML (enabled: false)
2. Restart gateway (loads v3 as disabled)
3. Admin UI → Stop model_v2
4. Admin UI → Start model_v3
5. Monitor performance
6. If good: Update YAML, if bad: reverse toggles
```

---

**🎉 This feature gives you instant control over your models without editing files or restarting the gateway!**

For more help, visit the main Admin Dashboard: http://localhost:8000/admin
