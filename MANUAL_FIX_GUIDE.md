# 🚨 MANUAL TROUBLESHOOTING GUIDE

## Issues You Encountered:
1. **chown warning**: "." should be ":opensearch.opensearch"
2. **OpenSearch not starting** during installation
3. **Gateway not running** after installation

## 🔧 STEP-BY-STEP MANUAL FIX

### Step 1: Fix OpenSearch Installation Issues

```bash
# Stop any running OpenSearch
sudo systemctl stop opensearch

# Remove problematic installation (if needed)
sudo apt remove --purge opensearch -y

# Clean up
sudo rm -rf /var/lib/opensearch
sudo rm -rf /etc/opensearch
sudo deluser opensearch 2>/dev/null || true
sudo delgroup opensearch 2>/dev/null || true

# Reinstall OpenSearch properly
wget -qO - https://artifacts.opensearch.org/publickeys/opensearch.pgp | sudo apt-key add -
echo "deb https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/apt stable main" | sudo tee /etc/apt/sources.list.d/opensearch-2.x.list
sudo apt update
sudo apt install -y opensearch=2.11.0

# Create opensearch user and group
sudo useradd -r -s /bin/false opensearch
sudo mkdir -p /var/lib/opensearch
sudo mkdir -p /var/log/opensearch
sudo chown -R opensearch:opensearch /var/lib/opensearch
sudo chown -R opensearch:opensearch /var/log/opensearch
sudo chown -R opensearch:opensearch /etc/opensearch
```

### Step 2: Configure OpenSearch Properly

```bash
# Edit OpenSearch configuration
sudo tee /etc/opensearch/opensearch.yml > /dev/null <<EOF
cluster.name: ml-gateway-cluster
path.data: /var/lib/opensearch
path.logs: /var/log/opensearch
network.host: 0.0.0.0
http.port: 9200
discovery.type: single-node
bootstrap.memory_lock: true
EOF

# Set proper permissions
sudo chown opensearch:opensearch /etc/opensearch/opensearch.yml
sudo chmod 660 /etc/opensearch/opensearch.yml

# Configure JVM options
sudo tee /etc/opensearch/jvm.options.d/custom.options > /dev/null <<EOF
-Xms512m
-Xmx512m
EOF

# Start OpenSearch
sudo systemctl enable opensearch
sudo systemctl start opensearch

# Wait and check
sleep 10
sudo systemctl status opensearch
curl http://localhost:9200/_cluster/health
```

### Step 3: Setup Gateway User and Directory

```bash
# Create gateway user
sudo useradd -m -s /bin/bash gateway || true

# Create application directory
sudo mkdir -p /opt/ml-gateway
sudo chown gateway:gateway /opt/ml-gateway

# Copy your application files to /opt/ml-gateway
# (Assuming you uploaded the repository files)
sudo cp -r * /opt/ml-gateway/ 2>/dev/null || echo "Copy files manually"
sudo chown -R gateway:gateway /opt/ml-gateway
```

### Step 4: Install Python Dependencies

```bash
# Switch to gateway user
sudo -u gateway bash << 'EOF'
cd /opt/ml-gateway

# Create virtual environment
python3 -m venv venv

# Activate and install
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Test import
python3 -c "import main; print('✅ Import successful')"
EOF
```

### Step 5: Create Systemd Services

```bash
# OpenSearch service (if not already created)
sudo tee /etc/systemd/system/opensearch.service > /dev/null <<EOF
[Unit]
Description=OpenSearch
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=opensearch
Group=opensearch
Environment=OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
Environment=OPENSEARCH_PATH_CONF=/etc/opensearch
ExecStart=/usr/share/opensearch/bin/opensearch
LimitNOFILE=65536
LimitNPROC=4096
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
EOF

# Gateway service
sudo tee /etc/systemd/system/ml-gateway.service > /dev/null <<EOF
[Unit]
Description=ML Inference Gateway
After=network.target opensearch.service
Requires=opensearch.service

[Service]
Type=simple
User=gateway
WorkingDirectory=/opt/ml-gateway
Environment=OPENSEARCH_HOST=localhost
Environment=OPENSEARCH_PORT=9200
Environment=OPENSEARCH_USER=admin
Environment=OPENSEARCH_PASSWORD=Admin@123
Environment=OPENSEARCH_USE_SSL=false
Environment=OPENSEARCH_VERIFY_CERTS=false
Environment=GATEWAY_HOST=0.0.0.0
Environment=GATEWAY_PORT=8000
ExecStart=/opt/ml-gateway/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start services
sudo systemctl daemon-reload
sudo systemctl enable opensearch
sudo systemctl enable ml-gateway
sudo systemctl start opensearch

# Wait for OpenSearch
sleep 30
sudo systemctl start ml-gateway
```

### Step 6: Configure Firewall

```bash
sudo ufw allow 8000/tcp
sudo ufw allow 9200/tcp
sudo ufw allow 22/tcp
sudo ufw --force enable
```

### Step 7: Verify Installation

```bash
# Check services
sudo systemctl status opensearch
sudo systemctl status ml-gateway

# Test endpoints
curl http://localhost:9200/_cluster/health
curl http://localhost:8000/health

# Check logs if issues
sudo journalctl -u opensearch -f
sudo journalctl -u ml-gateway -f
```

## 🔍 Common Issues & Fixes

### Issue: OpenSearch won't start
```bash
# Check logs
sudo journalctl -u opensearch -n 50

# Common fixes:
sudo chown -R opensearch:opensearch /var/lib/opensearch
sudo chmod 755 /usr/share/opensearch/bin/opensearch
```

### Issue: Gateway won't start
```bash
# Check logs
sudo journalctl -u ml-gateway -n 50

# Test manual start
sudo -u gateway bash -c "cd /opt/ml-gateway && source venv/bin/activate && python3 -c 'import main'"

# Check if OpenSearch is running first
curl http://localhost:9200/_cluster/health
```

### Issue: Permission errors
```bash
# Fix gateway permissions
sudo chown -R gateway:gateway /opt/ml-gateway

# Fix OpenSearch permissions
sudo chown -R opensearch:opensearch /var/lib/opensearch
sudo chown -R opensearch:opensearch /etc/opensearch
```

### Issue: Port already in use
```bash
# Find what's using the port
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :9200

# Kill process if needed
sudo kill -9 <PID>
```

## 📋 Final Verification

After fixing all issues, run:

```bash
# Check all services
sudo systemctl status opensearch ml-gateway

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:9200/_cluster/health

# Get server IP
ip addr show | grep "inet " | grep -v 127.0.0.1
```

## 🌐 Access URLs

- **Gateway API**: http://YOUR_SERVER_IP:8000
- **Admin Panel**: http://YOUR_SERVER_IP:8000/admin
- **OpenSearch**: http://YOUR_SERVER_IP:9200

## 🔐 Default Login

- Username: `gulshan@pragyaa.ai`
- Password: `changeme123`