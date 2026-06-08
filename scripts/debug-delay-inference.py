#!/usr/bin/env python3
"""Diagnose delay_fakeeh_ksa_local inference on the VM (run as mlgateway user)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PAYLOAD = {
    "MRNO": "2247106",
    "PROVIDER_NAME": "Arwa Faez Ghaleb Lardhi",
    "DEPARTMENT": "Adult Cardiology",
    "APPT_ALLOCATION_ID": "16912366",
    "ALLOCATION_DATE_TIME": "2026-05-25T21:15:00",
    "ALLOCATION_DAY": "Monday",
    "TOKEN_NO": "86A",
    "VIP": 0,
    "GIVEN_BY": "Administrator",
    "FOLLOW_NEW": "N",
    "AGE": "17y",
    "NATIONALITY": "SAUDI",
    "FACILITY_NAME": "DSFH",
    "GENDER": "Female",
    "VISIT_METHOD": "PHYSICAL",
    "GIVEN_ON": "2026-05-25T13:41:31",
    "DOCTORS_NATIONALITY": "YEMENI",
    "APPT_BOOKING_CHANNEL": "OTHERS",
    "CITY": "Jeddah",
    "PAYMENT_STATUS": "Not Paid",
    "VISIT_TYPE": "CASH",
    "CONTRACT_NAME": None,
}


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    from config.settings import settings
    from config.paths import PROJECT_ROOT, DEFAULT_LOCAL_MODELS_DIR
    from adapters.delay_features import (
        FAKEEH_DELAY_MODEL_COLUMNS,
        FAKEEH_DELAY_STRING_COLUMNS,
        engineer_delay_features,
    )
    from adapters.local_inference import _resolve_artifact_path, _automl_pipeline_predict
    from adapters.azureml_compat import load_azure_automl_pickle
    from models.registry import ModelRegistry

    print("=== delay_fakeeh_ksa_local debug ===")
    print(f"PROJECT_ROOT      : {PROJECT_ROOT}")
    print(f"LOCAL_MODELS_DIR  : {settings.local_models_dir or DEFAULT_LOCAL_MODELS_DIR}")

    cfg = ModelRegistry().get_model("delay_fakeeh_ksa_local")
    artifact = _resolve_artifact_path(cfg.local_artifact_path)  # type: ignore[arg-type]
    print(f"Resolved artifact : {artifact}")
    print(f"Artifact size     : {artifact.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"Artifact MD5      : {md5_file(artifact)}")
    print(f"Expected MD5      : dd2baccbac8b2e0e7f73ad1891e47b85  (repo 4MB wide model)")

    wide = engineer_delay_features(PAYLOAD)
    print(f"LEAD_TIME_MINUTES : {wide.get('LEAD_TIME_MINUTES')}")
    print(f"ALLOCATION_HOUR   : {wide.get('ALLOCATION_HOUR')}")
    print(f"AGE_MONTHS        : {wide.get('AGE_MONTHS')}")
    print(f"Wide column count : {len(wide)}")
    print(f"Has all 161 cols  : {all(k in wide for k in FAKEEH_DELAY_MODEL_COLUMNS)}")

    try:
        import lightgbm  # noqa: F401
        import xgboost

        print(f"xgboost           : {xgboost.__version__}")
    except ImportError as e:
        print(f"ML libs missing   : {e}")

    model = load_azure_automl_pickle(str(artifact))
    dt = model.pipeline.named_steps.get("datatransformer")
    n_tf = len(getattr(dt, "transformer_and_mapper_list", []))
    print(f"DataTransformers  : {n_tf}  (expect 161)")

    pred = _automl_pipeline_predict(model, wide)
    print(f"Direct prediction : {pred.get('prediction')}")
    print(f"Expected          : ~2.4 (not -507)")

    if n_tf != 161:
        print("\nFAIL: model.pkl is the OLD 23-column AutoML artifact — copy the 4MB model.pkl")
        return 1
    if abs(float(pred.get("prediction", 0)) - (-507.902368871524)) < 0.01:
        print("\nFAIL: still -507 — check MD5 matches repo; copy adapters/azureml_compat.py and restart")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
