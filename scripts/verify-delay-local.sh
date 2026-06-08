#!/usr/bin/env bash
# Quick smoke test for delay_fakeeh_ksa_local on the VM.
set -euo pipefail

GATEWAY_DIR="${GATEWAY_DIR:-/opt/ml-gateway}"
GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:8000}"
MODEL_PKL="$GATEWAY_DIR/models/local-models/Fakeeh-Delay-Arrival_ksa/model.pkl"

echo "=== delay_fakeeh_ksa_local verify ==="
echo "Gateway dir: $GATEWAY_DIR"
echo "Model file : $MODEL_PKL"
ls -lh "$MODEL_PKL"

echo ""
echo "Gateway adapters:"
grep -q "_is_hospital_appointment" "$GATEWAY_DIR/adapters/delay_features.py" \
  && echo "  delay_features.py: OK (wide schema)" \
  || echo "  delay_features.py: OUTDATED — run git pull && copy adapters"

grep -q "FAKEEH_DELAY_MODEL_COLUMNS" "$GATEWAY_DIR/adapters/local_inference.py" \
  && echo "  local_inference.py: OK" \
  || echo "  local_inference.py: OUTDATED"

echo ""
echo "lightgbm:"
"$GATEWAY_DIR/venv/bin/python" -c "import lightgbm; print('  OK', lightgbm.__version__)" \
  || echo "  MISSING — pip install lightgbm in gateway venv"

PAYLOAD='{"client_id":"verify","inputs":{"MRNO":"2247106","PROVIDER_NAME":"Arwa Faez Ghaleb Lardhi","DEPARTMENT":"Adult Cardiology","APPT_ALLOCATION_ID":"16912366","ALLOCATION_DATE_TIME":"2026-05-25T21:15:00","ALLOCATION_DAY":"Monday","TOKEN_NO":"86A","VIP":0,"GIVEN_BY":"Administrator","FOLLOW_NEW":"N","AGE":"17y","NATIONALITY":"SAUDI","FACILITY_NAME":"DSFH","GENDER":"Female","VISIT_METHOD":"PHYSICAL","GIVEN_ON":"2026-05-25T13:41:31","DOCTORS_NATIONALITY":"YEMENI","APPT_BOOKING_CHANNEL":"OTHERS","CITY":"Jeddah","PAYMENT_STATUS":"Not Paid","VISIT_TYPE":"CASH","CONTRACT_NAME":null}}'

echo ""
echo "POST $GATEWAY_URL/v1/predict/delay_fakeeh_ksa_local"
RESP=$(curl -sf -X POST "$GATEWAY_URL/v1/predict/delay_fakeeh_ksa_local" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")
echo "$RESP" | python3 -m json.tool 2>/dev/null || echo "$RESP"

echo ""
echo "Expected prediction: ~2.4 min (not -507). If -507, restart ml-gateway after copying adapters."
