"""
Parse raw appointment payloads and engineer features for no_show_fakeeh_ksa_local.

Accepts:
  - SageMaker-style nested payload: {"data": {"features": {"values": [[...]]}}}
  - Flat dict with field names (PROVIDER_NAME, DEPARTMENT, ...)
  - Pre-engineered 48-feature dict (passed through with defaults for missing)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple
import ast
import csv
import io

import numpy as np

NOSHOW_CLASS_LABELS: Tuple[str, str] = ("Show", "No Show")

# Standard 21-field appointment order (cloud / SageMaker schema)
NOSHOW_RAW_FIELDS_21: tuple[str, ...] = (
    "PROVIDER_NAME",
    "DEPARTMENT",
    "ALLOCATION_DATE_TIME",
    "ALLOCATION_DAY",
    "MRNO",
    "TOKEN_NO",
    "GIVEN_BY",
    "FOLLOW_NEW",
    "AGE",
    "REMARKS",
    "APPT_ALLOCATION_ID",
    "FACILITY_NAME",
    "GENDER",
    "VISIT_METHOD",
    "GIVEN_ON",
    "DOCTORS_NATIONALITY",
    "APPT_BOOKING_CHANNEL",
    "CITY",
    "VISIT_TYPE",
    "CONTRACT_NAME",
    "PAYMENT_STATUS",
)

# Extended 23-field schema (adds patient NATIONALITY + ISVIP after APPT_ALLOCATION_ID)
NOSHOW_RAW_FIELDS_23: tuple[str, ...] = (
    "PROVIDER_NAME",
    "DEPARTMENT",
    "ALLOCATION_DATE_TIME",
    "ALLOCATION_DAY",
    "MRNO",
    "TOKEN_NO",
    "GIVEN_BY",
    "FOLLOW_NEW",
    "AGE",
    "REMARKS",
    "APPT_ALLOCATION_ID",
    "NATIONALITY",
    "ISVIP",
    "FACILITY_NAME",
    "GENDER",
    "VISIT_METHOD",
    "GIVEN_ON",
    "DOCTORS_NATIONALITY",
    "APPT_BOOKING_CHANNEL",
    "CITY",
    "VISIT_TYPE",
    "CONTRACT_NAME",
    "PAYMENT_STATUS",
)

_DATETIME_FORMATS = (
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
)


def _coerce_float(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    if isinstance(val, bool):
        return 1.0 if val else 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _parse_datetime(val: Any) -> Optional[datetime]:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val)
        except (OSError, ValueError, OverflowError):
            return None
    text = str(val).strip()
    if not text:
        return None
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _values_row_to_dict(values: List[Any]) -> Dict[str, Any]:
    n = len(values)
    if n == len(NOSHOW_RAW_FIELDS_23):
        fields = NOSHOW_RAW_FIELDS_23
    elif n == len(NOSHOW_RAW_FIELDS_21):
        fields = NOSHOW_RAW_FIELDS_21
    else:
        # Best-effort: map by position up to known schema length, ignore extras
        fields = NOSHOW_RAW_FIELDS_23 if n > len(NOSHOW_RAW_FIELDS_21) else NOSHOW_RAW_FIELDS_21
    raw: Dict[str, Any] = {}
    for i, name in enumerate(fields):
        if i < n:
            raw[name] = values[i]
    return raw


def _extract_values_matrix(inputs: Dict[str, Any]) -> Optional[List[List[Any]]]:
    data = inputs.get("data")
    if not isinstance(data, dict):
        return None
    features = data.get("features")
    if not isinstance(features, dict):
        return None
    values = features.get("values")
    if not isinstance(values, list) or not values:
        return None
    if isinstance(values[0], list):
        return values
    return [values]


def normalize_noshow_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize gateway inputs to a flat appointment field dict.

    Supports nested SageMaker format, flat named fields, or pre-engineered features.
    """
    if not isinstance(inputs, dict):
        return {}

    # Nested: {"data":{"features":{"values":[[...]]}}}
    matrix = _extract_values_matrix(inputs)
    if matrix is not None:
        return _values_row_to_dict(matrix[0])

    # Nested under "inputs" (double-wrapped)
    inner = inputs.get("inputs")
    if isinstance(inner, dict):
        matrix = _extract_values_matrix(inner)
        if matrix is not None:
            return _values_row_to_dict(matrix[0])
        if any(k in inner for k in NOSHOW_RAW_FIELDS_21):
            return dict(inner)

    # Already flat raw appointment fields
    if any(k in inputs for k in NOSHOW_RAW_FIELDS_21):
        return dict(inputs)

    # Pre-engineered feature vector – return as-is
    return dict(inputs)


def _label_encode(label_encoders: Dict[str, Any], col: str, val: Any, default: float = 0.0) -> float:
    le = label_encoders.get(col)
    if le is None or val is None or val == "":
        return default
    text = str(val).strip()
    if not text:
        return default
    classes = getattr(le, "classes_", None)
    if classes is None:
        return default
    if text in classes:
        return float(le.transform([text])[0])
    # Case-insensitive fallback
    upper_map = {str(c).upper(): c for c in classes}
    match = upper_map.get(text.upper())
    if match is not None:
        return float(le.transform([match])[0])
    return default


def _has_engineered_features(inputs: Dict[str, Any], feature_names: List[str]) -> bool:
    """True when caller sent the 48 numeric model columns directly."""
    hits = sum(1 for name in feature_names if name in inputs)
    return hits >= max(10, len(feature_names) // 2)


def engineer_noshow_features(
    inputs: Dict[str, Any],
    bundle: Dict[str, Any],
) -> Dict[str, float]:
    """
    Build the 48-feature row expected by the local XGBoost bundle.

    Missing / unknown values default to 0.
    """
    feature_names: List[str] = list(bundle["feature_names"])
    label_encoders: Dict[str, Any] = bundle.get("label_encoders") or {}

    raw = normalize_noshow_inputs(inputs)
    features: Dict[str, float] = {name: 0.0 for name in feature_names}

    # Pre-engineered payload – fill what was sent, default rest to 0
    if _has_engineered_features(raw, feature_names):
        for name in feature_names:
            if name in raw:
                features[name] = _coerce_float(raw.get(name))
        return features

    # --- Map raw appointment row to model features ---
    try:
        features["MRNO"] = _coerce_float(raw.get("MRNO"))
    except (TypeError, ValueError):
        features["MRNO"] = 0.0

    features["ISVIP"] = _coerce_float(raw.get("ISVIP"))

    gender = str(raw.get("GENDER", "")).strip().upper()
    if gender in ("M", "MALE"):
        features["is_male"] = 1.0
        features["GENDER"] = _label_encode(label_encoders, "GENDER", "Male")
    elif gender in ("F", "FEMALE"):
        features["is_female"] = 1.0
        features["GENDER"] = _label_encode(label_encoders, "GENDER", "Female")
    else:
        features["GENDER"] = _label_encode(label_encoders, "GENDER", raw.get("GENDER"))

    remarks = str(raw.get("REMARKS", "")).upper()
    channel = str(raw.get("APPT_BOOKING_CHANNEL", "")).upper()
    visit_method = str(raw.get("VISIT_METHOD", "")).upper()
    appt_mode_val = None
    if "WALK" in remarks or "WALK" in channel:
        appt_mode_val = "WALK-IN"
    elif "VIRTUAL" in visit_method or "VIRTUAL" in channel:
        appt_mode_val = "VIRTUAL"
    elif "APP" in channel:
        appt_mode_val = "APP"
    features["APPT_MODE"] = _label_encode(label_encoders, "APPT_MODE", appt_mode_val)

    follow = str(raw.get("FOLLOW_NEW", "")).strip().upper()
    if follow in ("N", "NEW"):
        features["NEW_OLD_PATIENT"] = _label_encode(label_encoders, "NEW_OLD_PATIENT", "NEW")
    elif follow in ("F", "OLD", "FOLLOW"):
        features["NEW_OLD_PATIENT"] = _label_encode(label_encoders, "NEW_OLD_PATIENT", "OLD")

    features["DEPARTMENT"] = _label_encode(label_encoders, "DEPARTMENT", raw.get("DEPARTMENT"))
    features["VISIT_TYPE"] = _label_encode(label_encoders, "VISIT_TYPE", raw.get("VISIT_TYPE"))
    features["DATA_SOURCE"] = _label_encode(label_encoders, "DATA_SOURCE", raw.get("DATA_SOURCE"))

    appt_dt = _parse_datetime(raw.get("ALLOCATION_DATE_TIME"))
    given_dt = _parse_datetime(raw.get("GIVEN_ON"))

    if appt_dt is not None:
        features["appt_day_of_week"] = float(appt_dt.weekday())
        features["appt_month"] = float(appt_dt.month)
        features["appt_hour"] = float(appt_dt.hour)
        features["is_weekend"] = 1.0 if appt_dt.weekday() >= 5 else 0.0
        features["is_monday"] = 1.0 if appt_dt.weekday() == 0 else 0.0
        features["is_friday"] = 1.0 if appt_dt.weekday() == 4 else 0.0
        features["is_morning"] = 1.0 if appt_dt.hour < 12 else 0.0
        features["is_evening"] = 1.0 if appt_dt.hour >= 17 else 0.0
        features["is_lunch_time"] = 1.0 if 12 <= appt_dt.hour < 14 else 0.0
        features["is_summer"] = 1.0 if appt_dt.month in (6, 7, 8) else 0.0
        features["is_holiday_season"] = 1.0 if appt_dt.month in (12, 1) else 0.0

    if given_dt is not None:
        features["given_day_of_week"] = float(given_dt.weekday())
        features["is_weekend_booking"] = 1.0 if given_dt.weekday() >= 5 else 0.0

    if appt_dt is not None and given_dt is not None:
        diff_days = max((appt_dt - given_dt).total_seconds() / 86400.0, 0.0)
        features["DIFFERENCE"] = diff_days
        features["same_day"] = 1.0 if appt_dt.date() == given_dt.date() else 0.0
        features["short_notice"] = 1.0 if diff_days < 1.0 else 0.0
        features["long_advance"] = 1.0 if diff_days > 30.0 else 0.0
        if diff_days < 3.0:
            features["booking_urgency"] = _label_encode(label_encoders, "booking_urgency", "urgent")
        elif diff_days > 14.0:
            features["booking_urgency"] = _label_encode(label_encoders, "booking_urgency", "planned")

    visit_type = str(raw.get("VISIT_TYPE", "")).upper()
    payment = str(raw.get("PAYMENT_STATUS", "")).upper()
    if "CREDIT" in visit_type:
        features["is_credit"] = 1.0
    if "CASH" in visit_type or "SELF" in visit_type:
        features["is_cash"] = 1.0
    if "SELF" in payment or "CASH" in payment:
        features["IS_SELF_PAY"] = 1.0

    nat = str(raw.get("NATIONALITY") or raw.get("DOCTORS_NATIONALITY") or "").upper()
    if nat:
        if "SAUDI" in nat or nat in ("SA", "KSA"):
            features["is_local"] = 1.0
            features["is_common_nationality"] = 1.0
        if nat in ("EGYPTIAN", "INDIAN", "PAKISTANI", "YEMENI", "JORDANIAN"):
            features["is_common_nationality"] = 1.0

    if "EMERGENCY" in remarks or "EMERGENCY" in str(raw.get("VISIT_TYPE", "")).upper():
        features["is_emergency"] = 1.0
    else:
        features["is_routine"] = 1.0

    # Allow explicit overrides for any engineered column
    for name in feature_names:
        if name in raw and name not in NOSHOW_RAW_FIELDS_21 and name not in NOSHOW_RAW_FIELDS_23:
            features[name] = _coerce_float(raw[name])

    return features


def noshow_class_label(class_value: Any) -> str:
    """Map model class (0/1) to SageMaker label."""
    if class_value in (0, "0", "Show", "SHOW", "show"):
        return "Show"
    if class_value in (1, "1", "No Show", "NO_SHOW", "NO SHOW", "no show"):
        return "No Show"
    return str(class_value)


def format_noshow_sagemaker_prediction(
    predicted_label: str,
    probabilities: Sequence[float],
    class_labels: Sequence[str] = NOSHOW_CLASS_LABELS,
) -> str:
    """
    SageMaker Canvas CSV line, e.g.
    Show,0.659...,"[0.659..., 0.340...]","['Show', 'No Show']"
    """
    labels = list(class_labels)
    idx = labels.index(predicted_label) if predicted_label in labels else 0
    pred_score = float(probabilities[idx])
    proba_inner = ", ".join(str(float(p)) for p in probabilities)
    proba_str = f"[{proba_inner}]"
    labels_str = str(labels)
    return f'{predicted_label},{pred_score},"{proba_str}","{labels_str}"\n'


def parse_noshow_sagemaker_prediction(text: str) -> Optional[Dict[str, Any]]:
    """Parse SageMaker CSV prediction string into structured fields."""
    if not text or not isinstance(text, str) or "," not in text:
        return None
    try:
        row = next(csv.reader(io.StringIO(text.strip())))
        if len(row) < 2:
            return None
        label = row[0]
        pred_score = float(row[1])
        probabilities = ast.literal_eval(row[2]) if len(row) > 2 else []
        class_labels = ast.literal_eval(row[3]) if len(row) > 3 else list(NOSHOW_CLASS_LABELS)
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
            "class_labels": list(class_labels) if class_labels else list(NOSHOW_CLASS_LABELS),
        }
    except (ValueError, SyntaxError, StopIteration):
        return None
