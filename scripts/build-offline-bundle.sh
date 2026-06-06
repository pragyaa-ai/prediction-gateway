#!/usr/bin/env bash
# =============================================================================
#  Build an air-gapped deployment bundle for ML Inference Gateway.
#
#  Run on an internet-connected machine that matches production:
#    OS:   Ubuntu 22.04 (or same glibc Linux) x86_64
#    Python: 3.10 (python3.10)
#
#  Usage:
#    bash scripts/build-offline-bundle.sh
#    bash scripts/build-offline-bundle.sh /path/to/output-dir
#
#  Output:
#    dist/ml-gateway-offline-YYYYMMDD.tar.gz   (or .zip if zip is installed)
#
#  Transfer the archive to the production VM (USB / SCP from jump host),
#  extract, and run offline-install.sh — no internet required on target.
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y%m%d)"
OUTPUT_BASE="${1:-${REPO_ROOT}/dist/ml-gateway-offline-${STAMP}}"
BUNDLE_DIR="${OUTPUT_BASE}"
ARCHIVE_TGZ="${OUTPUT_BASE}.tar.gz"
ARCHIVE_ZIP="${OUTPUT_BASE}.zip"

PYTHON="${PYTHON:-python3.10}"
if ! command -v "$PYTHON" &>/dev/null; then
    PYTHON=python3
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }
step()    { echo -e "\n${BOLD}━━━  $*  ━━━${RESET}"; }

step "ML Gateway – offline bundle builder"
info "Repo       : $REPO_ROOT"
info "Bundle dir : $BUNDLE_DIR"
info "Python     : $PYTHON ($($PYTHON --version 2>&1))"

if [[ "$(uname -s)" != "Linux" ]]; then
    warn "Not running on Linux — wheel download will target manylinux2014_x86_64."
    warn "Pre-built venv/ copies are skipped (not portable across OS)."
    warn "Best practice: run this script on Ubuntu 22.04 x86_64 matching production."
fi

if [[ "$(uname -m)" != "x86_64" && "$(uname -m)" != "amd64" ]]; then
    warn "Architecture is $(uname -m); production bundle assumes x86_64."
fi

rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"/{app,wheels/gateway,wheels/autogluon,system-deps}

# ── 1. Application source + local models ───────────────────────────────────
step "1 / 5  Copying application and local models"

RSYNC_EXCLUDES=(
    --exclude='.git'
    --exclude='.gitignore'
    --exclude='venv'
    --exclude='venv39'
    --exclude='venv-autogluon'
    --exclude='.venv'
    --exclude='__pycache__'
    --exclude='*.pyc'
    --exclude='.pytest_cache'
    --exclude='dist'
    --exclude='offline-bundle'
    --exclude='.env'
    --exclude='.DS_Store'
    --exclude='*.log'
    --exclude='htmlcov'
    --exclude='.coverage'
)

rsync -a "${RSYNC_EXCLUDES[@]}" "$REPO_ROOT/" "$BUNDLE_DIR/app/"

if [[ ! -d "$BUNDLE_DIR/app/models/local-models" ]]; then
    error "models/local-models/ missing — add local model artifacts before building."
    exit 1
fi

MODEL_BYTES="$(du -sb "$BUNDLE_DIR/app/models/local-models" | cut -f1)"
info "Local models size: $(du -sh "$BUNDLE_DIR/app/models/local-models" | cut -f1)"

# ── 2. Download Python wheels (linux x86_64) ─────────────────────────────────
step "2 / 5  Downloading Python wheels (no install yet)"

"$PYTHON" -m pip install --upgrade pip wheel setuptools >/dev/null

PY_MM="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_TAG="$("$PYTHON" -c 'import sys; print(f"cp{sys.version_info.major}{sys.version_info.minor}")')"

download_wheels() {
    local req_file="$1"
    local dest="$2"
    info "Wheels for $(basename "$req_file") → $dest"

    if [[ "$(uname -s)" == "Linux" ]]; then
        "$PYTHON" -m pip download -r "$req_file" -d "$dest" \
            --no-cache-dir \
            || warn "Some wheels may be missing; retrying with fewer binary-only constraints..."
        "$PYTHON" -m pip download -r "$req_file" -d "$dest" \
            --no-cache-dir \
            --prefer-binary
    else
        # Cross-download Linux wheels from macOS/Windows build host
        "$PYTHON" -m pip download -r "$req_file" -d "$dest" \
            --no-cache-dir \
            --platform manylinux2014_x86_64 \
            --platform manylinux_2_17_x86_64 \
            --python-version "$PY_MM" \
            --implementation cp \
            --abi "$PY_TAG" \
            --only-binary=:all: \
            || true
        "$PYTHON" -m pip download -r "$req_file" -d "$dest" \
            --no-cache-dir \
            --platform manylinux2014_x86_64 \
            --python-version "$PY_MM" \
            --implementation cp \
            --abi "$PY_TAG" \
            || warn "Some packages may need to be built on the target from sdists."
    fi

    local count
    count="$(find "$dest" -type f \( -name '*.whl' -o -name '*.tar.gz' -o -name '*.zip' \) | wc -l | tr -d ' ')"
    info "  → $count wheel/sdist files"
}

download_wheels "$REPO_ROOT/requirements.txt" "$BUNDLE_DIR/wheels/gateway"
download_wheels "$REPO_ROOT/requirements-autogluon.txt" "$BUNDLE_DIR/wheels/autogluon"

# ── 3. Pre-build venvs (Linux only — portable when glibc matches) ────────────
step "3 / 5  Pre-building virtual environments"

create_offline_venv() {
    local venv_path="$1"
    local wheels_dir="$2"
    local req_file="$3"

    "$PYTHON" -m venv "$venv_path"
    # shellcheck disable=SC1091
    source "$venv_path/bin/activate"
    pip install --upgrade pip wheel setuptools
    pip install --no-index --find-links="$wheels_dir" -r "$req_file"
    deactivate
}

if [[ "$(uname -s)" == "Linux" ]]; then
    info "Building gateway venv..."
    create_offline_venv "$BUNDLE_DIR/venv" "$BUNDLE_DIR/wheels/gateway" "$REPO_ROOT/requirements.txt"
    success "venv/ ready"

    info "Building AutoGluon venv (no-show model)..."
    create_offline_venv "$BUNDLE_DIR/venv-autogluon" "$BUNDLE_DIR/wheels/autogluon" "$REPO_ROOT/requirements-autogluon.txt"
    success "venv-autogluon/ ready"

    # Strip venv caches to shrink bundle
    find "$BUNDLE_DIR/venv" "$BUNDLE_DIR/venv-autogluon" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
else
    warn "Skipping venv pre-build (not Linux). Target will create venvs from wheels/."
fi

# ── 4. Offline install script + system deps manifest ─────────────────────────
step "4 / 5  Adding offline install assets"

cp "$REPO_ROOT/scripts/offline-install.sh" "$BUNDLE_DIR/offline-install.sh"
chmod +x "$BUNDLE_DIR/offline-install.sh"

cat > "$BUNDLE_DIR/system-deps/apt-packages.txt" <<'EOF'
# Minimal Ubuntu 22.04 packages for air-gapped install.
# On a connected Ubuntu machine, download debs into system-deps/debs/:
#   bash system-deps/download-system-deps.sh
python3.10
python3.10-venv
python3-pip
libgomp1
libstdc++6
libgfortran5
curl
EOF

cat > "$BUNDLE_DIR/system-deps/download-system-deps.sh" <<'EOF'
#!/usr/bin/env bash
# Run on internet-connected Ubuntu 22.04 to cache .deb files for offline apt install.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DIR/debs"
sudo apt-get update
while read -r pkg; do
    [[ -z "$pkg" || "$pkg" =~ ^# ]] && continue
    apt-get download "$pkg" -o Dir::Cache::archives="$DIR/debs" || true
done < "$DIR/apt-packages.txt"
echo "Saved debs to $DIR/debs/"
ls -lh "$DIR/debs/" | tail -20
EOF
chmod +x "$BUNDLE_DIR/system-deps/download-system-deps.sh"

cat > "$BUNDLE_DIR/README-OFFLINE.txt" <<EOF
ML Inference Gateway – Offline Deployment Bundle
Built: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Python: $($PYTHON --version 2>&1)

CONTENTS
  app/                  Gateway source + models/local-models/
  wheels/gateway/       Pip wheels for main gateway (requirements.txt)
  wheels/autogluon/     Pip wheels for AutoGluon no-show venv
  venv/                 Pre-built gateway venv (Linux build only)
  venv-autogluon/       Pre-built AutoGluon venv (Linux build only)
  system-deps/          Optional Ubuntu .deb cache for fully air-gapped apt
  offline-install.sh    Install script (no internet)

PRODUCTION PREREQUISITES (must exist on target BEFORE install)
  - Ubuntu 22.04 x86_64 (or same glibc as build machine)
  - python3.10 + python3.10-venv  (install from system-deps/debs/ if no network)
  - libgomp1, libstdc++6

INSTALL (on air-gapped production VM)
  1. Copy archive to server (USB / internal SCP)
  2. tar -xzf ml-gateway-offline-*.tar.gz
  3. cd ml-gateway-offline-*
  4. sudo bash offline-install.sh --dir /opt/ml-gateway --port 8000

OPTIONAL: cache system packages while you still have internet
  cd system-deps && bash download-system-deps.sh
  Copy system-deps/debs/ along with this bundle; offline-install.sh can install them.

VERIFY
  curl http://localhost:8000/health
  curl http://localhost:8000/v1/models

ENV (written to /opt/ml-gateway/.env)
  AUTOGUON_PYTHON=/opt/ml-gateway/venv-autogluon/bin/python
  LOCAL_MODELS_DIR=/opt/ml-gateway/models/local-models
EOF

# Manifest
{
    echo "bundle_created_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "build_host=$(uname -a)"
    echo "python=$($PYTHON --version 2>&1)"
    echo "models_bytes=$MODEL_BYTES"
    du -sh "$BUNDLE_DIR"/* 2>/dev/null || true
    echo ""
    echo "local_models:"
    find "$BUNDLE_DIR/app/models/local-models" -maxdepth 2 -type f -o -type d | head -80
} > "$BUNDLE_DIR/BUNDLE_MANIFEST.txt"

# ── 5. Archive ───────────────────────────────────────────────────────────────
step "5 / 5  Creating archive"

mkdir -p "$(dirname "$ARCHIVE_TGZ")"
tar -czf "$ARCHIVE_TGZ" -C "$(dirname "$BUNDLE_DIR")" "$(basename "$BUNDLE_DIR")"
success "Created $ARCHIVE_TGZ ($(du -sh "$ARCHIVE_TGZ" | cut -f1))"

if command -v zip &>/dev/null; then
    (cd "$(dirname "$BUNDLE_DIR")" && zip -rq "$(basename "$ARCHIVE_ZIP")" "$(basename "$BUNDLE_DIR")")
    success "Created $ARCHIVE_ZIP ($(du -sh "$ARCHIVE_ZIP" | cut -f1))"
else
    warn "zip not installed — only .tar.gz created."
fi

echo ""
success "Offline bundle ready."
echo ""
echo "  Transfer to production:"
echo "    $ARCHIVE_TGZ"
if [[ -f "$ARCHIVE_ZIP" ]]; then
    echo "    $ARCHIVE_ZIP"
fi
echo ""
echo "  On production (no internet):"
echo "    tar -xzf $(basename "$ARCHIVE_TGZ")"
echo "    cd $(basename "$BUNDLE_DIR")"
echo "    sudo bash offline-install.sh"
echo ""
