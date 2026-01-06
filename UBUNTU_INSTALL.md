# Ubuntu Manual Installation Guide

## Prerequisites
- Ubuntu 20.04+ or 22.04+
- Root or sudo access
- Internet connection

## Step 1: Update System
```bash
sudo apt update && sudo apt upgrade -y
```

## Step 2: Install Python 3
```bash
sudo apt install -y python3 python3-venv python3-dev python3-pip
```

## Step 3: Install OpenSearch
```bash
# Add OpenSearch repository
wget -qO - https://artifacts.opensearch.org/publickeys/opensearch.pgp | sudo apt-key add -
echo "deb https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/apt stable main" | sudo tee /etc/apt/sources.list.d/opensearch-2.x.list
sudo apt update
sudo apt install -y opensearch=2.11.0

# Configure OpenSearch
sudo sed -i 's/#cluster.name: my-application/cluster.name: ml-gateway-cluster/' /etc/opensearch/opensearch.yml
sudo sed -i 's/#network.host: 192.168.0.1/network.host: 0.0.0.0/' /etc/opensearch/opensearch.yml
sudo sed -i 's/#discovery.type: single-node/discovery.type: single-node/' /etc/opensearch/opensearch.yml

# Install OpenSearch Dashboards
sudo apt install -y opensearch-dashboards=2.11.0

# Configure OpenSearch Dashboards
sudo tee /etc/opensearch-dashboards/opensearch_dashboards.yml > /dev/null <<EOF
server.port: 5601
server.host: "0.0.0.0"
opensearch.hosts: ["http://localhost:9200"]
opensearch.ssl.verificationMode: none
opensearch.username: "admin"
opensearch.password: "Admin@123"
opensearch.requestTimeout: 30000
opensearch.pingTimeout: 3000
EOF

# Start OpenSearch Dashboards
sudo systemctl enable opensearch-dashboards
sudo systemctl start opensearch-dashboards
```

## Step 4: Setup Application Directory
```bash
# Create gateway user
sudo useradd -m -s /bin/bash gateway

# Create application directory
sudo mkdir -p /opt/ml-gateway
sudo chown gateway:gateway /opt/ml-gateway

# Copy application files (upload your repository)
# Assuming you upload the files to /opt/ml-gateway/
sudo chown -R gateway:gateway /opt/ml-gateway
```

## Step 5: Install Python Dependencies
```bash
cd /opt/ml-gateway

# Create virtual environment
sudo -u gateway python3 -m venv venv
sudo -u gateway bash -c "source venv/bin/activate && pip install --upgrade pip"
sudo -u gateway bash -c "source venv/bin/activate && pip install -r requirements.txt"
```

## Step 6: Create Systemd Service
```bash
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

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ml-gateway
sudo systemctl start ml-gateway
```

## Step 7: Configure Firewall
```bash
sudo ufw allow 8000/tcp  # Gateway
sudo ufw allow 9200/tcp  # OpenSearch
sudo ufw allow 5601/tcp  # OpenSearch Dashboards
sudo ufw allow 22/tcp    # SSH
sudo ufw --force enable
```

## Step 8: Verify Installation
```bash
# Check services
sudo systemctl status opensearch
sudo systemctl status ml-gateway

# Check health
curl http://localhost:8000/health

# Check logs
sudo journalctl -u ml-gateway -f
```

## Access URLs
- **Gateway API**: http://your-server-ip:8000
- **Admin Panel**: http://your-server-ip:8000/admin
- **OpenSearch**: http://your-server-ip:9200
- **OpenSearch Dashboards**: http://your-server-ip:5601

## Default Admin Credentials
- Username: gulshan@pragyaa.ai
- Password: changeme123

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u ml-gateway -n 50

# Check if OpenSearch is running
curl http://localhost:9200/_cluster/health
```

### Permission issues
```bash
# Fix ownership
sudo chown -R gateway:gateway /opt/ml-gateway
```

### Port conflicts
```bash
# Check what's using ports
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :9200
```