#!/bin/bash

# Ubuntu Deployment Script for ML Gateway
# This script installs and configures the ML Gateway on Ubuntu

set -e

echo "🚀 ML Gateway Ubuntu Deployment"
echo "================================"

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
echo "🐍 Installing Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y curl wget gnupg software-properties-common

# Install OpenSearch
echo "🔍 Installing OpenSearch..."
wget -qO - https://artifacts.opensearch.org/publickeys/opensearch.pgp | sudo apt-key add -
echo "deb https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/apt stable main" | sudo tee /etc/apt/sources.list.d/opensearch-2.x.list
sudo apt update
sudo apt install -y opensearch=2.11.0

# Configure OpenSearch
echo "⚙️ Configuring OpenSearch..."
sudo sed -i 's/#cluster.name: my-application/cluster.name: ml-gateway-cluster/' /etc/opensearch/opensearch.yml
sudo sed -i 's/#path.data: \/var\/lib\/opensearch/path.data: \/var\/lib\/opensearch/' /etc/opensearch/opensearch.yml
sudo sed -i 's/#path.logs: \/var\/log\/opensearch/path.logs: \/var\/log\/opensearch/' /etc/opensearch/opensearch.yml
sudo sed -i 's/#network.host: 192.168.0.1/network.host: 0.0.0.0/' /etc/opensearch/opensearch.yml
sudo sed -i 's/#http.port: 9200/http.port: 9200/' /etc/opensearch/opensearch.yml
sudo sed -i 's/#discovery.type: single-node/discovery.type: single-node/' /etc/opensearch/opensearch.yml

# Set OpenSearch password
echo "🔐 Setting OpenSearch password..."
sudo /usr/share/opensearch/plugins/opensearch-security/tools/securityadmin.sh -cd /usr/share/opensearch/plugins/opensearch-security/securityconfig/ -icl -nhnv -cacert /usr/share/opensearch/config/root-ca.pem -cert /usr/share/opensearch/config/admin.pem -key /usr/share/opensearch/config/admin-key.pem -h localhost

# Create gateway user and directory
echo "👤 Creating gateway user..."
sudo useradd -m -s /bin/bash gateway || true
sudo mkdir -p /opt/ml-gateway
sudo chown gateway:gateway /opt/ml-gateway

# Clone or copy repository
echo "📁 Setting up application directory..."
# Assuming you're running this from the repository directory
sudo cp -r . /opt/ml-gateway/
sudo chown -R gateway:gateway /opt/ml-gateway

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd /opt/ml-gateway
sudo -u gateway python3.11 -m venv venv
sudo -u gateway bash -c "source venv/bin/activate && pip install --upgrade pip"
sudo -u gateway bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Create systemd services
echo "🔧 Creating systemd services..."

# OpenSearch service
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

# Start services
echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable opensearch
sudo systemctl enable ml-gateway
sudo systemctl start opensearch

# Wait for OpenSearch
echo "⏳ Waiting for OpenSearch to be ready..."
sleep 30
until curl -s http://localhost:9200/_cluster/health > /dev/null; do
  sleep 5
done

sudo systemctl start ml-gateway

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 8000/tcp
sudo ufw allow 9200/tcp
sudo ufw allow 5601/tcp  # Optional: OpenSearch Dashboards
sudo ufw --force enable

# Health check
echo "🏥 Running health checks..."
sleep 10

if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Gateway is running!"
    echo "🌐 Gateway URL: http://$(hostname -I | awk '{print $1}'):8000"
    echo "🔍 OpenSearch URL: http://$(hostname -I | awk '{print $1}'):9200"
    echo "👨‍💼 Admin Panel: http://$(hostname -I | awk '{print $1}'):8000/admin"
else
    echo "❌ Gateway health check failed"
fi

echo ""
echo "📋 Service Management:"
echo "sudo systemctl status opensearch"
echo "sudo systemctl status ml-gateway"
echo "sudo systemctl restart ml-gateway"
echo "sudo journalctl -u ml-gateway -f"
echo ""
echo "🎉 Deployment complete!"