"""
Load serialized models from disk (shipped under models/local-models) for on-prem deployment.
"""
from __future__ import annotations

import asyncio
import json
import pickle
import subprocess
import sys
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

from adapters.base import BaseModelAdapter
from adapters.mappers import get_input_mapper, get_output_mapper
from adapters.response_utils import (
    build_inference_response,
    regression_confidence_from_predictions,
)
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


def _artifact_mtime(path: Path, fmt: str) -> float:
    if fmt == "autogluon_dir":
        marker = path / "predictor.pkl"
        if marker.exists():
            return marker.stat().st_mtime
    return path.stat().st_mtime


def _load_artifact(config: ModelConfig) -> Any:
    path = _resolve_artifact_path(config.local_artifact_path)  # type: ignore[arg-type]
    fmt = (config.local_artifact_format or "pickle").lower()
    mtime = _artifact_mtime(path, fmt)
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
        elif fmt == "autogluon_dir":
            if not path.is_dir():
                raise FileNotFoundError(f"AutoGluon model directory not found: {path}")
            obj = _load_autogluon_artifact(path, config)
        elif fmt == "pickle":
            with open(path, "rb") as f:
                obj = pickle.load(f)
        else:
            raise ValueError(f"Unsupported local_artifact_format: {fmt}")
        _cache[key] = (mtime, obj)
    return obj


def _autogluon_python() -> str:
    if settings.autogluon_python:
        return settings.autogluon_python
    for rel in ("venv-autogluon/bin/python", "venv39/bin/python"):
        candidate = PROJECT_ROOT / rel
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _load_autogluon_artifact(path: Path, config: ModelConfig) -> Dict[str, Any]:
    from adapters.autogluon_noshow import DEFAULT_ENSEMBLE_MODEL, autogluon_available, load_autogluon_predictor

    model_name = config.local_autogluon_model_name or DEFAULT_ENSEMBLE_MODEL
    bundle: Dict[str, Any] = {
        "model_dir": str(path.resolve()),
        "model_name": model_name,
        "use_subprocess": not autogluon_available(),
        "python_bin": _autogluon_python(),
    }
    if not bundle["use_subprocess"]:
        bundle["predictor"] = load_autogluon_predictor(str(path))
    return bundle


def _autogluon_noshow_predict(bundle: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    model_name = bundle.get("model_name", "WeightedEnsemble_L3_FULL")
    if bundle.get("use_subprocess"):
        script = PROJECT_ROOT / "scripts" / "autogluon_noshow_infer.py"
        payload = {
            "model_dir": bundle["model_dir"],
            "model_name": model_name,
            "inputs": inputs,
        }
        proc = subprocess.run(
            [bundle["python_bin"], str(script)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"AutoGluon subprocess inference failed (exit {proc.returncode}): {proc.stderr.strip()}"
            )
        return json.loads(proc.stdout)

    from adapters.autogluon_noshow import predict_autogluon_noshow

    return predict_autogluon_noshow(bundle["predictor"], inputs, model_name=model_name)


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
        prob = float(np.max(probas))
        raw["score"] = prob
        raw["probability"] = prob
    elif hasattr(model, "estimators_"):
        tree_preds = np.array([est.predict(X)[0] for est in model.estimators_])
        conf = regression_confidence_from_predictions(tree_preds)
        raw["score"] = conf
        raw["probability"] = conf
    return raw


def _automl_pipeline_predict(model: Any, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run inference on an Azure AutoML RegressionPipeline loaded by azureml_compat."""
    from adapters.delay_features import DELAY_KSA_AUTOML_COLUMNS

    # Preserve column order when all keys are known (delay KSA schema)
    if all(k in inputs for k in DELAY_KSA_AUTOML_COLUMNS):
        X = pd.DataFrame([[inputs[k] for k in DELAY_KSA_AUTOML_COLUMNS]], columns=list(DELAY_KSA_AUTOML_COLUMNS))
    else:
        X = pd.DataFrame([inputs])
    preds = model.predict(X)
    val = float(preds[0]) if len(preds) else 0.0
    conf = _voting_ensemble_confidence(model, X)
    return {"prediction": val, "score": conf, "probability": conf}


def _voting_ensemble_confidence(model: Any, X: pd.DataFrame) -> float:
    """Estimate confidence from voting ensemble sub-estimator agreement."""
    try:
        pipe = getattr(model, "pipeline", None)
        if pipe is None or not hasattr(pipe, "named_steps"):
            return 1.0
        voter = pipe.named_steps.get("prefittedsoftvotingregressor")
        if voter is None:
            return 1.0
        ens = getattr(voter, "_wrappedEnsemble", None)
        if ens is None or not hasattr(ens, "estimators_"):
            return 1.0
        sub_preds = []
        for est in ens.estimators_:
            try:
                sub_preds.append(float(est.predict(X)[0]))
            except Exception:
                continue
        if sub_preds:
            return regression_confidence_from_predictions(np.array(sub_preds))
    except Exception:
        pass
    return 1.0


def _noshow_bundle_predict(bundle: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
    from adapters.noshow_features import (
        NOSHOW_CLASS_LABELS,
        engineer_noshow_features,
        noshow_class_label,
    )

    clf = bundle["model"]
    feature_names = bundle["feature_names"]
    row_dict = engineer_noshow_features(inputs, bundle)
    row = [row_dict.get(name, 0.0) for name in feature_names]
    X = np.array([row], dtype=np.float32)
    pred_raw = clf.predict(X)[0]
    pred_idx = int(pred_raw)
    predicted_label = noshow_class_label(pred_idx)

    classes = list(getattr(clf, "classes_", [0, 1]))
    show_idx = classes.index(0) if 0 in classes else 0
    no_show_idx = classes.index(1) if 1 in classes else 1

    score = None
    no_show_prob = None
    ordered_probs: list[float] = [0.0, 0.0]
    if hasattr(clf, "predict_proba"):
        probs = clf.predict_proba(X)[0]
        ordered_probs = [float(probs[show_idx]), float(probs[no_show_idx])]
        no_show_prob = ordered_probs[1]
        score = ordered_probs[0] if pred_idx == show_idx else ordered_probs[1]

    return {
        "prediction": pred_idx,
        "predicted_label": predicted_label,
        "score": score,
        "probability": no_show_prob,
        "no_show_probability": no_show_prob,
        "probabilities": ordered_probs,
        "class_labels": list(NOSHOW_CLASS_LABELS),
    }


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
            input_mapper = get_input_mapper(config.input_mapper)
            mapped = input_mapper(request.inputs)
            raw = await asyncio.to_thread(_noshow_bundle_predict, artifact, mapped)
        elif kind == "autogluon_tabular":
            if not isinstance(artifact, dict) or "model_dir" not in artifact:
                raise ValueError("autogluon_tabular expects a bundle dict with 'model_dir'")
            input_mapper = get_input_mapper(config.input_mapper)
            mapped = input_mapper(request.inputs)
            raw = await asyncio.to_thread(_autogluon_noshow_predict, artifact, mapped)
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
        if standardized.get("probability") is None and raw.get("probability") is not None:
            standardized["probability"] = raw.get("probability")
        if standardized.get("score") is None and raw.get("score") is not None:
            standardized["score"] = raw.get("score")
        return build_inference_response(request, standardized, latency_ms)
