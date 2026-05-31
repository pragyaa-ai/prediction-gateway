"""
Parse raw appointment payloads and engineer features for delay_fakeeh_ksa_local.

Accepts flat integration JSON (MRNO, PROVIDER_NAME, ALLOCATION_DATE_TIME, ...)
or SageMaker-style {"data": {"features": {"values": [[...]]}}}.
Missing fields default to 0 / empty / -1 for encoded columns.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from adapters.noshow_features import (
    NOSHOW_RAW_FIELDS_21,
    NOSHOW_RAW_FIELDS_23,
    _coerce_float,
    _extract_values_matrix,
    _parse_datetime,
    _values_row_to_dict,
)

# Aliases from upstream systems → canonical raw field names
_FIELD_ALIASES: Dict[str, str] = {
    "ALLOCATION_DATETIME": "ALLOCATION_DATE_TIME",
    "HOSPITAL_NAME": "FACILITY_NAME",
    "VIP": "ISVIP",
    "REMARKS": "REMARKS",
}


def normalize_delay_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize gateway inputs to flat appointment field dict."""
    if not isinstance(inputs, dict):
        return {}

    matrix = _extract_values_matrix(inputs)
    if matrix is not None:
        raw = _values_row_to_dict(matrix[0])
    elif isinstance(inputs.get("inputs"), dict):
        inner = inputs["inputs"]
        matrix = _extract_values_matrix(inner)
        raw = _values_row_to_dict(matrix[0]) if matrix else dict(inner)
    elif any(k in inputs for k in NOSHOW_RAW_FIELDS_21):
        raw = dict(inputs)
    else:
        raw = dict(inputs)

    # Apply aliases and drop nulls to empty string where helpful
    normalized: Dict[str, Any] = {}
    for key, val in raw.items():
        canon = _FIELD_ALIASES.get(key, key)
        if val is None:
            val = ""
        normalized[canon] = val

    return normalized


def _parse_age(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    text = str(val).strip().lower().replace("years", "").replace("year", "")
    if text.endswith("y"):
        text = text[:-1]
    try:
        return float(text.strip())
    except ValueError:
        return _coerce_float(val)


def _encode_gender(val: Any) -> float:
    g = str(val or "").strip().upper()
    if g in ("M", "MALE"):
        return 0.0
    if g in ("F", "FEMALE"):
        return 1.0
    return -1.0


def _encode_visit_method(val: Any) -> float:
    v = str(val or "").strip().upper()
    if not v:
        return -1.0
    if "PHYSICAL" in v or "IN-PERSON" in v or "IN PERSON" in v:
        return 0.0
    if "VIRTUAL" in v or "TELE" in v or "ONLINE" in v:
        return 1.0
    return 0.0


def _encode_payment_status(val: Any) -> float:
    p = str(val or "").strip().upper()
    if not p:
        return -1.0
    if "NOT PAID" in p or "UNPAID" in p:
        return 0.0
    if "PAID" in p:
        return 1.0
    return -1.0


def _encode_status(raw: Dict[str, Any]) -> float:
    """Best-effort STATUS_ENCODED from VIP / FOLLOW_NEW when no explicit status."""
    if raw.get("STATUS_ENCODED") not in (None, ""):
        return _coerce_float(raw.get("STATUS_ENCODED"))
    if _coerce_float(raw.get("ISVIP") or raw.get("VIP")) > 0:
        return 1.0
    follow = str(raw.get("FOLLOW_NEW", "")).strip().upper()
    if follow in ("N", "NEW"):
        return 0.0
    if follow in ("F", "OLD", "FOLLOW"):
        return 1.0
    return -1.0


def engineer_delay_features(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map raw appointment fields to the Azure AutoML delay pipeline column names.
    """
    raw = normalize_delay_inputs(inputs)

    engineered_keys = (
        "HOSPITAL_ID_details",
        "PROVIDER_NAME_details",
        "DEPARTMENT_details",
        "MRNO_details",
        "TOKEN_NO_details",
        "APPT_ALLOCATION_ID",
        "FACILITY_NAME_details",
        "PROVIDER_NAME_delay",
        "DEPARTMENT_delay",
        "MRNO_delay",
        "TOKEN_NO_delay",
        "HOSPITAL_ID_delay",
        "FACILITY_NAME_delay",
        "ALLOCATION_DATETIME",
        "ALLOCATION_HOUR",
        "ALLOCATION_DAY_OF_WEEK",
        "ALLOCATION_MONTH",
        "IS_WEEKEND",
        "AGE",
        "GENDER_ENCODED",
        "STATUS_ENCODED",
        "VISIT_METHOD_ENCODED",
        "PAYMENT_STATUS_ENCODED",
    )

    # Already-engineered payload – only when hallmark pipeline columns are present
    _pass_through_markers = (
        "HOSPITAL_ID_details",
        "PROVIDER_NAME_details",
        "MRNO_details",
        "ALLOCATION_DATETIME",
        "GENDER_ENCODED",
        "VISIT_METHOD_ENCODED",
        "PAYMENT_STATUS_ENCODED",
    )
    if any(k in raw for k in _pass_through_markers):
        return {k: raw.get(k, 0) for k in engineered_keys}

    appt_dt = _parse_datetime(
        raw.get("ALLOCATION_DATE_TIME") or raw.get("ALLOCATION_DATETIME")
    )

    provider = str(raw.get("PROVIDER_NAME", "") or "")
    department = str(raw.get("DEPARTMENT", "") or "")
    mrno = str(raw.get("MRNO", "") or "")
    token = str(raw.get("TOKEN_NO", "") or "")
    facility = str(raw.get("FACILITY_NAME", "") or raw.get("HOSPITAL_NAME", "") or "")
    hospital_id = _coerce_float(raw.get("HOSPITAL_ID") or raw.get("HOSPITAL_ID_details") or 1.0)

    appt_dt_str = raw.get("ALLOCATION_DATE_TIME") or raw.get("ALLOCATION_DATETIME") or ""
    if appt_dt is not None and not appt_dt_str:
        appt_dt_str = appt_dt.isoformat()

    return {
        "HOSPITAL_ID_details": hospital_id,
        "PROVIDER_NAME_details": provider,
        "DEPARTMENT_details": department,
        "MRNO_details": mrno,
        "TOKEN_NO_details": token,
        "APPT_ALLOCATION_ID": str(raw.get("APPT_ALLOCATION_ID", "") or ""),
        "FACILITY_NAME_details": facility,
        "PROVIDER_NAME_delay": provider,
        "DEPARTMENT_delay": department,
        "MRNO_delay": mrno,
        "TOKEN_NO_delay": token,
        "HOSPITAL_ID_delay": hospital_id,
        "FACILITY_NAME_delay": facility,
        "ALLOCATION_DATETIME": appt_dt_str,
        "ALLOCATION_HOUR": float(appt_dt.hour) if appt_dt else 0.0,
        "ALLOCATION_DAY_OF_WEEK": float(appt_dt.weekday()) if appt_dt else 0.0,
        "ALLOCATION_MONTH": float(appt_dt.month) if appt_dt else 0.0,
        "IS_WEEKEND": 1.0 if appt_dt and appt_dt.weekday() >= 5 else 0.0,
        "AGE": _parse_age(raw.get("AGE")),
        "GENDER_ENCODED": _encode_gender(raw.get("GENDER")),
        "STATUS_ENCODED": _encode_status(raw),
        "VISIT_METHOD_ENCODED": _encode_visit_method(raw.get("VISIT_METHOD")),
        "PAYMENT_STATUS_ENCODED": _encode_payment_status(raw.get("PAYMENT_STATUS")),
    }
