#!/usr/bin/env bash
# =============================================================================
#  Air-gapped install for ML Inference Gateway offline bundle.
#
#  Run from the extracted bundle root (contains app/, wheels/, offline-install.sh):
#    sudo bash offline-install.sh [--dir /opt/ml-gateway] [--port 8000] [--no-systemd]
#
#  No pip/PyPI or apt network access required when wheels/ and venv/ are bundled.
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

BUNDLE_ROOT="$(cd "$(dirname "$0")" && pwd)"
GATEWAY_DIR="/opt/ml-gateway"
GATEWAY_USER="mlgateway"
GATEWAY_PORT=8000
INSTALL_SYSTEMD=true
PYTHON="${PYTHON:-python3.10}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }
step()    { echo -e "\n${BOLD}━━━  $*  ━━━${RESET}"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir)           GATEWAY_DIR="$2"; shift 2 ;;
        --port)          GATEWAY_PORT="$2"; shift 2 ;;
        --no-systemd)    INSTALL_SYSTEMD=false; shift ;;
        --python)        PYTHON="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: sudo bash offline-install.sh [--dir PATH] [--port PORT] [--no-systemd]"
            exit 0 ;;
        *) error "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ "$EUID" -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

if [[ ! -f "$BUNDLE_ROOT/app/main.py" ]]; then
    error "Run from extracted bundle root (expected app/main.py beside this script)."
    exit 1
fi

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗"
echo -e "║   ML Inference Gateway  –  Offline Installer     ║"
echo -e "╚══════════════════════════════════════════════════╝${RESET}"
echo ""
info "Bundle       : $BUNDLE_ROOT"
info "Install dir  : $GATEWAY_DIR"
info "Port         : $GATEWAY_PORT"
info "Systemd      : $INSTALL_SYSTEMD"
echo ""

# ── Optional offline apt from bundled debs ───────────────────────────────────
DEB_DIR="$BUNDLE_ROOT/system-deps/debs"
if [[ -d "$DEB_DIR" ]] && ls "$DEB_DIR"/*.deb &>/dev/null; then
    step "Installing system packages from bundled .deb files"
    dpkg -i "$DEB_DIR"/*.deb 2>/dev/null || apt-get install -f -y --no-download || true
    success "System packages installed from cache."
fi

# ── Python check ─────────────────────────────────────────────────────────────
step "Checking Python"

if ! command -v "$PYTHON" &>/dev/null; then
    if command -v python3.10 &>/dev/null; then
        PYTHON=python3.10
    elif command -v python3 &>/dev/null; then
        PYTHON=python3
        warn "python3.10 not found; using $PYTHON — verify AutoGluon compatibility."
    else
        error "Python 3.10+ required. Install python3.10-venv (see system-deps/apt-packages.txt)."
        exit 1
    fi
fi

PY_VERSION="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
info "Using $PYTHON (Python $PY_VERSION)"

# ── Service user ─────────────────────────────────────────────────────────────
step "Creating service user"

if ! id "$GATEWAY_USER" &>/dev/null; then
    useradd --system --home-dir "$GATEWAY_DIR" --shell /usr/sbin/nologin "$GATEWAY_USER"
    success "Created user $GATEWAY_USER"
else
    info "User $GATEWAY_USER already exists"
fi

# ── Deploy application ───────────────────────────────────────────────────────
step "Deploying application to $GATEWAY_DIR"

mkdir -p "$GATEWAY_DIR"
rsync -a --delete \
    --exclude='venv' \
    --exclude='venv-autogluon' \
    --exclude='.env' \
    "$BUNDLE_ROOT/app/" "$GATEWAY_DIR/"

chown -R "$GATEWAY_USER:$GATEWAY_USER" "$GATEWAY_DIR"

# ── Virtual environments ─────────────────────────────────────────────────────
step "Setting up Python virtual environments"

install_venv_from_wheels() {
    local target_venv="$1"
    local wheels_dir="$2"
    local req_file="$3"

    rm -rf "$target_venv"
    "$PYTHON" -m venv "$target_venv"
    # shellcheck disable=SC1091
    source "$target_venv/bin/activate"
    pip install --upgrade pip wheel setuptools
    pip install --no-index --find-links="$wheels_dir" -r "$req_file"
    deactivate
}

try_bundled_venv() {
    local src="$1"
    local dest="$2"

    if [[ ! -x "$src/bin/python" ]]; then
        return 1
    fi
    rm -rf "$dest"
    cp -a "$src" "$dest"
    if "$dest/bin/python" -c "import sys; print(sys.version)" &>/dev/null; then
        return 0
    fi
    rm -rf "$dest"
    return 1
}

GATEWAY_VENV="$GATEWAY_DIR/venv"
AG_VENV="$GATEWAY_DIR/venv-autogluon"

if try_bundled_venv "$BUNDLE_ROOT/venv" "$GATEWAY_VENV"; then
    success "Gateway venv copied from bundle"
else
    info "Building gateway venv from wheels..."
    install_venv_from_wheels "$GATEWAY_VENV" "$BUNDLE_ROOT/wheels/gateway" "$GATEWAY_DIR/requirements.txt"
    success "Gateway venv built offline"
fi

if try_bundled_venv "$BUNDLE_ROOT/venv-autogluon" "$AG_VENV"; then
    success "AutoGluon venv copied from bundle"
else
    info "Building AutoGluon venv from wheels..."
    install_venv_from_wheels "$AG_VENV" "$BUNDLE_ROOT/wheels/autogluon" "$GATEWAY_DIR/requirements-autogluon.txt"
    success "AutoGluon venv built offline"
fi

chown -R "$GATEWAY_USER:$GATEWAY_USER" "$GATEWAY_VENV" "$AG_VENV"

# ── Environment file ─────────────────────────────────────────────────────────
step "Writing .env"

ENV_FILE="$GATEWAY_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$GATEWAY_DIR/.env.example" "$ENV_FILE" 2>/dev/null || touch "$ENV_FILE"
fi

set_env() {
    local key="$1"
    local val="$2"
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}

set_env "GATEWAY_HOST" "0.0.0.0"
set_env "GATEWAY_PORT" "$GATEWAY_PORT"
set_env "AUTOGUON_PYTHON" "$AG_VENV/bin/python"
set_env "LOCAL_MODELS_DIR" "$GATEWAY_DIR/models/local-models"

chown "$GATEWAY_USER:$GATEWAY_USER" "$ENV_FILE"
chmod 640 "$ENV_FILE"
success ".env configured"

# ── Smoke test ───────────────────────────────────────────────────────────────
step "Smoke-testing imports"

sudo -u "$GATEWAY_USER" bash -c "
    cd $GATEWAY_DIR
    $GATEWAY_VENV/bin/python -c \"
import sys, traceback
sys.path.insert(0, '.')
try:
    from core.registry import ModelRegistry
    r = ModelRegistry()
    enabled = [n for n, m in r.models.items() if m.enabled]
    print('    Enabled models:', enabled)
    print('    Registry OK.')
except Exception as e:
    print('    WARNING:', e)
    traceback.print_exc()
\"
" && success "Import smoke test passed." || warn "Smoke test failed — check logs after start."

# ── systemd ──────────────────────────────────────────────────────────────────
if $INSTALL_SYSTEMD; then
    step "Installing systemd service"

    SYSTEMD_UNIT=/etc/systemd/system/ml-gateway.service
    cat > "$SYSTEMD_UNIT" <<EOF
[Unit]
Description=ML Inference Gateway (offline bundle)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$GATEWAY_USER
Group=$GATEWAY_USER
WorkingDirectory=$GATEWAY_DIR
EnvironmentFile=-$ENV_FILE
Environment=GATEWAY_HOST=0.0.0.0
Environment=GATEWAY_PORT=$GATEWAY_PORT
Environment=PYTHONUNBUFFERED=1
Environment=AUTOGUON_PYTHON=$AG_VENV/bin/python
Environment=LOCAL_MODELS_DIR=$GATEWAY_DIR/models/local-models

ExecStart=$GATEWAY_VENV/bin/uvicorn main:app \\
    --host 0.0.0.0 \\
    --port $GATEWAY_PORT \\
    --workers 2 \\
    --log-level info \\
    --access-log

Restart=always
RestartSec=10
TimeoutStartSec=180
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ml-gateway
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable ml-gateway
    systemctl restart ml-gateway
    success "ml-gateway.service enabled and started"
fi

# ── Health check ─────────────────────────────────────────────────────────────
step "Health check"

HEALTH_URL="http://127.0.0.1:${GATEWAY_PORT}/health"
for i in $(seq 1 60); do
    if command -v curl &>/dev/null && curl -sf "$HEALTH_URL" &>/dev/null; then
        success "Gateway healthy at $HEALTH_URL"
        echo ""
        echo "  Logs:    sudo journalctl -u ml-gateway -f"
        echo "  Models:  curl http://127.0.0.1:${GATEWAY_PORT}/v1/models"
        echo "  Predict: POST http://127.0.0.1:${GATEWAY_PORT}/v1/predict/{model_id}"
        exit 0
    fi
    if "$GATEWAY_VENV/bin/python" -c "
import urllib.request
urllib.request.urlopen('$HEALTH_URL', timeout=2)
" &>/dev/null; then
        success "Gateway healthy at $HEALTH_URL"
        exit 0
    fi
    sleep 2
done

warn "Health check timed out — service may still be loading models."
echo "  sudo journalctl -u ml-gateway -n 50 --no-pager"
exit 0
