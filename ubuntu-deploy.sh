#!/bin/bash
# Ubuntu Deployment Script for ML Inference Gateway
# Run as a user with sudo privileges on a fresh Ubuntu 22.04+ VM.
# Usage: bash ubuntu-deploy.sh

set -euo pipefail

GATEWAY_DIR="/opt/ml-gateway"
GATEWAY_USER="gateway"
APP_PORT=8000

echo "=============================================="
echo " ML Inference Gateway - Ubuntu Deploy Script"
echo "=============================================="
echo ""

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
echo "[1/8] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y \
    curl wget gnupg software-properties-common \
    python3 python3-venv python3-dev python3-pip \
    build-essential libgomp1 git

# ---------------------------------------------------------------------------
# 2. Create dedicated user and app directory
# ---------------------------------------------------------------------------
echo "[2/8] Creating gateway user and directory..."
sudo useradd -r -m -s /bin/bash "$GATEWAY_USER" 2>/dev/null || true
sudo mkdir -p "$GATEWAY_DIR"

# Copy the repository to the deployment directory
if [ -f "main.py" ] && [ -f "requirements.txt" ]; then
    echo "    Syncing from current directory..."
    sudo rsync -a --delete \
        --exclude='.git' \
        --exclude='venv' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        . "$GATEWAY_DIR/"
else
    echo "ERROR: Run this script from inside the prediction-gateway repository root."
    exit 1
fi

sudo chown -R "$GATEWAY_USER:$GATEWAY_USER" "$GATEWAY_DIR"

# ---------------------------------------------------------------------------
# 3. Python virtual environment + dependencies
# ---------------------------------------------------------------------------
echo "[3/8] Installing Python dependencies..."
sudo -u "$GATEWAY_USER" python3 -m venv "$GATEWAY_DIR/venv"
sudo -u "$GATEWAY_USER" bash -c "
    source $GATEWAY_DIR/venv/bin/activate
    pip install --upgrade pip wheel
    pip install -r $GATEWAY_DIR/requirements.txt
"
echo "    Dependencies installed."

# ---------------------------------------------------------------------------
# 4. Environment file
# ---------------------------------------------------------------------------
echo "[4/8] Setting up environment file..."
if [ ! -f "$GATEWAY_DIR/.env" ]; then
    sudo -u "$GATEWAY_USER" cp "$GATEWAY_DIR/.env.example" "$GATEWAY_DIR/.env"
    echo "    Created .env from template. Edit $GATEWAY_DIR/.env to set credentials."
else
    echo "    .env already exists – skipping."
fi

# ---------------------------------------------------------------------------
# 5. Smoke-test model loading (optional, non-fatal)
# ---------------------------------------------------------------------------
echo "[5/8] Running model smoke-test (non-fatal)..."
sudo -u "$GATEWAY_USER" bash -c "
    source $GATEWAY_DIR/venv/bin/activate
    cd $GATEWAY_DIR
    python3 -c \"
import sys, traceback
sys.path.insert(0, '.')
try:
    from core.registry import ModelRegistry
    r = ModelRegistry()
    print('    ModelRegistry initialised – models YAML loaded OK.')
except Exception as e:
    print('    WARNING: smoke-test raised:', e)
    traceback.print_exc()
\"
" || true

# ---------------------------------------------------------------------------
# 6. systemd service (gateway only – OpenSearch is optional)
# ---------------------------------------------------------------------------
echo "[6/8] Creating systemd service..."

sudo tee /etc/systemd/system/ml-gateway.service > /dev/null <<EOF
[Unit]
Description=ML Inference Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$GATEWAY_USER
Group=$GATEWAY_USER
WorkingDirectory=$GATEWAY_DIR
EnvironmentFile=-$GATEWAY_DIR/.env

# Default env vars – overridden by .env when present
Environment=GATEWAY_HOST=0.0.0.0
Environment=GATEWAY_PORT=$APP_PORT
Environment=PYTHONUNBUFFERED=1

# Give enough time for local models to load before uvicorn starts accepting
# (azure_automl_pickle deserialization can take 20-40s on first request)
ExecStartPre=/bin/sleep 2
ExecStart=$GATEWAY_DIR/venv/bin/uvicorn main:app \
    --host 0.0.0.0 \
    --port $APP_PORT \
    --workers 2 \
    --log-level info \
    --access-log

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ml-gateway

# Allow enough open file descriptors for model files
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ml-gateway

# ---------------------------------------------------------------------------
# 7. Firewall
# ---------------------------------------------------------------------------
echo "[7/8] Configuring firewall..."
# Allow SSH so we don't lock ourselves out
sudo ufw allow 22/tcp
sudo ufw allow "$APP_PORT/tcp"
# Enable non-interactively
echo "y" | sudo ufw enable || true
sudo ufw status

# ---------------------------------------------------------------------------
# 8. Start and health-check
# ---------------------------------------------------------------------------
echo "[8/8] Starting ml-gateway service..."
sudo systemctl start ml-gateway

echo ""
echo "Waiting for gateway to become healthy (up to 90 s)..."
SERVER_IP=$(hostname -I | awk '{print $1}')
for i in $(seq 1 18); do
    if curl -sf "http://localhost:$APP_PORT/health" > /dev/null 2>&1; then
        echo ""
        echo "=============================================="
        echo " Deployment successful!"
        echo "=============================================="
        echo " Gateway API  : http://$SERVER_IP:$APP_PORT"
        echo " Health check : http://$SERVER_IP:$APP_PORT/health"
        echo " API docs     : http://$SERVER_IP:$APP_PORT/docs"
        echo " Admin UI     : http://$SERVER_IP:$APP_PORT/admin"
        echo "=============================================="
        echo ""
        echo "Useful commands:"
        echo "  sudo systemctl status  ml-gateway"
        echo "  sudo systemctl restart ml-gateway"
        echo "  sudo journalctl -u ml-gateway -f"
        echo "  sudo journalctl -u ml-gateway --since '5 min ago'"
        echo ""
        echo "To update the app:"
        echo "  1. rsync your new code to $GATEWAY_DIR"
        echo "  2. sudo systemctl restart ml-gateway"
        exit 0
    fi
    echo "  ($((i * 5))s) not ready yet..."
    sleep 5
done

echo ""
echo "WARNING: Health check did not pass within 90 s."
echo "Check logs with: sudo journalctl -u ml-gateway -n 100 --no-pager"
sudo systemctl status ml-gateway --no-pager -l || true
exit 1
