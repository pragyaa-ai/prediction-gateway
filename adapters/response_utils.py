"""Build standardized API responses with prediction + probability."""
from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from models.schemas import InferenceRequest, InferenceResponse


def extract_probability(standardized: Dict[str, Any]) -> Optional[float]:
    """Read probability/confidence from mapper output (first non-null float)."""
    for key in (
        "probability",
        "no_show_probability",
        "score",
        "confidence",
    ):
        val = standardized.get(key)
        if val is None:
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return None


def build_inference_response(
    request: InferenceRequest,
    standardized: Dict[str, Any],
    latency_ms: int,
) -> InferenceResponse:
    """Map mapper output to InferenceResponse with probability always exposed."""
    probability = extract_probability(standardized)
    return InferenceResponse(
        request_id=request.request_id,
        model_id=request.model_id,
        prediction=standardized.get("prediction"),
        score=probability,
        probability=probability,
        latency_ms=latency_ms,
    )


def regression_confidence_from_predictions(preds: np.ndarray) -> float:
    """
    Turn spread of sub-model predictions into a 0–1 confidence score.
    Used for regressors that have no predict_proba (RF trees, voting ensembles).
    """
    if preds is None or len(preds) == 0:
        return 1.0
    arr = np.asarray(preds, dtype=float).reshape(-1)
    if len(arr) == 1:
        return 1.0
    mean = float(np.mean(np.abs(arr)))
    std = float(np.std(arr))
    if mean < 1e-9:
        return 1.0
    cv = std / mean
    return float(max(0.0, min(1.0, 1.0 - cv)))
