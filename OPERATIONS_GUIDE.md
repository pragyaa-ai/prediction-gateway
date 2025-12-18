# 🚀 ML Inference Gateway - Operations Guide

**Version:** 1.0.0  
**Last Updated:** December 18, 2025  
**For:** New Operators & DevOps Team

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Initial Setup](#initial-setup)
4. [Starting the Gateway](#starting-the-gateway)
5. [Accessing the Admin Dashboard](#accessing-the-admin-dashboard)
6. [Running Predictions](#running-predictions)
7. [Monitoring & Health Checks](#monitoring--health-checks)
8. [Stopping the Gateway](#stopping-the-gateway)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Common Tasks](#common-tasks)
11. [Emergency Procedures](#emergency-procedures)

---

## 🎯 Overview

### What is This?
The ML Inference Gateway is a production-ready API service that:
- Routes prediction requests to different ML models hosted on Azure
- Provides a unified API interface for all models
- Logs all predictions to OpenSearch for analytics
- Offers a web-based admin dashboard for monitoring

### Current Models
1. **LOS Fakeeh KSA** (`los_fakeeh_ksa`) - Hospital Length of Stay prediction - **ENABLED ✅**
2. **Credit Risk V2** (`credit_risk_v2`) - Credit risk assessment - **DISABLED ❌**
3. **Fraud Detection V1** (`fraud_detection_v1`) - Transaction fraud detection - **DISABLED ❌**

### Key URLs
- **API Endpoint:** `http://localhost:8000`
- **Admin Dashboard:** `http://localhost:8000/admin`
- **Health Check:** `http://localhost:8000/health`
- **OpenSearch Dashboards:** `http://localhost:5601` (if running)

---

## ⚙️ Prerequisites

### Required Software
- **Python 3.9+** (check: `python3 --version`)
- **Git** (for updates)
- **Docker & Docker Compose** (optional, for OpenSearch)

### System Requirements
- **RAM:** 2GB minimum, 4GB recommended
- **Disk:** 1GB free space
- **Network:** Internet access to reach Azure ML endpoints

### Access Requirements
- SSH access to the VM
- Sudo privileges (for port binding if needed)
- Network access to Azure ML endpoints

---

## 🔧 Initial Setup

### Step 1: Navigate to Project Directory
```bash
cd /Users/krishnabajpai/code/pragyaa-ai/gateway/prediction-gateway
```

### Step 2: Verify Files
Check that all required files exist:
```bash
ls -la
```

You should see:
- `main.py` - Main application file
- `requirements.txt` - Python dependencies
- `config/models.yaml` - Model configurations
- `start.sh` - Quick start script
- `docker-compose.yml` - Docker configuration

### Step 3: Check Python Installation
```bash
python3 --version
```
Should show: `Python 3.9.x` or higher

### Step 4: Create Virtual Environment (First Time Only)
```bash
python3 -m venv venv
```

### Step 5: Install Dependencies
```bash
# Activate virtual environment
source venv/bin/activate

# Install packages
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected output:** Should install ~15 packages without errors

### Step 6: Configure Environment (First Time Only)
```bash
# Check if .env exists
ls -la .env

# If not, copy from example
cp .env.example .env

# Edit if needed (optional for basic operation)
nano .env
```

**Default .env settings work for local deployment without OpenSearch.**

---

## ▶️ Starting the Gateway

### Method 1: Using the Start Script (Recommended)
```bash
./start.sh
```

This script will:
1. ✅ Check Python version
2. ✅ Create virtual environment (if needed)
3. ✅ Install dependencies
4. ✅ Start the gateway server

### Method 2: Manual Start
```bash
# Activate virtual environment
source venv/bin/activate

# Start the server
python main.py
```

### What You Should See
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Verify It's Running
Open a new terminal and run:
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "gateway": "ok",
  "opensearch": "unavailable",
  "models_loaded": 3
}
```

✅ **Status "healthy" or "degraded" is OK** (degraded just means OpenSearch is not running, predictions still work)

---

## 🖥️ Accessing the Admin Dashboard

### Step 1: Open Browser
Navigate to: **http://localhost:8000/admin**

### Step 2: Login
Use one of these accounts:

| Name | Email | Password |
|------|-------|----------|
| Gulshan Mehta | `gulshan@pragyaa.ai` | `changeme123` |
| Manoj Gulati | `manoj@pragyaa.ai` | `changeme123` |
| Krishna Bajpai | `krishna@pragyaa.ai` | `changeme123` |

### Step 3: Explore Dashboard Tabs

1. **📊 Overview** - System status, model registry, recent predictions
2. **📈 Analytics** - Charts, graphs, export data
3. **🧪 Testing** - Test models directly from UI
4. **📦 Batch** - Upload CSV for bulk predictions
5. **🔑 API Keys** - Generate/manage API keys
6. **📋 Activity** - View admin action logs
7. **⚙️ Settings** - Configure email/SMTP

### Dashboard Features
- **Auto-refresh:** Every 60 seconds
- **Dark Mode:** Toggle in top-right corner
- **Model Control:** Enable/disable models with toggle switches

---

## 🎯 Running Predictions

### Method 1: Using Test Script (Recommended for Testing)
```bash
# From project directory
python test_los_model.py
```

**Expected output:**
```
🏥 Testing LOS Fakeeh KSA Model
================================================================================
📍 Gateway URL: http://localhost:8000/v1/predict
🔬 Model ID: los_fakeeh_ksa
...
✅ SUCCESS! Prediction completed
🎯 Prediction: LONG
📊 Score: 0.85
⏱️  Latency: 142ms
```

### Method 2: Using curl (RESTful API)
```bash
curl -X POST http://localhost:8000/predict/los_fakeeh_ksa \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "AGE": 38,
      "BMI": 35.841,
      "NATIONALITY": "BRITISH",
      "ADMISSION_TYPE": "Regular Admission",
      "ROOM_TYPE": "Ward"
    }
  }'
```

### Method 3: Using Admin Dashboard
1. Go to **🧪 Testing** tab
2. Select model: `los_fakeeh_ksa`
3. Enter JSON input or use sample
4. Click **Test Model**
5. View results below

### API Response Format
```json
{
  "request_id": "uuid-here",
  "model_id": "los_fakeeh_ksa",
  "prediction": "LONG",
  "score": 0.85,
  "latency_ms": 142
}
```

---

## 📊 Monitoring & Health Checks

### Check Gateway Health
```bash
curl http://localhost:8000/health
```

**Healthy Response:**
```json
{
  "status": "healthy",
  "gateway": "ok",
  "opensearch": "ok",
  "models_loaded": 3
}
```

### List Available Models
```bash
curl http://localhost:8000/models
```

**Response:**
```json
{
  "count": 3,
  "models": {
    "los_fakeeh_ksa": {
      "provider": "azure_ml",
      "version": "1.0",
      "enabled": true,
      "timeout_ms": 5000
    }
  }
}
```

### View Recent Activity (Dashboard)
1. Login to admin dashboard
2. Go to **📋 Activity** tab
3. View recent actions with timestamps

### Monitor Logs
```bash
# View gateway logs (if running in terminal)
# Or check log file if configured

# Check activity logs
tail -f logs/activity.jsonl
```

---

## ⏹️ Stopping the Gateway

### Method 1: If Running in Foreground
Press `CTRL + C` in the terminal where it's running

**Expected output:**
```
^C
INFO:     Shutting down
INFO:     Finished server shutdown
```

### Method 2: If Running in Background
```bash
# Find the process
ps aux | grep "python main.py"

# Kill the process (replace XXXX with actual PID)
kill XXXX

# Or force kill if needed
kill -9 XXXX
```

### Method 3: Using pkill
```bash
pkill -f "python main.py"
```

### Verify It's Stopped
```bash
curl http://localhost:8000/health
```

**Expected:** Connection refused or timeout

---

## 🔧 Troubleshooting Guide

### Problem 1: Gateway Won't Start - "Address already in use"

**Symptom:**
```
ERROR: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in .env
echo "GATEWAY_PORT=8001" >> .env

# Restart
python main.py
```

---

### Problem 2: "ModuleNotFoundError: No module named 'fastapi'"

**Symptom:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Check if activated (should show venv path)
which python

# Reinstall dependencies
pip install -r requirements.txt

# Retry
python main.py
```

---

### Problem 3: Prediction Returns "Model not found"

**Symptom:**
```json
{
  "detail": "Model 'los_fakeeh_ksa' not found in registry"
}
```

**Solution:**
```bash
# Check models.yaml exists
cat config/models.yaml

# Verify model_id matches exactly
# Check if model is enabled in config/models.yaml

# Restart gateway to reload config
pkill -f "python main.py"
python main.py
```

---

### Problem 4: "Gateway timeout" or Slow Responses

**Symptom:**
```json
{
  "detail": "Gateway timeout: Azure ML request timeout after 5000ms"
}
```

**Solution:**
```bash
# Check Azure endpoint is reachable
curl -I http://52934d5b-4a57-4ac8-ab56-8667f4a7a8d4.eastus.azurecontainer.io/score

# Increase timeout in config/models.yaml
nano config/models.yaml
# Change: timeout_ms: 10000

# Reload config via admin dashboard or restart
```

---

### Problem 5: Admin Login Fails

**Symptom:**
```
Invalid email or password
```

**Solution:**
```bash
# Verify you're using correct credentials:
# Email: gulshan@pragyaa.ai
# Password: changeme123

# Check auth/users.py for valid users
cat auth/users.py | grep "@pragyaa.ai"

# Clear browser cookies and retry

# Check server logs for specific error
```

---

### Problem 6: OpenSearch Connection Issues

**Symptom:**
```
WARNING: OpenSearch not connected, skipping log
```

**Impact:** Predictions still work, but not logged for analytics

**Solution:**
```bash
# Option 1: Start OpenSearch with Docker
docker-compose up -d opensearch

# Option 2: Continue without OpenSearch (predictions work fine)
# Just ignore the warning

# Option 3: Disable OpenSearch logging
# Edit .env and set:
# OPENSEARCH_HOST=none
```

---

### Problem 7: Cannot Access Dashboard from Browser

**Symptom:** Browser shows "Unable to connect" or "ERR_CONNECTION_REFUSED"

**Solution:**
```bash
# 1. Verify gateway is running
curl http://localhost:8000/health

# 2. Check you're using correct URL
# Correct: http://localhost:8000/admin
# Wrong: https://localhost:8000/admin (no SSL)

# 3. If on remote VM, use VM's IP address
# http://<VM-IP>:8000/admin

# 4. Check firewall rules allow port 8000
sudo ufw status
sudo ufw allow 8000/tcp

# 5. Verify gateway is listening on 0.0.0.0, not 127.0.0.1
# Check .env file:
cat .env | grep GATEWAY_HOST
# Should be: GATEWAY_HOST=0.0.0.0
```

---

### Problem 8: Model Predictions Return Errors from Azure

**Symptom:**
```json
{
  "detail": "Model error: Azure ML error: 400 - Bad Request"
}
```

**Solution:**
```bash
# 1. Test Azure endpoint directly
curl -X POST http://52934d5b-4a57-4ac8-ab56-8667f4a7a8d4.eastus.azurecontainer.io/score \
  -H "Content-Type: application/json" \
  -d '{"data": [{"AGE": 38}]}'

# 2. Check input format in adapters/mappers.py
cat adapters/mappers.py | grep "los_fakeeh_input" -A 50

# 3. Verify all required fields are provided
python test_los_model.py

# 4. Check Azure ML model is running
# Contact Azure ML team to verify endpoint status
```

---

### Problem 9: High Memory Usage

**Symptom:** System becomes slow, high RAM usage

**Solution:**
```bash
# Check memory usage
free -h

# Check Python process memory
ps aux | grep python | awk '{print $6}'

# Restart gateway
pkill -f "python main.py"
python main.py

# If issue persists, check for memory leaks in logs
# Consider increasing VM memory or limiting concurrent requests
```

---

### Problem 10: "Permission denied" Errors

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: 'logs/activity.jsonl'
```

**Solution:**
```bash
# Create logs directory with correct permissions
mkdir -p logs
chmod 755 logs

# Fix file permissions
chmod 644 logs/*.jsonl

# Ensure you're running as the correct user
whoami

# Restart gateway
python main.py
```

---

## 📚 Common Tasks

### Task 1: Enable/Disable a Model

**Via Admin Dashboard:**
1. Login to dashboard
2. Go to **📊 Overview** tab
3. Find model in "Model Registry" section
4. Click toggle switch next to model name
5. Model immediately enabled/disabled

**Via Configuration File:**
```bash
# Edit models.yaml
nano config/models.yaml

# Change enabled: true to enabled: false (or vice versa)
# Example:
los_fakeeh_ksa:
  enabled: false  # Change this line

# Save and reload config
curl -X POST http://localhost:8000/admin/reload-config \
  -H "Authorization: Bearer YOUR_TOKEN"

# Or restart gateway
pkill -f "python main.py"
python main.py
```

---

### Task 2: Add a New Model

```bash
# 1. Edit models.yaml
nano config/models.yaml

# 2. Add new model configuration:
new_model_name:
  provider: azure_ml
  endpoint_url: https://your-new-endpoint.azurecontainer.io/score
  auth_type: none
  api_key: null
  timeout_ms: 5000
  version: "1.0"
  input_mapper: new_model_mapper
  output_mapper: new_model_mapper
  enabled: true

# 3. Create mapper functions in adapters/mappers.py
nano adapters/mappers.py

# Add:
# def new_model_mapper_input(inputs):
#     return {"data": [inputs]}
# 
# def new_model_mapper_output(response):
#     return {"prediction": response.get("result"), "score": None}

# 4. Update mapper registry at bottom of mappers.py

# 5. Restart gateway
pkill -f "python main.py"
python main.py

# 6. Test new model
curl -X POST http://localhost:8000/predict/new_model_name \
  -H "Content-Type: application/json" \
  -d '{"inputs": {...}}'
```

---

### Task 3: Update Model Configuration

```bash
# 1. Edit models.yaml
nano config/models.yaml

# 2. Make changes (e.g., increase timeout)
los_fakeeh_ksa:
  timeout_ms: 10000  # Changed from 5000

# 3. Reload config (no restart needed)
# Login to admin dashboard and click "Reload Config"
# Or use API:
curl -X POST http://localhost:8000/admin/reload-config

# 4. Verify changes
curl http://localhost:8000/models
```

---

### Task 4: Export Prediction Analytics

**Via Admin Dashboard:**
1. Login to dashboard
2. Go to **📈 Analytics** tab
3. Set date range and filters
4. Click **Export CSV** or **Export Excel**
5. File downloads to your browser

**Via Command Line (if OpenSearch is running):**
```bash
# This requires OpenSearch to be running
# Contact DevOps team for direct OpenSearch queries
```

---

### Task 5: Generate API Key for Client

**Via Admin Dashboard:**
1. Login to dashboard
2. Go to **🔑 API Keys** tab
3. Fill in form:
   - Client Name: e.g., "Mobile App Production"
   - Description: "For mobile app v2.0"
4. Click **Generate API Key**
5. Copy key and save securely (shown only once)
6. Share with client team

---

### Task 6: View Recent Predictions

**Via Admin Dashboard:**
1. Login to dashboard
2. Go to **📊 Overview** tab
3. Scroll to "Recent Predictions" section
4. Shows last 20 predictions with details

**Via API:**
```bash
# Requires authentication token
# Login first to get token, then:
curl http://localhost:8000/admin/predictions \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Task 7: Test Model with Custom Data

```bash
# 1. Create JSON file with test data
cat > test_input.json << 'EOF'
{
  "inputs": {
    "AGE": 45,
    "BMI": 28.5,
    "NATIONALITY": "SAUDI",
    "ADMISSION_TYPE": "Emergency",
    "ROOM_TYPE": "ICU"
  }
}
EOF

# 2. Send prediction request
curl -X POST http://localhost:8000/predict/los_fakeeh_ksa \
  -H "Content-Type: application/json" \
  -d @test_input.json

# 3. Check response
```

---

### Task 8: Backup Configuration

```bash
# Backup models configuration
cp config/models.yaml config/models.yaml.backup-$(date +%Y%m%d)

# Backup environment file
cp .env .env.backup-$(date +%Y%m%d)

# Backup activity logs
cp -r logs logs.backup-$(date +%Y%m%d)

# Create full backup archive
tar -czf gateway-backup-$(date +%Y%m%d).tar.gz \
  config/ templates/ adapters/ models/ services/ auth/ \
  .env main.py requirements.txt

# List backups
ls -lh *.tar.gz
```

---

### Task 9: Update Gateway Code

```bash
# 1. Stop the gateway
pkill -f "python main.py"

# 2. Backup current version
cp -r . ../prediction-gateway-backup-$(date +%Y%m%d)

# 3. Pull latest changes
git pull origin main

# 4. Update dependencies (if requirements changed)
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 5. Review changes
git log -5 --oneline

# 6. Restart gateway
python main.py

# 7. Verify health
curl http://localhost:8000/health
```

---

### Task 10: Run Health Check Before Deployment

```bash
# Use the provided check script
python check.py

# This verifies:
# ✅ Configuration files exist
# ✅ Required dependencies installed
# ✅ Models configured correctly
# ✅ Endpoints reachable
# ✅ Permissions correct
```

---

## 🚨 Emergency Procedures

### Emergency 1: Gateway is Down - Quick Restart

```bash
# 1. Kill any existing processes
pkill -9 -f "python main.py"

# 2. Navigate to directory
cd /Users/krishnabajpai/code/pragyaa-ai/gateway/prediction-gateway

# 3. Quick start
./start.sh

# 4. Verify within 30 seconds
curl http://localhost:8000/health
```

**Expected Time:** < 1 minute

---

### Emergency 2: All Predictions Failing

```bash
# 1. Check Azure ML endpoint directly
curl -I http://52934d5b-4a57-4ac8-ab56-8667f4a7a8d4.eastus.azurecontainer.io/score

# If Azure is down:
#   - Contact Azure ML team
#   - Check Azure status page
#   - Escalate to DevOps

# If Azure is up but gateway fails:
# 2. Restart gateway
pkill -f "python main.py"
python main.py

# 3. Test immediately
python test_los_model.py

# 4. If still failing, check logs and contact DevOps
```

---

### Emergency 3: High Error Rate (>10%)

```bash
# 1. Check error rate in dashboard
# Login -> Analytics tab -> Error Rate chart

# 2. Check recent errors
tail -50 logs/activity.jsonl | grep "error"

# 3. Common causes:
#    - Azure ML endpoint down -> Contact Azure team
#    - Invalid input format -> Check recent code changes
#    - Timeout issues -> Increase timeout_ms in models.yaml

# 4. If critical, disable problematic model
nano config/models.yaml
# Set enabled: false for failing model
pkill -f "python main.py"
python main.py
```

---

### Emergency 4: Cannot Access Admin Dashboard

```bash
# 1. Verify gateway is running
curl http://localhost:8000/health

# If gateway is down:
./start.sh

# If gateway is up but dashboard inaccessible:
# 2. Check browser console for errors (F12)

# 3. Try different browser or incognito mode

# 4. Clear cookies
# Chrome: Settings -> Privacy -> Clear browsing data

# 5. Check auth service
cat auth/users.py | grep "gulshan@pragyaa.ai"

# 6. Restart gateway
pkill -f "python main.py"
python main.py
```

---

### Emergency 5: Disk Space Full

```bash
# 1. Check disk usage
df -h

# 2. Clean up logs
rm -f logs/*.jsonl.old
find logs/ -name "*.jsonl" -mtime +30 -delete

# 3. Clean up Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# 4. Clean up Docker (if using OpenSearch)
docker system prune -a -f

# 5. Archive old backups
tar -czf old-backups-$(date +%Y%m%d).tar.gz *.backup-*
rm -f *.backup-*

# 6. Check space again
df -h
```

---

## 📞 Escalation & Support

### When to Escalate

**Immediate Escalation:**
- Gateway down for > 5 minutes
- All predictions failing
- Security breach suspected
- Data loss

**Standard Escalation:**
- Error rate > 10% for > 30 minutes
- Performance degradation
- Model accuracy issues
- Configuration questions

### Support Contacts

**DevOps Team:**
- Email: devops@pragyaa.ai
- Slack: #devops-support

**ML Team (Model Issues):**
- Email: ml-team@pragyaa.ai
- Slack: #ml-models

**Security Team:**
- Email: security@pragyaa.ai
- Slack: #security-incidents

---

## 📝 Daily Checklist

### Morning Checklist (5 minutes)
- [ ] Check gateway health: `curl http://localhost:8000/health`
- [ ] Login to admin dashboard
- [ ] Review Overview tab for status
- [ ] Check error rate in Analytics tab (should be < 5%)
- [ ] Review recent predictions (last 24 hours)

### Weekly Checklist (15 minutes)
- [ ] Review activity logs for unusual patterns
- [ ] Check disk space: `df -h`
- [ ] Backup configuration files
- [ ] Review API key usage
- [ ] Test all enabled models
- [ ] Check for software updates: `git fetch origin`

### Monthly Checklist (30 minutes)
- [ ] Archive old logs
- [ ] Review model performance metrics
- [ ] Update documentation if needed
- [ ] Test disaster recovery procedure
- [ ] Review and rotate admin passwords
- [ ] Clean up old backups

---

## 🎓 Training Exercises

### Exercise 1: Start and Test
1. Start the gateway
2. Access admin dashboard
3. Run test script
4. Verify prediction in dashboard
5. Stop the gateway

### Exercise 2: Handle Failure
1. Start gateway
2. Kill it forcefully: `pkill -9 -f "python main.py"`
3. Verify it's down
4. Restart it
5. Verify health

### Exercise 3: Configuration Change
1. Disable `los_fakeeh_ksa` model via dashboard
2. Try to make prediction (should fail)
3. Re-enable the model
4. Verify prediction works

### Exercise 4: Monitor Analytics
1. Run 10 test predictions
2. Login to dashboard
3. Find those predictions in Overview
4. Check Analytics charts
5. Export data to CSV

---

## 📚 Additional Resources

### Documentation Files
- `README.md` - Main project documentation
- `API_USAGE.md` - API usage examples
- `LOS_MODEL_GUIDE.md` - LOS model specific guide
- `ADMIN_PANEL_README.md` - Admin dashboard guide
- `TROUBLESHOOTING.md` - Detailed troubleshooting

### Configuration Files
- `config/models.yaml` - Model configurations
- `.env` - Environment variables
- `requirements.txt` - Python dependencies

### Test Files
- `test_los_model.py` - LOS model test script
- `test_gateway.py` - Gateway integration tests
- `check.py` - Pre-deployment health check

---

## 🔖 Quick Reference Commands

```bash
# Start gateway
./start.sh

# Stop gateway
pkill -f "python main.py"

# Health check
curl http://localhost:8000/health

# List models
curl http://localhost:8000/models

# Run test
python test_los_model.py

# View logs
tail -f logs/activity.jsonl

# Check disk space
df -h

# Check process
ps aux | grep "python main.py"

# Backup config
cp config/models.yaml config/models.yaml.backup

# Update code
git pull origin main
```

---

## ✅ Summary

**To Start:**
```bash
cd /Users/krishnabajpai/code/pragyaa-ai/gateway/prediction-gateway
./start.sh
```

**To Test:**
```bash
python test_los_model.py
```

**To Access Dashboard:**
- URL: http://localhost:8000/admin
- Email: gulshan@pragyaa.ai
- Password: changeme123

**To Stop:**
```bash
pkill -f "python main.py"
```

**If Issues:**
1. Check troubleshooting section
2. Restart gateway
3. Contact DevOps team

---

**Document Version:** 1.0  
**Maintained by:** DevOps Team  
**Last Review:** December 18, 2025  
**Next Review:** January 18, 2026
