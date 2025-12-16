# Changelog

All notable changes to the ML Inference Gateway will be documented in this file.

## [1.0.0] - 2024-01-15

### 🎉 Initial Release - Enterprise Edition

### Added

#### Core Infrastructure
- ✅ FastAPI-based inference gateway with async support
- ✅ Multi-model routing via YAML configuration
- ✅ Azure ML adapter with HTTP integration
- ✅ Request/response transformation pipeline
- ✅ OpenSearch async logging (non-blocking)
- ✅ Health check endpoints with system status

#### Authentication & Security
- ✅ JWT token-based authentication
- ✅ bcrypt password hashing
- ✅ Multi-user support (3 super admin users)
- ✅ OAuth2 password flow integration
- ✅ Secure token storage in localStorage
- ✅ 8-hour token expiration

#### Admin Dashboard
- ✅ Beautiful purple gradient UI design
- ✅ Responsive layout for all screen sizes
- ✅ Tab-based navigation (7 sections)
- ✅ Real-time status cards
- ✅ Model registry viewer
- ✅ Start/Stop model toggle functionality
- ✅ Auto-refresh every 60 seconds

#### Analytics & Reporting
- ✅ Prediction volume timeline (Chart.js)
- ✅ Error rate tracking by model
- ✅ Model latency comparison charts
- ✅ Export to CSV/Excel/JSON
- ✅ Advanced search with filters (model, client, status, date range)
- ✅ Performance metrics dashboard

#### Model Testing
- ✅ In-dashboard model testing tool
- ✅ JSON input editor with syntax validation
- ✅ Real-time prediction results
- ✅ Latency measurement
- ✅ Error handling with formatted output

#### Batch Processing
- ✅ CSV file upload for bulk predictions
- ✅ Progress tracking during processing
- ✅ Success/error statistics
- ✅ Detailed results viewing
- ✅ Download results functionality

#### API Key Management
- ✅ Generate secure API keys (SHA256 hashed)
- ✅ Key format: `pragyaa_{32-char-token}`
- ✅ Usage tracking (count, last used)
- ✅ Revocation support
- ✅ Client management (name, email, permissions)

#### Activity Logging
- ✅ JSONL-based audit trail
- ✅ Log all admin actions (login, toggle model, config reload, etc.)
- ✅ User tracking (email, name)
- ✅ Success/failure status
- ✅ Detailed action metadata
- ✅ Searchable activity logs UI

#### Email Notifications
- ✅ SMTP integration (Gmail support)
- ✅ Model down alerts
- ✅ High error rate warnings
- ✅ Test email functionality
- ✅ Configuration validation

#### UI/UX Enhancements
- ✅ Dark mode toggle with localStorage persistence
- ✅ Theme icons (🌙/☀️)
- ✅ Smooth transitions and animations
- ✅ Toast notifications for actions
- ✅ Confirmation dialogs for destructive actions
- ✅ Empty state placeholders

#### Data Management
- ✅ Daily index rotation (ml-predictions-v1-YYYY.MM.DD)
- ✅ Comprehensive prediction metadata
- ✅ Input hashing for privacy
- ✅ Latency tracking
- ✅ Client identification

### Technical Improvements
- ✅ Pydantic settings management
- ✅ Environment variable support (.env)
- ✅ Async/await throughout
- ✅ Background tasks for non-blocking operations
- ✅ Comprehensive error handling
- ✅ Type hints with Pydantic models
- ✅ Clean separation of concerns (services, adapters, models)

### Dependencies
- fastapi==0.109.0
- uvicorn[standard]==0.27.0
- pydantic==2.5.3
- pydantic-settings==2.1.0
- python-dotenv==1.0.0
- pyyaml==6.0.1
- httpx==0.26.0
- opensearch-py==2.4.2
- jinja2==3.1.3
- python-multipart==0.0.6
- aiofiles==23.2.1
- python-jose[cryptography]==3.3.0
- passlib[bcrypt]==1.7.4
- pandas==2.1.4
- openpyxl==3.1.2
- aiosmtplib==3.0.1

### Configuration
- Default admin users: Gulshan Mehta, Manoj Gulati, Krishna Bajpai
- Default password: changeme123 (⚠️ must change in production)
- OpenSearch optional (graceful degradation)
- SMTP optional (for email features)

### Endpoints Added
- `POST /v1/predict` - Inference endpoint
- `GET /health` - Health check
- `GET /models` - List available models
- `GET /admin` - Admin dashboard
- `POST /admin/login` - Authentication
- `POST /admin/toggle-model/{model_id}` - Enable/disable models
- `POST /admin/reload-config` - Reload YAML config
- `GET /admin/analytics/timeline` - Prediction volume over time
- `GET /admin/analytics/error-rates` - Error rates by model
- `GET /admin/analytics/export` - Export data (CSV/Excel/JSON)
- `GET /admin/activity-logs` - Get activity logs
- `GET /admin/activity-logs/user/{email}` - User-specific logs
- `GET /admin/activity-logs/action/{action}` - Action-specific logs
- `POST /admin/api-keys` - Generate API key
- `GET /admin/api-keys` - List all API keys
- `DELETE /admin/api-keys/{key_hash}` - Revoke API key
- `GET /admin/api-keys/{key_hash}/stats` - Key usage stats
- `GET /admin/search` - Advanced prediction search
- `POST /admin/test-model` - Test model with custom input
- `POST /admin/batch-upload` - Upload CSV for batch predictions
- `POST /admin/email/test` - Send test email
- `GET /admin/email/config` - Get email configuration

### Files Structure
```
new-gateway/
├── main.py (870 lines)
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── config/
│   ├── models.yaml
│   └── settings.py
├── models/
│   ├── schemas.py
│   └── registry.py
├── adapters/
│   ├── base.py
│   └── mappers.py
├── services/
│   ├── opensearch.py
│   ├── activity_log.py
│   ├── api_keys.py
│   └── email_service.py
├── auth/
│   └── users.py
├── templates/
│   ├── login.html
│   └── dashboard.html (1500+ lines)
└── logs/
    └── activity.jsonl
```

### Known Limitations
- No built-in rate limiting (use nginx/API gateway)
- No user password change UI (manual in users.py)
- Email alerts require SMTP configuration
- OpenSearch recommended for full functionality
- No database for persistent API key storage (in-memory)

### Future Enhancements (Roadmap)
- [ ] User management UI (add/edit/delete users)
- [ ] Password change functionality
- [ ] Role-based permissions (viewer, operator, admin)
- [ ] Model versioning and A/B testing
- [ ] Cost tracking per model/client
- [ ] Webhook notifications
- [ ] Slack/Teams integration
- [ ] Custom alert rules configuration
- [ ] Model performance degradation detection
- [ ] Automated model retraining triggers
- [ ] Multi-cloud support (AWS SageMaker, GCP Vertex AI)
- [ ] GraphQL API option
- [ ] WebSocket for real-time updates
- [ ] Kubernetes deployment manifests
- [ ] Prometheus metrics export
- [ ] Grafana dashboards

---

**Contributors:** Gulshan Mehta, Manoj Gulati, Krishna Bajpai  
**License:** Proprietary - Pragyaa AI  
**Status:** ✅ Production Ready
