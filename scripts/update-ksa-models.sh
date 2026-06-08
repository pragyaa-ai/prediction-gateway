#!/usr/bin/env bash
# =============================================================================
#  KSA model update — run from cloned GitHub repo (git pull + git lfs pull first).
#
#    cd prediction-gateway
#    git lfs pull
#    sudo bash scripts/update-ksa-models.sh
#
#  Updates no_show_fakeeh_ksa_local + delay_fakeeh_ksa_local on /opt/ml-gateway.
#  Keeps existing gateway venv; creates venv-autogluon (Python 3.9) for no-show.
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Default source = repo root when script lives in scripts/
if [[ -f "$SCRIPT_DIR/../main.py" ]]; then
    SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    SOURCE_DIR="$SCRIPT_DIR"
fi
GATEWAY_DIR="/opt/ml-gateway"
GATEWAY_USER="mlgateway"
SKIP_RESTART=false

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }
step()    { echo -e "\n${BOLD}━━━  $*  ━━━${RESET}"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir)          GATEWAY_DIR="$2"; shift 2 ;;
        --source)       SOURCE_DIR="$2"; shift 2 ;;
        --no-restart)   SKIP_RESTART=true; shift ;;
        --help|-h)
            echo "Usage: sudo bash update-ksa-models.sh [--dir /opt/ml-gateway] [--source PATH]"
            exit 0 ;;
        *) error "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ "$EUID" -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

if [[ ! -d "$GATEWAY_DIR" || ! -f "$GATEWAY_DIR/main.py" ]]; then
    error "Gateway not found at $GATEWAY_DIR"
    exit 1
fi

if [[ ! -f "$SOURCE_DIR/config/models.yaml" ]]; then
    error "Run from prediction-gateway repo (or pass --source /path/to/repo)"
    exit 1
fi

if [[ ! -d "$SOURCE_DIR/models/local-models/new-noshow-ksa" ]]; then
    warn "new-noshow-ksa missing — run: git lfs pull"
fi

echo ""
echo -e "${BOLD}KSA model update (in-place) → $GATEWAY_DIR${RESET}"
info "Source: $SOURCE_DIR"
echo ""

# ── Locate existing gateway venv (from deploy or systemd) ─────────────────────
detect_gateway_venv() {
    local candidate="$GATEWAY_DIR/venv"
    if [[ -x "$candidate/bin/python" ]]; then
        echo "$candidate"
        return 0
    fi
    local unit="/etc/systemd/system/ml-gateway.service"
    if [[ -f "$unit" ]]; then
        local uvicorn_path
        uvicorn_path="$(grep -oE 'ExecStart=[^ ]+/uvicorn' "$unit" | head -1 | sed 's|ExecStart=||;s|/uvicorn||')"
        if [[ -n "$uvicorn_path" && -x "${uvicorn_path}/python" ]]; then
            echo "$uvicorn_path"
            return 0
        fi
    fi
    return 1
}

GATEWAY_VENV="$(detect_gateway_venv)" || {
    error "Existing gateway venv not found under $GATEWAY_DIR/venv"
    error "This script patches an existing deployment — it does not create a new one."
    exit 1
}

GATEWAY_PY="$GATEWAY_VENV/bin/python"
info "Keeping existing gateway venv: $GATEWAY_VENV"
info "  Python: $($GATEWAY_PY --version 2>&1)"

# Base python used to create the old venv (for spawning autogluon sibling venv)
BASE_PYTHON="$GATEWAY_PY"
if [[ -f "$GATEWAY_VENV/pyvenv.cfg" ]]; then
    cfg_home="$(grep '^home = ' "$GATEWAY_VENV/pyvenv.cfg" | cut -d= -f2- | tr -d ' ')"
    if [[ -n "$cfg_home" && -x "$cfg_home/bin/python3" ]]; then
        BASE_PYTHON="$cfg_home/bin/python3"
    elif [[ -n "$cfg_home" && -x "$cfg_home/python3" ]]; then
        BASE_PYTHON="$cfg_home/python3"
    fi
fi

pip_in_venv() {
    local venv_py="$1"
    local wheels_dir="$2"
    shift 2
    if [[ -d "$wheels_dir" ]] && ls "$wheels_dir"/* &>/dev/null 2>&1; then
        "$venv_py" -m pip install --no-index --find-links="$wheels_dir" "$@"
    else
        warn "No wheels at $wheels_dir — pip needs network"
        "$venv_py" -m pip install "$@"
    fi
}

venv_has_module() {
    local venv_py="$1"
    local module="$2"
    "$venv_py" -c "import $module" 2>/dev/null
}

find_autogluon_python() {
    # 1. .env AUTOGUON_PYTHON if already set and working
    local env_file="$GATEWAY_DIR/.env"
    if [[ -f "$env_file" ]]; then
        local configured
        configured="$(grep -E '^(AUTOGLUON_PYTHON|AUTOGUON_PYTHON)=' "$env_file" | head -1 | cut -d= -f2- | tr -d ' \"')"
        if [[ -n "$configured" && -x "$configured" ]] && venv_has_module "$configured" autogluon.tabular; then
            echo "$configured"
            return 0
        fi
    fi
    # 2. Common sibling venvs from prior deploys
    local candidate
    for candidate in \
        "$GATEWAY_DIR/venv-autogluon/bin/python" \
        "$GATEWAY_DIR/venv39/bin/python"; do
        if [[ -x "$candidate" ]] && venv_has_module "$candidate" autogluon.tabular; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

# ── 1. Patch code (never touch venv/) ────────────────────────────────────────
step "1 / 6  Patching application code (venv/ untouched)"

PATCH_PATHS=(
    config
    models/schemas.py
    models/registry.py
    adapters
    scripts/autogluon_noshow_infer.py
    requirements-autogluon.txt
)

for rel in "${PATCH_PATHS[@]}"; do
    if [[ -e "$SOURCE_DIR/$rel" ]]; then
        rsync -a "$SOURCE_DIR/$rel" "$GATEWAY_DIR/$(dirname "$rel")/"
        info "  synced $rel"
    fi
done

# Merge models.yaml — only update the two KSA local model blocks if user had custom edits?
# For simplicity rsync config/ already done above.

chown -R "$GATEWAY_USER:$GATEWAY_USER" \
    "$GATEWAY_DIR/config" "$GATEWAY_DIR/models" \
    "$GATEWAY_DIR/adapters" "$GATEWAY_DIR/scripts" 2>/dev/null || true

# ── 2. Model artifacts ───────────────────────────────────────────────────────
step "2 / 6  Deploying model artifacts"

MODELS_BASE="$GATEWAY_DIR/models/local-models"
mkdir -p "$MODELS_BASE"

for dir in new-noshow-ksa Fakeeh-Delay-Arrival_ksa; do
    src="$SOURCE_DIR/models/local-models/$dir"
    if [[ ! -d "$src" ]]; then
        warn "Missing $dir in update pack — skipping"
        continue
    fi
    dest="$MODELS_BASE/$dir"
    if [[ -d "$dest" ]]; then
        backup="${dest}.bak.$(date +%Y%m%d%H%M%S)"
        info "  backup $dir → $(basename "$backup")"
        mv "$dest" "$backup"
    fi
    rsync -a "$src/" "$dest/"
    chown -R "$GATEWAY_USER:$GATEWAY_USER" "$dest"
    success "  $dir deployed"
done

# ── 3. Existing venv — add lightgbm only if missing ─────────────────────────
step "3 / 6  Patching existing gateway venv (add lightgbm if needed)"

GW_WHEELS="$SOURCE_DIR/wheels/gateway"

if venv_has_module "$GATEWAY_PY" lightgbm; then
    success "lightgbm already in gateway venv — no pip changes"
else
    info "Installing lightgbm into existing venv (--no-deps, delay model)..."
    if [[ -d "$GW_WHEELS" ]]; then
        pip_in_venv "$GATEWAY_PY" "$GW_WHEELS" --no-deps lightgbm
    else
        pip_in_venv "$GATEWAY_PY" "" --no-deps lightgbm
    fi
    venv_has_module "$GATEWAY_PY" lightgbm \
        && success "lightgbm installed" \
        || warn "lightgbm install failed — delay model may not load"
fi

find_bundled_python39() {
    local candidate
    for candidate in \
        "$SOURCE_DIR/runtime/python39/bin/python3.9" \
        "$SOURCE_DIR/runtime/python39/bin/python3" \
        "$GATEWAY_DIR/runtime/python39/bin/python3.9"; do
        if [[ -x "$candidate" ]]; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

ensure_python39() {
    if command -v python3.9 &>/dev/null; then
        echo python3.9
        return 0
    fi
    info "Installing python3.9 (AutoGluon requires 3.9, gateway stays on 3.12)..."
    apt-get update -qq
    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y python3.9 python3.9-venv python3.9-dev
    echo python3.9
}

install_autogluon_venv() {
    local ag_venv="$GATEWAY_DIR/venv-autogluon"
    local ag_wheels="$SOURCE_DIR/wheels/autogluon"
    local req="$SOURCE_DIR/requirements-autogluon.txt"
    local py39 bundled_py

    [[ -f "$req" ]] || { error "Missing $req"; exit 1; }
    cp "$req" "$GATEWAY_DIR/requirements-autogluon.txt"

    if bundled_py="$(find_bundled_python39 2>/dev/null)"; then
        info "Using bundled Python 3.9 from runtime/python39/"
        mkdir -p "$GATEWAY_DIR/runtime"
        rsync -a "$SOURCE_DIR/runtime/python39/" "$GATEWAY_DIR/runtime/python39/"
        py39="$GATEWAY_DIR/runtime/python39/bin/python3.9"
        [[ -x "$py39" ]] || py39="$GATEWAY_DIR/runtime/python39/bin/python3"
    else
        py39="$(ensure_python39)"
    fi

    rm -rf "$ag_venv"
    info "Creating venv-autogluon..."
    "$py39" -m venv "$ag_venv"
    AG_PY="$ag_venv/bin/python"
    "$AG_PY" -m pip install --upgrade pip
    if [[ -d "$ag_wheels" ]] && ls "$ag_wheels"/* &>/dev/null 2>&1; then
        pip_in_venv "$AG_PY" "$ag_wheels" -r "$GATEWAY_DIR/requirements-autogluon.txt"
    else
        pip_in_venv "$AG_PY" "" -r "$GATEWAY_DIR/requirements-autogluon.txt"
    fi
    chown -R "$GATEWAY_USER:$GATEWAY_USER" "$ag_venv" "$GATEWAY_DIR/runtime" 2>/dev/null || \
        chown -R "$GATEWAY_USER:$GATEWAY_USER" "$ag_venv"
    echo "$AG_PY"
}

# ── 4. AutoGluon python for no-show ─────────────────────────────────────────
step "4 / 6  AutoGluon env for no-show (Python 3.9 venv)"

AG_PY=""
if AG_PY="$(find_autogluon_python)"; then
    success "Reusing existing AutoGluon python: $AG_PY"
else
    AG_PY="$(install_autogluon_venv)"
    venv_has_module "$AG_PY" autogluon.tabular \
        && success "venv-autogluon ready ($AG_PY)" \
        || error "AutoGluon install failed — check network and requirements-autogluon.txt"
fi

# ── 5. .env ──────────────────────────────────────────────────────────────────
step "5 / 6  Updating .env"

ENV_FILE="$GATEWAY_DIR/.env"
[[ -f "$ENV_FILE" ]] || cp "$GATEWAY_DIR/.env.example" "$ENV_FILE" 2>/dev/null || touch "$ENV_FILE"

set_env() {
    local key="$1" val="$2"
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}

set_env "AUTOGLUON_PYTHON" "$AG_PY"
# Do not overwrite LOCAL_MODELS_DIR if already set for old deploy
if ! grep -q "^LOCAL_MODELS_DIR=" "$ENV_FILE" 2>/dev/null; then
    set_env "LOCAL_MODELS_DIR" "$MODELS_BASE"
fi

chown "$GATEWAY_USER:$GATEWAY_USER" "$ENV_FILE"
chmod 640 "$ENV_FILE"
success "AUTOGLUON_PYTHON=$AG_PY"

# ── 6. Restart ───────────────────────────────────────────────────────────────
step "6 / 6  Restart and verify"

if $SKIP_RESTART; then
    warn "Skipped restart (--no-restart)"
else
    if systemctl is-enabled ml-gateway &>/dev/null; then
        systemctl restart ml-gateway
        success "ml-gateway restarted (still using $GATEWAY_VENV/bin/uvicorn)"
    else
        warn "systemd unit not found — restart manually with existing venv"
    fi
fi

info "Smoke test..."
sudo -u "$GATEWAY_USER" env AUTOGLUON_PYTHON="$AG_PY" bash -c "
    cd $GATEWAY_DIR
    $GATEWAY_PY -c \"
from models.registry import ModelRegistry
r = ModelRegistry()
for mid in ('no_show_fakeeh_ksa_local', 'delay_fakeeh_ksa_local'):
    m = r.get_model(mid)
    print(mid, '->', m.local_artifact_path, m.local_artifact_format)
from pathlib import Path
for d in ('new-noshow-ksa', 'Fakeeh-Delay-Arrival_ksa'):
    print(' ', d, (Path('$MODELS_BASE') / d).exists())
\"
"

PORT=8000
grep -q '^GATEWAY_PORT=' "$ENV_FILE" 2>/dev/null && PORT="$(grep '^GATEWAY_PORT=' "$ENV_FILE" | cut -d= -f2)"

if ! $SKIP_RESTART; then
    for i in $(seq 1 30); do
        if curl -sf "http://127.0.0.1:${PORT}/health" &>/dev/null; then
            success "Gateway healthy on port $PORT"
            echo ""
            echo "  Existing venv kept : $GATEWAY_VENV"
            echo "  AutoGluon python   : $AG_PY"
            echo "  Test no-show       : POST /v1/predict/no_show_fakeeh_ksa_local"
            echo "  Test delay         : POST /v1/predict/delay_fakeeh_ksa_local"
            exit 0
        fi
        sleep 2
    done
    warn "Health check timed out"
    echo "  sudo journalctl -u ml-gateway -n 80 --no-pager"
fi

success "Update applied — existing deployment patched in place."
