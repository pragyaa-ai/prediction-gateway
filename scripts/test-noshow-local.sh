#!/usr/bin/env bash
# Smoke-test no_show_fakeeh_ksa_local (AutoGluon subprocess + model files).
# Run on the VM: sudo bash scripts/test-noshow-local.sh
set -euo pipefail

GATEWAY_DIR="${GATEWAY_DIR:-/opt/ml-gateway}"
MODELS_DIR="${LOCAL_MODELS_DIR:-$GATEWAY_DIR/models/local-models}"
MODEL_DIR="$MODELS_DIR/new-noshow-ksa"
ENV_FILE="$GATEWAY_DIR/.env"
GATEWAY_USER="${GATEWAY_USER:-ml-gateway}"

red() { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }
info() { printf '==> %s\n' "$*"; }

AG_PY=""
if [[ -f "$ENV_FILE" ]]; then
    AG_PY="$(grep -E '^(AUTOGLUON_PYTHON|AUTOGUON_PYTHON)=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d ' \"')"
fi
AG_PY="${AG_PY:-$GATEWAY_DIR/venv-autogluon/bin/python}"

info "Gateway dir : $GATEWAY_DIR"
info "Models dir  : $MODELS_DIR"
info "AutoGluon py: $AG_PY"

if [[ ! -x "$AG_PY" ]]; then
    red "AutoGluon python not found or not executable: $AG_PY"
    red "Re-run install.sh or: python3.9 -m venv $GATEWAY_DIR/venv-autogluon && pip install -r requirements-autogluon.txt"
    exit 1
fi

if [[ ! -f "$MODEL_DIR/predictor.pkl" ]]; then
    red "Model directory missing: $MODEL_DIR"
    exit 1
fi

if head -c 30 "$MODEL_DIR/learner.pkl" 2>/dev/null | grep -q "git-lfs"; then
    red "learner.pkl is a Git LFS pointer — run: cd repo && git lfs pull"
    exit 1
fi

info "Checking autogluon.tabular import..."
sudo -u "$GATEWAY_USER" "$AG_PY" -c "import autogluon.tabular; print('autogluon OK')"

PAYLOAD_FILE="$(mktemp)"
trap 'rm -f "$PAYLOAD_FILE"' EXIT
cat > "$PAYLOAD_FILE" <<EOF
{
  "model_dir": "$MODEL_DIR",
  "model_name": "WeightedEnsemble-L3-FULL-t1",
  "inputs": {
    "PROVIDER_NAME": "Test Provider",
    "DEPARTMENT": "Standard PT Session",
    "ALLOCATION_DATE_TIME": "14-06-2026 07:30",
    "ALLOCATION_DAY": "Sunday",
    "MRNO": "",
    "TOKEN_NO": "1A",
    "GIVEN_BY": "Test",
    "FOLLOW_NEW": "N",
    "AGE": "58y",
    "REMARKS": "Walkin Appointment",
    "APPT_ALLOCATION_ID": "19189806",
    "FACILITY_NAME": "DSFH",
    "GENDER": "Female",
    "VISIT_METHOD": "PHYSICAL",
    "GIVEN_ON": "08-06-2026 11:49",
    "DOCTORS_NATIONALITY": "SAUDI",
    "APPT_BOOKING_CHANNEL": "OTHERS",
    "CITY": "JEDDAH",
    "VISIT_TYPE": "CREDIT",
    "CONTRACT_NAME": "Tawuniya - Fakeeh Medical Group",
    "PAYMENT_STATUS": "Not Paid"
  }
}
EOF
chown "$GATEWAY_USER:$GATEWAY_USER" "$PAYLOAD_FILE" 2>/dev/null || true

info "Running AutoGluon subprocess inference..."
if sudo -u "$GATEWAY_USER" bash -c "cd '$GATEWAY_DIR' && '$AG_PY' scripts/autogluon_noshow_infer.py < '$PAYLOAD_FILE'"; then
    green "AutoGluon subprocess inference OK"
else
    red "AutoGluon subprocess inference FAILED (see traceback above)"
    exit 1
fi

info "POST /v1/predict/no_show_fakeeh_ksa_local ..."
RESP="$(curl -sS -w '\n%{http_code}' -X POST "http://127.0.0.1:8000/v1/predict/no_show_fakeeh_ksa_local" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"smoke-test","inputs":{"data":{"features":{"values":[["Test Provider","Standard PT Session","14-06-2026 07:30","Sunday","","1A","Test","N","58y","Walkin Appointment","19189806","DSFH","Female","PHYSICAL","08-06-2026 11:49","SAUDI","OTHERS","JEDDAH","CREDIT","Tawuniya - Fakeeh Medical Group","Not Paid"]]}}}}')"
BODY="${RESP%$'\n'*}"
CODE="${RESP##*$'\n'}"
echo "$BODY"
if [[ "$CODE" == "200" ]]; then
    green "Gateway prediction OK (HTTP $CODE)"
else
    red "Gateway prediction FAILED (HTTP $CODE)"
    exit 1
fi
