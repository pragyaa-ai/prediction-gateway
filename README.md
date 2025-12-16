# 🚀 ML Inference Gateway - Enterprise Edition

A production-ready, enterprise-grade ML inference gateway with multi-model support, Azure ML integration, comprehensive analytics, and a beautiful admin dashboard.

## ✨ Premium Features

### Core Capabilities
- **Multi-Model Support**: Route requests to different ML models based on configuration
- **Azure ML Integration**: Seamless integration with Azure-hosted models via HTTP adapter pattern
- **Request/Response Transformation**: Automatic input/output mapping for different model versions
- **Async Logging**: Non-blocking OpenSearch integration for prediction logging
- **JWT Authentication**: Secure admin panel with token-based authentication

### 🎨 Premium Dashboard Features
- **📊 Overview Dashboard**: Real-time status cards, model registry, performance metrics
- **📈 Analytics & Insights**: 
  - Prediction volume timeline charts (Chart.js)
  - Error rate tracking by model
  - Model latency comparison
  - Export to CSV/Excel/JSON
- **🧪 Model Testing Tool**: Test models with custom JSON inputs directly from UI
- **📦 Batch Predictions**: Upload CSV files for bulk predictions
- **🔑 API Key Management**: Generate, revoke, and monitor client API keys
- **📋 Activity Logs**: Complete audit trail of all admin actions
- **⚙️ Settings Panel**: Email configuration, SMTP testing
- **🌙 Dark Mode**: Toggle between light and dark themes
- **🔒 Secure Authentication**: Multi-user support with role-based access

## 📦 Installation

### Prerequisites
- Python 3.9+
- OpenSearch 2.11+ (optional but recommended)
- Azure ML endpoint (for model hosting)

### Setup Steps

1. **Install dependencies**
\`\`\`bash
pip install -r requirements.txt
\`\`\`

2. **Configure environment** (create \`.env\`)
\`\`\`env
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
SECRET_KEY=your-super-secret-key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
\`\`\`

3. **Run the gateway**
\`\`\`bash
python main.py
\`\`\`

Access at: http://localhost:8000

## 🎯 Admin Dashboard

**URL:** http://localhost:8000/admin

**Default Users:**
- Gulshan Mehta: gulshan@pragyaa.ai
- Manoj Gulati: manoj@pragyaa.ai
- Krishna Bajpai: krishna@pragyaa.ai

**Default Password:** changeme123

### Dashboard Tabs

1. **📊 Overview**: Real-time status, models, predictions
2. **📈 Analytics**: Charts, export data
3. **🧪 Testing**: Test models with custom inputs
4. **📦 Batch**: CSV upload for bulk predictions
5. **🔑 API Keys**: Generate/manage keys
6. **📋 Activity**: Audit logs
7. **⚙️ Settings**: Email config, SMTP testing

## 📝 License

Proprietary - Pragyaa AI

---
**Version:** 1.0.0 | **Status:** ✅ Production Ready
