#!/usr/bin/env bash
# =============================================================================
#  ML Inference Gateway – Universal Linux Installer
#  Supports: Ubuntu/Debian, CentOS/RHEL/Rocky/AlmaLinux, Fedora, Amazon Linux
#  Usage:    bash install.sh [--port 8000] [--dir /opt/ml-gateway] [--no-opensearch]
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# ── Defaults ─────────────────────────────────────────────────────────────────
GATEWAY_DIR="/opt/ml-gateway"
GATEWAY_USER="mlgateway"
GATEWAY_PORT=8000
INSTALL_OPENSEARCH=true
REPO_SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }
step()    { echo -e "\n${BOLD}━━━  $*  ━━━${RESET}"; }

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)          GATEWAY_PORT="$2";   shift 2 ;;
        --dir)           GATEWAY_DIR="$2";    shift 2 ;;
        --no-opensearch) INSTALL_OPENSEARCH=false; shift ;;
        --help|-h)
            echo "Usage: bash install.sh [--port PORT] [--dir PATH] [--no-opensearch]"
            exit 0 ;;
        *) error "Unknown argument: $1"; exit 1 ;;
    esac
done

# ── Privilege check ───────────────────────────────────────────────────────────
if [[ "$EUID" -ne 0 ]]; then
    # Re-run with sudo if not root
    exec sudo bash "$0" "$@"
fi

# ── Sanity: must be run from the repo root ────────────────────────────────────
if [[ ! -f "$REPO_SOURCE_DIR/main.py" || ! -f "$REPO_SOURCE_DIR/requirements.txt" ]]; then
    error "Run this script from the prediction-gateway repository root."
    exit 1
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗"
echo -e "║    ML Inference Gateway  –  Linux Installer      ║"
echo -e "╚══════════════════════════════════════════════════╝${RESET}"
echo ""
info "Install dir  : $GATEWAY_DIR"
info "Gateway port : $GATEWAY_PORT"
info "OpenSearch   : $INSTALL_OPENSEARCH"
echo ""

# =============================================================================
# STEP 1 – Detect distro & package manager
# =============================================================================
step "1 / 8  Detecting Linux distribution"

PKG_MGR=""
DISTRO=""

if command -v apt-get &>/dev/null; then
    PKG_MGR="apt"
    DISTRO="debian"
elif command -v dnf &>/dev/null; then
    PKG_MGR="dnf"
    DISTRO="fedora"
elif command -v yum &>/dev/null; then
    PKG_MGR="yum"
    DISTRO="rhel"
else
    error "No supported package manager found (apt / dnf / yum)."
    exit 1
fi

# Grab a human-readable distro name
if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    DISTRO_NAME="${PRETTY_NAME:-$ID}"
else
    DISTRO_NAME="Unknown"
fi

success "Detected: $DISTRO_NAME  (pkg: $PKG_MGR)"

# =============================================================================
# STEP 2 – Install system packages
# =============================================================================
step "2 / 8  Installing system packages"

install_packages() {
    case "$PKG_MGR" in
        apt)
            apt-get update -y -qq
            DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
                curl wget gnupg2 ca-certificates software-properties-common \
                python3 python3-venv python3-dev python3-pip \
                build-essential libgomp1 git git-lfs rsync ;;
        dnf|yum)
            $PKG_MGR install -y -q \
                curl wget gnupg2 ca-certificates \
                python3 python3-devel \
                gcc gcc-c++ make libgomp git rsync

            # pip may not come with python3 on older RHEL/CentOS
            if ! command -v pip3 &>/dev/null; then
                python3 -m ensurepip --upgrade 2>/dev/null || \
                    $PKG_MGR install -y python3-pip
            fi ;;
    esac
}

install_packages
success "System packages ready."

# Python 3.9 for AutoGluon no-show (gateway venv uses system python3 / 3.12)
ensure_python39() {
    if command -v python3.9 &>/dev/null; then
        success "Python 3.9 available for AutoGluon."
        return 0
    fi
    if [[ "$PKG_MGR" == "apt" ]]; then
        info "Installing Python 3.9 (AutoGluon no-show model)..."
        add-apt-repository -y ppa:deadsnakes/ppa
        apt-get update -y -qq
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
            python3.9 python3.9-venv python3.9-dev
        success "Python 3.9 installed."
    else
        warn "python3.9 not found — install manually for no_show_fakeeh_ksa_local."
    fi
}
ensure_python39

# Ensure we have a recent-enough Python (≥ 3.9)
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [[ "$PY_MAJOR" -lt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 9 ) ]]; then
    error "Python $PY_VERSION detected, but >= 3.9 is required."
    error "Please upgrade Python and re-run this script."
    exit 1
fi
success "Python $PY_VERSION OK."

# =============================================================================
# STEP 3 – Create user & deploy application files
# =============================================================================
step "3 / 9  Deploying application"

# Pull LFS model artifacts when installing from a git clone
if [[ -d "$REPO_SOURCE_DIR/.git" ]] && command -v git-lfs &>/dev/null; then
    info "Pulling Git LFS models (required for no-show + delay)..."
    git lfs install --local 2>/dev/null || true
    (cd "$REPO_SOURCE_DIR" && git lfs pull)
fi

if [[ -d "$REPO_SOURCE_DIR/models/local-models/new-noshow-ksa" ]]; then
    if [[ ! -f "$REPO_SOURCE_DIR/models/local-models/new-noshow-ksa/learner.pkl" ]] \
        || head -c 20 "$REPO_SOURCE_DIR/models/local-models/new-noshow-ksa/learner.pkl" 2>/dev/null | grep -q "git-lfs"; then
        warn "Model files look like LFS pointers — run: git lfs pull"
    fi
fi

# Create a dedicated system user (no login shell)
if ! id "$GATEWAY_USER" &>/dev/null; then
    useradd -r -m -d "$GATEWAY_DIR" -s /sbin/nologin "$GATEWAY_USER"
    info "Created user: $GATEWAY_USER"
fi

mkdir -p "$GATEWAY_DIR"

info "Syncing repository to $GATEWAY_DIR ..."
rsync -a --delete \
    --exclude='.git' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    "$REPO_SOURCE_DIR/" "$GATEWAY_DIR/"

# Ensure local-models directory exists (models are in the repo already)
mkdir -p "$GATEWAY_DIR/models/local-models"
mkdir -p "$GATEWAY_DIR/logs"

chown -R "$GATEWAY_USER:$GATEWAY_USER" "$GATEWAY_DIR"
success "Application files deployed."

# =============================================================================
# STEP 4 – Gateway virtual environment (Python 3.12+)
# =============================================================================
step "4 / 9  Installing gateway Python dependencies"

VENV="$GATEWAY_DIR/venv"

sudo -u "$GATEWAY_USER" python3 -m venv "$VENV"

info "Upgrading pip, wheel, setuptools..."
sudo -u "$GATEWAY_USER" "$VENV/bin/pip" install --upgrade pip wheel setuptools -q

info "Installing requirements.txt (this may take 1-2 minutes for numpy/xgboost)..."
sudo -u "$GATEWAY_USER" "$VENV/bin/pip" install -r "$GATEWAY_DIR/requirements.txt"

success "Gateway venv ready."

# =============================================================================
# STEP 5 – AutoGluon virtual environment (Python 3.9, no-show model)
# =============================================================================
step "5 / 9  Installing AutoGluon environment (no-show KSA)"

AG_VENV="$GATEWAY_DIR/venv-autogluon"
if command -v python3.9 &>/dev/null && [[ -f "$GATEWAY_DIR/requirements-autogluon.txt" ]]; then
    rm -rf "$AG_VENV"
    sudo -u "$GATEWAY_USER" python3.9 -m venv "$AG_VENV"
    info "Installing requirements-autogluon.txt (may take several minutes)..."
    sudo -u "$GATEWAY_USER" "$AG_VENV/bin/pip" install --upgrade pip wheel setuptools -q
    sudo -u "$GATEWAY_USER" "$AG_VENV/bin/pip" install -r "$GATEWAY_DIR/requirements-autogluon.txt"
    success "AutoGluon venv: $AG_VENV"
else
    warn "Skipped AutoGluon venv — python3.9 or requirements-autogluon.txt missing."
fi

# =============================================================================
# STEP 6 – Environment file
# =============================================================================
step "6 / 9  Configuring environment"

ENV_FILE="$GATEWAY_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$REPO_SOURCE_DIR/.env" ]]; then
        cp "$REPO_SOURCE_DIR/.env" "$ENV_FILE"
        info "Copied existing .env from repository."
    else
        cp "$GATEWAY_DIR/.env.example" "$ENV_FILE"
        warn ".env created from template – review $ENV_FILE before production use."
    fi
    chown "$GATEWAY_USER:$GATEWAY_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
else
    info ".env already exists – skipping."
fi

# Always set paths for local KSA models + AutoGluon python
set_env_var() {
    local key="$1" val="$2"
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}
if [[ -x "$AG_VENV/bin/python" ]]; then
    set_env_var "AUTOGUON_PYTHON" "$AG_VENV/bin/python"
fi
set_env_var "LOCAL_MODELS_DIR" "$GATEWAY_DIR/models/local-models"
chown "$GATEWAY_USER:$GATEWAY_USER" "$ENV_FILE"
chmod 600 "$ENV_FILE"

success "Environment configured."

# =============================================================================
# STEP 7 – Model smoke-test (non-fatal)
# =============================================================================
step "7 / 9  Model smoke-test"

sudo -u "$GATEWAY_USER" bash -c "
    cd $GATEWAY_DIR
    $VENV/bin/python3 -c \"
import sys, traceback
sys.path.insert(0, '.')
try:
    from models.registry import ModelRegistry
    r = ModelRegistry()
    enabled = [n for n, m in r.list_models().items() if m.enabled]
    print('    Enabled models:', enabled)
    print('    Registry OK.')
except Exception as e:
    print('    WARNING:', e)
    traceback.print_exc()
\"
" && success "Registry loaded." || warn "Smoke-test raised an error (gateway may still start)."

# =============================================================================
# STEP 8 – systemd service
# =============================================================================
step "8 / 9  Creating systemd service"

SYSTEMD_UNIT=/etc/systemd/system/ml-gateway.service

cat > "$SYSTEMD_UNIT" <<EOF
[Unit]
Description=ML Inference Gateway
Documentation=https://github.com/pragyaa-ai/prediction-gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$GATEWAY_USER
Group=$GATEWAY_USER
WorkingDirectory=$GATEWAY_DIR
EnvironmentFile=-$ENV_FILE

# Fallback environment (overridden by .env)
Environment=GATEWAY_HOST=0.0.0.0
Environment=GATEWAY_PORT=$GATEWAY_PORT
Environment=PYTHONUNBUFFERED=1
Environment=LOCAL_MODELS_DIR=$GATEWAY_DIR/models/local-models
EOF

if [[ -x "$AG_VENV/bin/python" ]]; then
    cat >> "$SYSTEMD_UNIT" <<EOF
Environment=AUTOGUON_PYTHON=$AG_VENV/bin/python
EOF
fi

cat >> "$SYSTEMD_UNIT" <<EOF

ExecStart=$VENV/bin/uvicorn main:app \\
    --host 0.0.0.0 \\
    --port $GATEWAY_PORT \\
    --workers 2 \\
    --log-level info \\
    --access-log

Restart=always
RestartSec=10
TimeoutStartSec=120

StandardOutput=journal
StandardError=journal
SyslogIdentifier=ml-gateway

# Enough file descriptors for model files and connections
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ml-gateway
success "Systemd service installed and enabled."

# =============================================================================
# STEP 9 – Firewall & launch
# =============================================================================
step "9 / 9  Firewall & launch"

# ufw (Debian/Ubuntu)
if command -v ufw &>/dev/null; then
    ufw allow 22/tcp   comment "SSH"    2>/dev/null || true
    ufw allow "$GATEWAY_PORT/tcp" comment "ML Gateway" 2>/dev/null || true
    echo "y" | ufw enable 2>/dev/null || true
    success "ufw configured."
# firewalld (RHEL/CentOS/Fedora)
elif command -v firewall-cmd &>/dev/null && systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-port="$GATEWAY_PORT/tcp"
    firewall-cmd --permanent --add-service=ssh
    firewall-cmd --reload
    success "firewalld configured."
else
    warn "No active firewall manager detected – you may need to open port $GATEWAY_PORT manually."
fi

info "Starting ml-gateway service..."
systemctl start ml-gateway

echo ""
info "Waiting for gateway to become healthy (up to 120 s)..."
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
for i in $(seq 1 24); do
    if curl -sf "http://localhost:$GATEWAY_PORT/health" > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}${BOLD}"
        echo "╔══════════════════════════════════════════════════╗"
        echo "║           Deployment successful!                 ║"
        echo "╚══════════════════════════════════════════════════╝"
        echo -e "${RESET}"
        echo -e "  ${BOLD}Gateway API ${RESET}: http://$SERVER_IP:$GATEWAY_PORT"
        echo -e "  ${BOLD}Health     ${RESET}: http://$SERVER_IP:$GATEWAY_PORT/health"
        echo -e "  ${BOLD}API Docs   ${RESET}: http://$SERVER_IP:$GATEWAY_PORT/docs"
        echo -e "  ${BOLD}Admin UI   ${RESET}: http://$SERVER_IP:$GATEWAY_PORT/admin"
        echo ""
        echo "  Management commands:"
        echo "    sudo systemctl status  ml-gateway"
        echo "    sudo systemctl restart ml-gateway"
        echo "    sudo journalctl -u ml-gateway -f"
        echo "    sudo journalctl -u ml-gateway --since '10 min ago'"
        echo ""
        echo "  To update after git pull:"
        echo "    git lfs pull"
        echo "    sudo bash scripts/update-ksa-models.sh --dir $GATEWAY_DIR"
        echo ""
        exit 0
    fi
    echo -e "  ${YELLOW}($((i * 5))s)${RESET} not ready yet..."
    sleep 5
done

# If we reach here, something went wrong
echo ""
error "Gateway did not become healthy within 120 s."
echo ""
echo "Check logs:"
echo "  sudo journalctl -u ml-gateway -n 100 --no-pager"
echo ""
systemctl status ml-gateway --no-pager -l || true
exit 1
