# 🔐 Admin Panel - Super Admin Guide

## Welcome to ML Gateway Admin Panel!

You have been granted **Super Admin** access to the ML Inference Gateway.

## 👥 Authorized Super Admins

| Name | Email | Role |
|------|-------|------|
| **Gulshan Mehta** | gulshan@pragyaa.ai | Super Admin |
| **Manoj Gulati** | manoj@pragyaa.ai | Super Admin |
| **Krishna Bajpai** | krishna@pragyaa.ai | Super Admin |

## 🚀 How to Access

### 1. Start the Gateway

```bash
cd /Users/krishnabajpai/code/pragyaa-ai/new-gateway
./start.sh
```

### 2. Access Admin Panel

Open your browser and navigate to:
```
http://localhost:8000/admin
```

You'll be redirected to the login page.

### 3. Login

**Default Password (CHANGE IMMEDIATELY):** `changeme123`

- Email: Your @pragyaa.ai email
- Password: `changeme123`

## 🎨 Dashboard Features

Once logged in, you'll have access to:

### 📊 Overview Cards
- **Gateway Status** - System health
- **OpenSearch Connection** - Logging status  
- **Active Models** - Number of registered models
- **Predictions Today** - Recent activity count

### 🎯 Model Registry
- View all registered ML models
- See endpoint URLs, versions, timeouts
- **Start/Stop models** with one click
- Reload configuration without restart

### 📈 Performance Metrics
- Average latency per model
- Total prediction counts
- Success/error rates

### 🔮 Recent Predictions
- Last 50 predictions in real-time
- Request IDs, timestamps, clients
- Prediction results and scores
- Status indicators

## 🛠️ Admin Actions

### Stop a Model

1. Navigate to **Model Registry** section
2. Find the model you want to stop
3. Click the **"⏸ Stop"** button
4. Confirm the action
5. ✅ Model is now disabled

**Use case:** Azure endpoint maintenance, cost control, bug fixes

### Start a Model

1. Find the disabled model (gray "DISABLED" badge)
2. Click the **"▶ Start"** button
3. Confirm the action
4. ✅ Model is now active

### Reload Configuration

1. Edit `config/models.yaml` on the server
2. Click **"↻ Reload Config"** button in dashboard
3. ✅ Changes applied without restart

## 🔒 Security

### Change Your Password

**IMPORTANT:** Change the default password immediately!

1. Contact the system administrator
2. Or edit `/auth/users.py` on the server:

```python
"your-email@pragyaa.ai": {
    "name": "Your Name",
    "email": "your-email@pragyaa.ai",
    "password_hash": pwd_context.hash("YOUR_NEW_STRONG_PASSWORD"),
    "role": "super_admin"
}
```

3. Restart the gateway

### Session Management

- **Session Duration:** 8 hours
- **Auto-logout:** After token expires
- **Manual Logout:** Click "🚪 Logout" button (top right)

## 📱 Mobile Access

The admin panel is fully responsive and works on:
- ✅ Desktop browsers
- ✅ Tablets
- ✅ Mobile phones

## 🔔 Best Practices

1. **Always logout** when done
2. **Don't share credentials** - each admin has their own account
3. **Check model status** before disabling
4. **Monitor OpenSearch** connection health
5. **Review recent predictions** for anomalies

## ⚠️ Important Notes

### Model Toggle Behavior
- **Memory-based:** Changes apply immediately
- **Not persistent:** State resets on gateway restart
- **For permanent changes:** Edit `config/models.yaml` + reload

### What You Can Do
- ✅ View all models and their status
- ✅ Start/stop models instantly
- ✅ View prediction logs (if OpenSearch is running)
- ✅ Monitor system health
- ✅ Reload configuration

### What You Cannot Do
- ❌ Add new models (edit YAML file manually)
- ❌ Change endpoint URLs (edit YAML file manually)
- ❌ Modify model versions (edit YAML file manually)
- ❌ Delete prediction logs

## 🆘 Troubleshooting

### "Invalid email or password"
- ✅ Check you're using your @pragyaa.ai email
- ✅ Verify password is `changeme123` (default)
- ✅ Ensure caps lock is OFF

### "Authentication required" errors
- ✅ Your session may have expired - login again
- ✅ Clear browser cache and cookies
- ✅ Try incognito/private browsing mode

### Dashboard not loading
- ✅ Check gateway is running: `http://localhost:8000/health`
- ✅ Check server logs in terminal
- ✅ Verify you're accessing correct URL

### Can't stop/start models
- ✅ Ensure you're logged in
- ✅ Check network connection
- ✅ Try refreshing the page

## 📞 Support

For technical support:
- Check the main README.md
- Review server logs
- Contact: Krishna Bajpai (krishna@pragyaa.ai)

## 🎯 Quick Actions

### Daily Operations

**Morning Check:**
```
1. Login to admin panel
2. Check Gateway Status (should be green)
3. Verify OpenSearch connection
4. Review overnight predictions
```

**Before Model Changes:**
```
1. Check current model status
2. Review recent prediction errors
3. Plan maintenance window
4. Stop model if needed
```

**After Azure Maintenance:**
```
1. Login to admin panel
2. Start the affected model
3. Test with a prediction
4. Monitor for errors
```

## 🎨 Dashboard Navigation

```
┌─────────────────────────────────────────────┐
│  🚀 ML Gateway Admin     👤 Your Name  🚪   │ ← Top Bar
├─────────────────────────────────────────────┤
│  Dashboard Overview                          │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐              │
│  │ ✅ │ │ 🟢 │ │ 🤖 │ │ 📊 │ Status Cards │
│  └────┘ └────┘ └────┘ └────┘              │
├─────────────────────────────────────────────┤
│  🎯 Model Registry                          │
│  [Table with Start/Stop buttons]            │
├─────────────────────────────────────────────┤
│  📈 Model Performance                       │
│  [Performance metrics per model]            │
├─────────────────────────────────────────────┤
│  🔮 Recent Predictions                      │
│  [Last 50 predictions with details]         │
└─────────────────────────────────────────────┘
```

## 🌟 Features Highlights

### Real-time Updates
- Dashboard auto-refreshes every 60 seconds
- Always showing latest data

### Beautiful UI
- Modern, gradient design
- Color-coded status indicators
- Smooth animations
- Mobile-responsive

### One-Click Actions
- No command line needed
- Instant visual feedback
- Confirmation prompts for safety

### Secure Access
- JWT-based authentication
- Individual user accounts
- Session management

---

**Enjoy managing your ML Gateway! 🚀**

For questions, contact your system administrator or refer to the main documentation.
