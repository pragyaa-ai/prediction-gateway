#!/usr/bin/env python3
"""
Pinpoint the -507 root cause: featurization vs XGBoost.
Run on the VM as:
  sudo -u mlgateway bash -c 'cd /opt/ml-gateway && venv/bin/python scripts/debug-delay-features.py'
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

print(f"pandas  {pd.__version__}")
print(f"numpy   {np.__version__}")

from adapters.delay_features import engineer_delay_features, FAKEEH_DELAY_MODEL_COLUMNS, FAKEEH_DELAY_STRING_COLUMNS
from adapters.azureml_compat import install_azureml_compat, _patch_loaded_model, load_azure_automl_pickle

PAYLOAD = {
    "MRNO":"2247106","PROVIDER_NAME":"Arwa Faez Ghaleb Lardhi","DEPARTMENT":"Adult Cardiology",
    "APPT_ALLOCATION_ID":"16912366","ALLOCATION_DATE_TIME":"2026-05-25T21:15:00","ALLOCATION_DAY":"Monday",
    "TOKEN_NO":"86A","VIP":0,"GIVEN_BY":"Administrator","FOLLOW_NEW":"N","AGE":"17y",
    "NATIONALITY":"SAUDI","FACILITY_NAME":"DSFH","GENDER":"Female","VISIT_METHOD":"PHYSICAL",
    "GIVEN_ON":"2026-05-25T13:41:31","DOCTORS_NATIONALITY":"YEMENI","APPT_BOOKING_CHANNEL":"OTHERS",
    "CITY":"Jeddah","PAYMENT_STATUS":"Not Paid","VISIT_TYPE":"CASH","CONTRACT_NAME":None,
}

wide = engineer_delay_features(PAYLOAD)
row = [
    ("" if col in FAKEEH_DELAY_STRING_COLUMNS else (0 if wide.get(col) is None or wide.get(col) == "" else wide.get(col)))
    for col in FAKEEH_DELAY_MODEL_COLUMNS
]
X = pd.DataFrame([row], columns=list(FAKEEH_DELAY_MODEL_COLUMNS))
print(f"\nInput DataFrame shape: {X.shape}")
print(f"Nonzero input cols: {[(c, X[c].iloc[0]) for c in X.columns if X[c].iloc[0] not in (0, 0.0, '')][:10]}")

model = load_azure_automl_pickle("models/local-models/Fakeeh-Delay-Arrival_ksa/model.pkl")

# Step 1: Run DataTransformer only
dt = model.pipeline.named_steps["datatransformer"]
try:
    feat = dt.transform(X)
    print(f"\nDataTransformer output shape: {feat.shape}")
    print(f"First 10 feature values: {feat[0, :10]}")
    print(f"Min: {feat.min():.4f}  Max: {feat.max():.4f}  Mean: {feat.mean():.4f}")
    print(f"NaN count: {np.isnan(feat).sum()}")
    print(f"Inf count: {np.isinf(feat).sum()}")
except Exception as e:
    print(f"DataTransformer FAILED: {e}")
    sys.exit(1)

# Step 2: Run voter on known good features (all zeros)
voter = model.pipeline.named_steps["prefittedsoftvotingregressor"]
ens = voter._wrappedEnsemble
print(f"\nEnsemble estimators: {len(ens.estimators_)}, weights: {ens.weights}")

# Test each sub-estimator
for i, est in enumerate(ens.estimators_):
    try:
        p = float(est.predict(feat)[0])
        print(f"  est[{i}] {type(est).__name__}: {p:.4f}")
    except Exception as e:
        print(f"  est[{i}] ERROR: {e}")

# Step 3: Test XGBoost booster directly with all-zeros to confirm it loads
print("\n--- XGBoost booster direct test (all-zeros 100 features) ---")
for i, est in enumerate(ens.estimators_):
    inner = getattr(est, "model", None)
    if inner is None:
        continue
    booster = getattr(inner, "_Booster", None)
    if booster is None:
        try:
            booster = inner.get_booster()
        except Exception:
            pass
    if booster is None:
        print(f"  est[{i}]: no booster attribute")
        continue
    cls_name = type(est).__name__
    if "XGBoost" not in cls_name:
        continue
    try:
        import xgboost as xgb
        n_feat = feat.shape[1]
        zero_dmat = xgb.DMatrix(np.zeros((1, n_feat)))
        p0 = float(booster.predict(zero_dmat)[0])
        real_dmat = xgb.DMatrix(feat)
        pr = float(booster.predict(real_dmat)[0])
        print(f"  est[{i}] zeros->{p0:.4f}  real->{pr:.4f}")
    except Exception as e:
        print(f"  est[{i}] direct booster error: {e}")

print("\nDone.")
