#!/usr/bin/env bash
# =============================================================================
#  Build a minimal offline update pack for KSA no-show + delay arrival models.
#  Patches an EXISTING /opt/ml-gateway — keeps the old venv/, adds venv-autogluon/.
#
#  Run on internet-connected machine (Ubuntu 22.04 x86_64 recommended):
#    bash scripts/build-ksa-update-pack.sh
#
#  Transfer ksa-update-*.tar.gz to production, extract, then:
#    sudo bash update-ksa-models.sh
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date +%Y%m%d)"
OUTPUT="${1:-${REPO_ROOT}/dist/ksa-update-${STAMP}}"
ARCHIVE="${OUTPUT}.tar.gz"

PYTHON="${PYTHON:-python3.10}"
if ! command -v "$PYTHON" &>/dev/null; then
    PYTHON=python3
fi

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
step()    { echo -e "\n${BOLD}━━━  $*  ━━━${RESET}"; }

# Files required for no_show_fakeeh_ksa_local + delay_fakeeh_ksa_local
PATCH_FILES=(
    config/models.yaml
    config/settings.py
    config/paths.py
    models/schemas.py
    models/registry.py
    requirements.txt
    requirements-autogluon.txt
    adapters/__init__.py
    adapters/autogluon_noshow.py
    adapters/azureml_compat.py
    adapters/base.py
    adapters/delay_features.py
    adapters/local_inference.py
    adapters/mappers.py
    adapters/noshow_features.py
    adapters/response_utils.py
    adapters/sagemaker_format.py
    scripts/autogluon_noshow_infer.py
)

MODEL_DIRS=(
    new-noshow-ksa
    Fakeeh-Delay-Arrival_ksa
)

step "KSA model update pack builder"
info "Output: $OUTPUT"

rm -rf "$OUTPUT"
mkdir -p "$OUTPUT/wheels/gateway" "$OUTPUT/wheels/autogluon"
mkdir -p "$OUTPUT/models/local-models"

step "1 / 4  Copying changed code"

for rel in "${PATCH_FILES[@]}"; do
    src="$REPO_ROOT/$rel"
    if [[ ! -f "$src" ]]; then
        warn "Missing $rel — skipping"
        continue
    fi
    mkdir -p "$OUTPUT/$(dirname "$rel")"
    cp "$src" "$OUTPUT/$rel"
done

cp "$REPO_ROOT/scripts/update-ksa-models.sh" "$OUTPUT/update-ksa-models.sh"
chmod +x "$OUTPUT/update-ksa-models.sh"

step "2 / 4  Copying model artifacts"

for dir in "${MODEL_DIRS[@]}"; do
    src="$REPO_ROOT/models/local-models/$dir"
    if [[ ! -d "$src" ]]; then
        warn "Model dir missing: $dir"
        continue
    fi
    rsync -a "$src/" "$OUTPUT/models/local-models/$dir/"
    info "  $dir ($(du -sh "$src" | cut -f1))"
done

step "3 / 4  Downloading wheels (offline install on production)"

"$PYTHON" -m pip install --upgrade pip wheel setuptools >/dev/null

PY_MM="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_TAG="$("$PYTHON" -c 'import sys; print(f"cp{sys.version_info.major}{sys.version_info.minor}")')"

# Production target (Ubuntu 22.04). AutoGluon 0.5.2 requires Python 3.9.
TARGET_PY_MM="${TARGET_PY_MM:-3.9}"
TARGET_PY_TAG="${TARGET_PY_TAG:-cp39}"
# Gateway venv on production is usually Python 3.10
GATEWAY_PY_MM="${GATEWAY_PY_MM:-3.10}"
GATEWAY_PY_TAG="${GATEWAY_PY_TAG:-cp310}"

download_wheels() {
    local req="$1"
    local dest="$2"
    local py_mm="$3"
    local py_tag="$4"
    if [[ "$(uname -s)" == "Linux" ]]; then
        "$PYTHON" -m pip download -r "$req" -d "$dest" --no-cache-dir --prefer-binary
    else
        info "  cross-download for linux x86_64 py${py_mm}"
        "$PYTHON" -m pip download -r "$req" -d "$dest" --no-cache-dir \
            --only-binary=:all: \
            --platform manylinux2014_x86_64 \
            --platform manylinux_2_17_x86_64 \
            --python-version "$py_mm" \
            --implementation cp \
            --abi "$py_tag"
    fi
}

download_wheel_pkg() {
    local pkg="$1"
    local dest="$2"
    local py_mm="$3"
    local py_tag="$4"
    if [[ "$(uname -s)" == "Linux" ]]; then
        "$PYTHON" -m pip download "$pkg" -d "$dest" --no-cache-dir --prefer-binary
    else
        "$PYTHON" -m pip download "$pkg" -d "$dest" --no-cache-dir \
            --only-binary=:all: \
            --platform manylinux2014_x86_64 \
            --platform manylinux_2_17_x86_64 \
            --python-version "$py_mm" \
            --implementation cp \
            --abi "$py_tag"
    fi
}

# Gateway: lightgbm only (delay model) — patch existing py3.10 venv
info "Downloading lightgbm wheel for gateway venv patch (py${GATEWAY_PY_MM})..."
download_wheel_pkg lightgbm "$OUTPUT/wheels/gateway" "$GATEWAY_PY_MM" "$GATEWAY_PY_TAG"

info "Downloading AutoGluon stack (py${TARGET_PY_MM} — required for autogluon 0.5.2)..."
download_wheels "$REPO_ROOT/requirements-autogluon.txt" "$OUTPUT/wheels/autogluon" "$TARGET_PY_MM" "$TARGET_PY_TAG" \
    || warn "Some AutoGluon wheels may be missing — build on Linux py3.9 for a complete pack"

step "4 / 4  Creating archive"

{
    echo "pack=ksa-update"
    echo "created=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "python=$($PYTHON --version 2>&1)"
    echo "models=${MODEL_DIRS[*]}"
    echo "files=${#PATCH_FILES[@]}"
} > "$OUTPUT/PATCH_MANIFEST.txt"

mkdir -p "$(dirname "$ARCHIVE")"
tar -czf "$ARCHIVE" -C "$(dirname "$OUTPUT")" "$(basename "$OUTPUT")"
success "Created $ARCHIVE ($(du -sh "$ARCHIVE" | cut -f1))"

ARCHIVE_ZIP="${OUTPUT}.zip"
if command -v zip &>/dev/null; then
    (cd "$(dirname "$OUTPUT")" && zip -rq "$(basename "$ARCHIVE_ZIP")" "$(basename "$OUTPUT")")
    success "Created $ARCHIVE_ZIP ($(du -sh "$ARCHIVE_ZIP" | cut -f1))"
else
    warn "zip not installed — only .tar.gz created"
fi

echo ""
success "Update pack ready."
echo ""
echo "  On production (existing /opt/ml-gateway):"
echo "    unzip $(basename "$ARCHIVE_ZIP")   # or: tar -xzf $(basename "$ARCHIVE")"
echo "    cd $(basename "$OUTPUT")"
echo "    sudo bash update-ksa-models.sh"
echo ""
