"""SageMaker Canvas CSV prediction string formatters and parsers."""
from __future__ import annotations

import ast
import csv
import io
from typing import Any, Dict, List, Optional, Sequence, Tuple

NOSHOW_CLASS_LABELS: Tuple[str, str] = ("Show", "No Show")
REGRESSION_CLASS_LABELS: Tuple[str, ...] = ()


def _format_float(value: float) -> str:
    return format(float(value), ".15g")


def format_classification_prediction(
    predicted_label: str,
    probabilities: Sequence[float],
    class_labels: Sequence[str] = NOSHOW_CLASS_LABELS,
) -> str:
    """
    SageMaker Canvas classification CSV line, e.g.
    Show,0.659...,"[0.659..., 0.340...]","['Show', 'No Show']"
    """
    labels = list(class_labels)
    idx = labels.index(predicted_label) if predicted_label in labels else 0
    pred_score = float(probabilities[idx])
    proba_inner = ", ".join(_format_float(p) for p in probabilities)
    proba_str = f"[{proba_inner}]"
    labels_str = str(labels)
    return f'{predicted_label},{_format_float(pred_score)},"{proba_str}","{labels_str}"\n'


def format_regression_prediction(
    value: float,
    confidence: Optional[float] = None,
) -> str:
    """
    SageMaker Canvas numeric/regression CSV line, e.g.
    2.45,0.88,"[2.45]","[]"
    """
    val = _format_float(value)
    conf = _format_float(confidence if confidence is not None else 1.0)
    values_str = f"[{val}]"
    labels_str = str(list(REGRESSION_CLASS_LABELS))
    return f'{val},{conf},"{values_str}","{labels_str}"\n'


def parse_classification_prediction(text: str) -> Optional[Dict[str, Any]]:
    """Parse SageMaker classification CSV prediction string."""
    if not text or not isinstance(text, str) or "," not in text:
        return None
    try:
        row = next(csv.reader(io.StringIO(text.strip())))
        if len(row) < 4:
            return None
        class_labels = ast.literal_eval(row[3])
        if not isinstance(class_labels, list) or not class_labels:
            return None
        if not any(isinstance(label, str) and not label.replace(".", "", 1).isdigit() for label in class_labels):
            return None

        label = row[0]
        pred_score = float(row[1])
        probabilities = ast.literal_eval(row[2]) if len(row) > 2 else []
        no_show_prob = None
        if probabilities and class_labels:
            if "No Show" in class_labels:
                no_show_prob = float(probabilities[class_labels.index("No Show")])
            elif len(probabilities) > 1:
                no_show_prob = float(probabilities[1])

        formatted = text if text.endswith("\n") else f"{text.strip()}\n"
        return {
            "prediction": formatted,
            "predicted_label": label,
            "score": pred_score,
            "no_show_probability": no_show_prob,
            "probabilities": [float(p) for p in probabilities] if probabilities else None,
            "class_labels": list(class_labels),
        }
    except (ValueError, SyntaxError, StopIteration):
        return None


def parse_regression_prediction(text: str) -> Optional[Dict[str, Any]]:
    """Parse SageMaker numeric/regression CSV prediction string."""
    if not text or not isinstance(text, str) or "," not in text:
        return None
    try:
        row = next(csv.reader(io.StringIO(text.strip())))
        if len(row) < 2:
            return None

        predicted_value = float(row[0])
        confidence = float(row[1])
        values: List[float] = []
        if len(row) > 2 and row[2]:
            parsed_values = ast.literal_eval(row[2])
            if isinstance(parsed_values, list):
                values = [float(v) for v in parsed_values]
        if not values:
            values = [predicted_value]

        formatted = text if text.endswith("\n") else f"{text.strip()}\n"
        return {
            "prediction": formatted,
            "predicted_value": predicted_value,
            "score": confidence,
            "confidence": confidence,
            "values": values,
        }
    except (ValueError, SyntaxError, StopIteration):
        return None


def parse_sagemaker_prediction(text: str) -> Optional[Dict[str, Any]]:
    """Parse SageMaker CSV prediction (classification or regression)."""
    parsed = parse_classification_prediction(text)
    if parsed:
        return parsed
    return parse_regression_prediction(text)


def regression_output_from_response(
    response: Dict[str, Any],
    *,
    value_key: str = "prediction",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build mapper output with SageMaker regression CSV in prediction."""
    raw_prediction = response.get(value_key)
    confidence = response.get(
        "score",
        response.get("probability", response.get("confidence")),
    )

    if isinstance(raw_prediction, str):
        parsed = parse_sagemaker_prediction(raw_prediction)
        if parsed:
            out = dict(parsed)
            if extra:
                out.update(extra)
            return out

    try:
        value = float(raw_prediction)
    except (TypeError, ValueError):
        out = {
            "prediction": str(raw_prediction),
            "score": confidence,
            "confidence": confidence,
        }
        if extra:
            out.update(extra)
        return out

    out = {
        "prediction": format_regression_prediction(value, confidence),
        "predicted_value": value,
        "score": confidence,
        "confidence": confidence,
    }
    if extra:
        out.update(extra)
    return out
