#!/bin/bash

# Ubuntu Deployment Script for ML Gateway
# This script installs and configures the ML Gateway on Ubuntu

# Remove set -e to preve# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow 8000/tcp
sudo ufw allow 9200/tcp
sudo ufw allow 22/tcp
echo "y" | sudo ufw enable

# Health check
echo "🏥 Running health checks..."
sleep 10

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Gateway is running!"
    echo "🌐 Gateway URL: http://$SERVER_IP:8000"
    echo "🔍 OpenSearch URL: http://$SERVER_IP:9200"
    echo "👨‍💼 Admin Panel: http://$SERVER_IP:8000/admin"
else
    echo "❌ Gateway health check failed - checking service status..."
    sudo systemctl status ml-gateway --no-pager -l
fiors
# set -e

echo "🚀 ML Gateway Ubuntu Deployment"
echo "================================"

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip
echo "🐍 Installing Python..."
sudo apt install -y python3 python3-venv python3-dev python3-pip

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
sudo sed -i 's/#network.host: 192.168.0.1/network.host: 0.0.0.0/' /etc/opensearch/opensearch.yml
sudo sed -i 's/#http.port: 9200/http.port: 9200/' /etc/opensearch/opensearch.yml
sudo sed -i 's/#discovery.type: single-node/discovery.type: single-node/' /etc/opensearch/opensearch.yml

# Skip OpenSearch security setup for now (can be done later)
echo "🔐 Skipping OpenSearch security setup (will configure manually later)..."

# Create gateway user and directory
echo "👤 Creating gateway user..."
sudo useradd -m -s /bin/bash gateway || true
sudo mkdir -p /opt/ml-gateway
sudo chown -R gateway:gateway /opt/ml-gateway

# Clone or copy repository
echo "📁 Setting up application directory..."
# Check if we're in the repository directory
if [ -f "main.py" ] && [ -f "requirements.txt" ]; then
    echo "📋 Copying from current directory..."
    sudo cp -r . /opt/ml-gateway/
else
    echo "📋 Cloning repository..."
    sudo git clone https://github.com/pragyaa-ai/prediction-gateway.git /tmp/gateway-repo
    sudo cp -r /tmp/gateway-repo/* /opt/ml-gateway/
    sudo rm -rf /tmp/gateway-repo
fi
sudo chown -R gateway:gateway /opt/ml-gateway

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd /opt/ml-gateway
sudo -u gateway python3 -m venv venv
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

echo "🔄 Starting OpenSearch..."
sudo systemctl start opensearch

# Wait for OpenSearch
echo "⏳ Waiting for OpenSearch to be ready..."
sleep 30
for i in {1..10}; do
    if curl -s http://localhost:9200/_cluster/health > /dev/null; then
        echo "✅ OpenSearch is ready!"
        break
    fi
    echo "Waiting... ($i/10)"
    sleep 5
done

echo "🔄 Starting ML Gateway..."
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
    echo "� Dashboards URL: http://$(hostname -I | awk '{print $1}'):5601"
    echo "�👨‍💼 Admin Panel: http://$(hostname -I | awk '{print $1}'):8000/admin"
else
    echo "❌ Gateway health check failed"
fi

echo ""
echo "📋 Service Management:"
echo "sudo systemctl status opensearch"
echo "sudo systemctl status ml-gateway"
echo "sudo systemctl restart ml-gateway"
echo "sudo journalctl -u ml-gateway -f"
echo "sudo journalctl -u opensearch -f"
echo ""
echo "🔧 Troubleshooting:"
echo "sudo systemctl stop ml-gateway && sudo -u gateway bash -c 'cd /opt/ml-gateway && source venv/bin/activate && python3 main.py'"
echo ""
echo "🎉 Deployment complete!"