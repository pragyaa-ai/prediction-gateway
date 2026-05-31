"""
Load serialized models from disk (shipped under models/local-models) for on-prem deployment.
"""
from __future__ import annotations

import asyncio
import pickle
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from adapters.base import BaseModelAdapter
from adapters.mappers import get_input_mapper, get_output_mapper
from config.paths import DEFAULT_LOCAL_MODELS_DIR, PROJECT_ROOT
from config.settings import settings
from models.schemas import InferenceRequest, InferenceResponse, ModelConfig

_locks: Dict[str, Lock] = {}
_cache: Dict[str, Tuple[float, Any]] = {}


def _local_models_base() -> Path:
    """Directory containing on-disk model folders (override via LOCAL_MODELS_DIR in .env)."""
    if settings.local_models_dir:
        p = Path(settings.local_models_dir)
        return p if p.is_absolute() else PROJECT_ROOT / p
    return DEFAULT_LOCAL_MODELS_DIR


def _artifact_lock(key: str) -> Lock:
    if key not in _locks:
        _locks[key] = Lock()
    return _locks[key]


def _resolve_artifact_path(rel: str) -> Path:
    """
    Resolve local_artifact_path from config/models.yaml.

    Supported forms:
      - Absolute: /opt/ml-models/los/model.pkl
      - Relative to LOCAL_MODELS_DIR: cost-estimation-ksa/model.joblib
      - Legacy repo-relative: models/local-models/los_prediction_ksa/model.pkl
    """
    raw = rel.replace("\\", "/")
    p = Path(rel)

    if p.is_absolute():
        return p

    base = _local_models_base()
    candidates: list[Path] = []

    if raw.startswith("models/local-models/"):
        candidates.append(base / raw[len("models/local-models/"):])
    candidates.append(base / raw)
    candidates.append(PROJECT_ROOT / raw)

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve())
        if key in seen:
            continue
        seen.add(key)
        if candidate.exists():
            return candidate

    tried = "\n  ".join(str(c) for c in candidates)
    raise FileNotFoundError(
        f"Local model artifact not found for '{rel}'.\n"
        f"  LOCAL_MODELS_DIR={base}\n"
        f"  PROJECT_ROOT={PROJECT_ROOT}\n"
        f"  Tried:\n  {tried}"
    )


def _load_artifact(config: ModelConfig) -> Any:
    path = _resolve_artifact_path(config.local_artifact_path)  # type: ignore[arg-type]
    fmt = (config.local_artifact_format or "pickle").lower()
    mtime = path.stat().st_mtime
    key = str(path.resolve())
    cached = _cache.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    with _artifact_lock(key):
        cached = _cache.get(key)
        if cached and cached[0] == mtime:
            return cached[1]
        if fmt == "joblib":
            import joblib

            obj = joblib.load(path)
        elif fmt == "azure_automl_pickle":
            from adapters.azureml_compat import load_azure_automl_pickle

            obj = load_azure_automl_pickle(str(path))
        elif fmt == "pickle":
            with open(path, "rb") as f:
                obj = pickle.load(f)
        else:
            raise ValueError(f"Unsupported local_artifact_format: {fmt}")
        _cache[key] = (mtime, obj)
    return obj


def _coerce_float(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _sklearn_predict(model: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    if "_local_records" in payload:
        X = pd.DataFrame(payload["_local_records"])
    elif "_local_matrix" in payload:
        X = np.asarray(payload["_local_matrix"], dtype=float)
    else:
        raise ValueError(
            "Local sklearn model expects input mapper to set '_local_records' "
            "(list of row dicts) or '_local_matrix' (2D row-major values)."
        )
    preds = model.predict(X)
    raw: Dict[str, Any] = {"prediction": preds[0] if len(preds) else None}
    if hasattr(model, "predict_proba"):
        probas = model.predict_proba(X)[0]
        raw["score"] = float(np.max(probas))
    return raw


def _automl_pipeline_predict(model: Any, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run inference on an Azure AutoML RegressionPipeline loaded by azureml_compat."""
    X = pd.DataFrame([inputs])
    preds = model.predict(X)
    val = float(preds[0]) if len(preds) else 0.0
    return {"prediction": val, "score": None}


def _noshow_bundle_predict(bundle: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    from adapters.noshow_features import engineer_noshow_features

    clf = bundle["model"]
    feature_names = bundle["feature_names"]
    row_dict = engineer_noshow_features(inputs, bundle)
    row = [row_dict.get(name, 0.0) for name in feature_names]
    X = np.array([row], dtype=np.float32)
    pred = int(clf.predict(X)[0])
    score = None
    if hasattr(clf, "predict_proba"):
        probs = clf.predict_proba(X)[0]
        classes = list(getattr(clf, "classes_", [0, 1]))
        if 1 in classes:
            score = float(probs[classes.index(1)])
        else:
            score = float(np.max(probs))
    return {"prediction": pred, "score": score}


class LocalArtifactAdapter(BaseModelAdapter):
    """Run inference for models stored as pickle/joblib under the repo."""

    async def predict(self, request: InferenceRequest, config: ModelConfig) -> InferenceResponse:
        start_time = time.time()
        kind = (config.local_model_kind or "sklearn").lower()
        artifact = await asyncio.to_thread(_load_artifact, config)
        output_mapper = get_output_mapper(config.output_mapper)

        if kind == "noshow_xgboost_bundle":
            if not isinstance(artifact, dict) or "model" not in artifact or "feature_names" not in artifact:
                raise ValueError("noshow_xgboost_bundle expects a pickle dict with 'model' and 'feature_names'")
            raw = await asyncio.to_thread(_noshow_bundle_predict, artifact, request.inputs)
        elif kind == "azure_automl_pipeline":
            input_mapper = get_input_mapper(config.input_mapper)
            mapped = input_mapper(request.inputs)
            raw = await asyncio.to_thread(_automl_pipeline_predict, artifact, mapped)
        else:
            input_mapper = get_input_mapper(config.input_mapper)
            payload = input_mapper(request.inputs)
            raw = await asyncio.to_thread(_sklearn_predict, artifact, payload)

        standardized = output_mapper(raw)
        latency_ms = int((time.time() - start_time) * 1000)
        return InferenceResponse(
            request_id=request.request_id,
            model_id=request.model_id,
            prediction=standardized["prediction"],
            score=standardized.get("score"),
            latency_ms=standardized.get("latency_ms", latency_ms),
        )
