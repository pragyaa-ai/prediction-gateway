"""
Parse raw appointment payloads and engineer features for delay_fakeeh_ksa_local.

The 2025 KSA delay AutoML model expects a wide row (~161 columns) with one-hot
indicators (DEPARTMENT_*, TOKEN_NO_*, CITY_*, etc.) plus derived date fields.

Accepts flat integration JSON, SageMaker-style values matrix, or pre-engineered wide rows.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Set

from adapters.noshow_features import (
    NOSHOW_RAW_FIELDS_21,
    NOSHOW_RAW_FIELDS_23,
    _coerce_float,
    _extract_values_matrix,
    _parse_datetime,
    _values_row_to_dict,
)

# Column order from Fakeeh-Delay-Arrival_ksa/model.pkl (AutoML featurizer input)
DELAY_WIDE_COLUMNS: tuple[str, ...] = (
    "AGE_MONTHS",
    "ALLOCATION_DAY",
    "ALLOCATION_DAYOFWEEK",
    "ALLOCATION_HOUR",
    "ALLOCATION_MONTH",
    "ALLOCATION_PART_OF_DAY_PM",
    "APPT_BOOKING_CHANNEL_OTHERS",
    "APPT_BOOKING_CHANNEL_PORTAL",
    "CITY_MECCA",
    "CITY_Others",
    "CITY_RIYADH",
    "CITY_YANBU",
    "CONTRACT_NAME_Bupa Arabia - SABIC",
    "CONTRACT_NAME_Bupa Arabia - Saudi Aramco",
    "CONTRACT_NAME_Bupa Arabia - Saudi Aramco_2",
    "CONTRACT_NAME_Bupa Arabia Regular",
    "CONTRACT_NAME_Default (Cash Account)",
    "CONTRACT_NAME_Dr Suliman Fakeeh Hospital ( Staff Policy )",
    "CONTRACT_NAME_General Organization For Social Insurance(GOSI)",
    "CONTRACT_NAME_Globemed/Saudi Enaya Cooperative Insurance",
    "CONTRACT_NAME_MedGulf",
    "CONTRACT_NAME_NO_INFO",
    "CONTRACT_NAME_NO_INFO_3",
    "CONTRACT_NAME_Others",
    "CONTRACT_NAME_TCS/Arabian Shield",
    "CONTRACT_NAME_TCS/Cigna Worldwide Insurance Co.",
    "CONTRACT_NAME_Tawuniya",
    "DEPARTMENT_Adult Endocrinology",
    "DEPARTMENT_Adult Gastroenterology",
    "DEPARTMENT_Adult Hematology",
    "DEPARTMENT_Adult Nephrology",
    "DEPARTMENT_Adult Neurology",
    "DEPARTMENT_Adult Pulmonology And Respiratory Diseases",
    "DEPARTMENT_Adult Rheumatology",
    "DEPARTMENT_Allergology And Immunology",
    "DEPARTMENT_Anesthesia",
    "DEPARTMENT_Audiology",
    "DEPARTMENT_Cardiothoracic And Vascular Diseases",
    "DEPARTMENT_Chiropractic",
    "DEPARTMENT_Dental And Maxillofacial",
    "DEPARTMENT_Dermatology",
    "DEPARTMENT_Diabetology",
    "DEPARTMENT_Dietary Services",
    "DEPARTMENT_Ear, Nose, And Throat",
    "DEPARTMENT_Family Medicine",
    "DEPARTMENT_General And Laparoscopic Surgery",
    "DEPARTMENT_General Internal Medicine",
    "DEPARTMENT_General Pediatrics",
    "DEPARTMENT_Infectious Diseases",
    "DEPARTMENT_Khadija Attar Center for Special Needs",
    "DEPARTMENT_Medical Oncology",
    "DEPARTMENT_Neurosurgery",
    "DEPARTMENT_Obstetric And Gynecology",
    "DEPARTMENT_Ophthalmology",
    "DEPARTMENT_Orthopedics And Spine",
    "DEPARTMENT_Others",
    "DEPARTMENT_Pediatric And Neonatal ICU",
    "DEPARTMENT_Pediatric Cardiology",
    "DEPARTMENT_Pediatric Endocrinology",
    "DEPARTMENT_Pediatric Gastroenterology",
    "DEPARTMENT_Pediatric Infectious Disease",
    "DEPARTMENT_Pediatric Nephrology",
    "DEPARTMENT_Pediatric Pulmonology",
    "DEPARTMENT_Pediatric Surgery",
    "DEPARTMENT_Physical Medicine and Rehabilitation",
    "DEPARTMENT_Plastic Surgery",
    "DEPARTMENT_Psychiatry",
    "DEPARTMENT_Speech Therapy and Phoniatrics",
    "DEPARTMENT_Support Clinic",
    "DEPARTMENT_Urology",
    "DEPARTMENT_Vascular Surgery",
    "FACILITY_NAME_DSFH JEDDAH",
    "FACILITY_NAME_DSFH RIYADH",
    "FACILITY_NAME_DSFMC",
    "FOLLOW_NEW_N",
    "GENDER_Female",
    "GENDER_Male",
    "GIVEN_ON_DAYOFWEEK",
    "GIVEN_ON_HOUR",
    "LEAD_TIME_DAYS",
    "LEAD_TIME_MINUTES",
    "TOKEN_NO_11A",
    "TOKEN_NO_12A",
    "TOKEN_NO_13A",
    "TOKEN_NO_14A",
    "TOKEN_NO_15A",
    "TOKEN_NO_16A",
    "TOKEN_NO_17A",
    "TOKEN_NO_18A",
    "TOKEN_NO_19A",
    "TOKEN_NO_1A",
    "TOKEN_NO_20A",
    "TOKEN_NO_21A",
    "TOKEN_NO_22A",
    "TOKEN_NO_23A",
    "TOKEN_NO_24A",
    "TOKEN_NO_25A",
    "TOKEN_NO_26A",
    "TOKEN_NO_27A",
    "TOKEN_NO_28A",
    "TOKEN_NO_29A",
    "TOKEN_NO_2A",
    "TOKEN_NO_30A",
    "TOKEN_NO_31A",
    "TOKEN_NO_32A",
    "TOKEN_NO_33A",
    "TOKEN_NO_34A",
    "TOKEN_NO_35A",
    "TOKEN_NO_36A",
    "TOKEN_NO_37A",
    "TOKEN_NO_38A",
    "TOKEN_NO_39A",
    "TOKEN_NO_3A",
    "TOKEN_NO_40A",
    "TOKEN_NO_41A",
    "TOKEN_NO_42A",
    "TOKEN_NO_43A",
    "TOKEN_NO_44A",
    "TOKEN_NO_45A",
    "TOKEN_NO_46A",
    "TOKEN_NO_47A",
    "TOKEN_NO_48A",
    "TOKEN_NO_49A",
    "TOKEN_NO_4A",
    "TOKEN_NO_50A",
    "TOKEN_NO_51A",
    "TOKEN_NO_52A",
    "TOKEN_NO_53A",
    "TOKEN_NO_54A",
    "TOKEN_NO_55A",
    "TOKEN_NO_56A",
    "TOKEN_NO_57A",
    "TOKEN_NO_58A",
    "TOKEN_NO_59A",
    "TOKEN_NO_5A",
    "TOKEN_NO_60A",
    "TOKEN_NO_61A",
    "TOKEN_NO_62A",
    "TOKEN_NO_63A",
    "TOKEN_NO_64A",
    "TOKEN_NO_65A",
    "TOKEN_NO_66A",
    "TOKEN_NO_67A",
    "TOKEN_NO_68A",
    "TOKEN_NO_69A",
    "TOKEN_NO_6A",
    "TOKEN_NO_70A",
    "TOKEN_NO_71A",
    "TOKEN_NO_72A",
    "TOKEN_NO_73A",
    "TOKEN_NO_74A",
    "TOKEN_NO_75A",
    "TOKEN_NO_76A",
    "TOKEN_NO_7A",
    "TOKEN_NO_8A",
    "TOKEN_NO_9A",
    "VIP",
    "VISIT_METHOD_VIRTUAL",
    "VISIT_TYPE_CREDIT",
    "VISIT_TYPE_NO_INFO",
    "VISIT_TYPE_NO_INFO_1",
)

DELAY_WIDE_COLUMN_SET: Set[str] = set(DELAY_WIDE_COLUMNS)

# Fakeeh delay Flask proxy cloud schema (prepare_model_input column order)
FAKEEH_DELAY_STRING_COLUMNS: frozenset[str] = frozenset(
    {
        "CONTRACT_NAME_Bupa Arabia - Saudi Aramco_2",
        "CONTRACT_NAME_NO_INFO_3",
    }
)

FAKEEH_DELAY_MODEL_COLUMNS: tuple[str, ...] = (
    "AGE_MONTHS",
    "VIP",
    "ALLOCATION_MONTH",
    "ALLOCATION_DAY",
    "ALLOCATION_DAYOFWEEK",
    "ALLOCATION_HOUR",
    "LEAD_TIME_MINUTES",
    "LEAD_TIME_DAYS",
    "GIVEN_ON_DAYOFWEEK",
    "GIVEN_ON_HOUR",
    "DEPARTMENT_Adult Endocrinology",
    "DEPARTMENT_Adult Gastroenterology",
    "DEPARTMENT_Adult Hematology",
    "DEPARTMENT_Adult Nephrology",
    "DEPARTMENT_Adult Neurology",
    "DEPARTMENT_Adult Pulmonology And Respiratory Diseases",
    "DEPARTMENT_Adult Rheumatology",
    "DEPARTMENT_Allergology And Immunology",
    "DEPARTMENT_Anesthesia",
    "DEPARTMENT_Audiology",
    "DEPARTMENT_Cardiothoracic And Vascular Diseases",
    "DEPARTMENT_Chiropractic",
    "DEPARTMENT_Dental And Maxillofacial",
    "DEPARTMENT_Dermatology",
    "DEPARTMENT_Diabetology",
    "DEPARTMENT_Dietary Services",
    "DEPARTMENT_Ear, Nose, And Throat",
    "DEPARTMENT_Family Medicine",
    "DEPARTMENT_General And Laparoscopic Surgery",
    "DEPARTMENT_General Internal Medicine",
    "DEPARTMENT_General Pediatrics",
    "DEPARTMENT_Infectious Diseases",
    "DEPARTMENT_Khadija Attar Center for Special Needs",
    "DEPARTMENT_Medical Oncology",
    "DEPARTMENT_Neurosurgery",
    "DEPARTMENT_Obstetric And Gynecology",
    "DEPARTMENT_Ophthalmology",
    "DEPARTMENT_Orthopedics And Spine",
    "DEPARTMENT_Others",
    "DEPARTMENT_Pediatric And Neonatal ICU",
    "DEPARTMENT_Pediatric Cardiology",
    "DEPARTMENT_Pediatric Endocrinology",
    "DEPARTMENT_Pediatric Gastroenterology",
    "DEPARTMENT_Pediatric Infectious Disease",
    "DEPARTMENT_Pediatric Nephrology",
    "DEPARTMENT_Pediatric Pulmonology",
    "DEPARTMENT_Pediatric Surgery",
    "DEPARTMENT_Physical Medicine and Rehabilitation",
    "DEPARTMENT_Plastic Surgery",
    "DEPARTMENT_Psychiatry",
    "DEPARTMENT_Speech Therapy and Phoniatrics",
    "DEPARTMENT_Support Clinic",
    "DEPARTMENT_Urology",
    "DEPARTMENT_Vascular Surgery",
    "TOKEN_NO_11A",
    "TOKEN_NO_12A",
    "TOKEN_NO_13A",
    "TOKEN_NO_14A",
    "TOKEN_NO_15A",
    "TOKEN_NO_16A",
    "TOKEN_NO_17A",
    "TOKEN_NO_18A",
    "TOKEN_NO_19A",
    "TOKEN_NO_1A",
    "TOKEN_NO_20A",
    "TOKEN_NO_21A",
    "TOKEN_NO_22A",
    "TOKEN_NO_23A",
    "TOKEN_NO_24A",
    "TOKEN_NO_25A",
    "TOKEN_NO_26A",
    "TOKEN_NO_27A",
    "TOKEN_NO_28A",
    "TOKEN_NO_29A",
    "TOKEN_NO_2A",
    "TOKEN_NO_30A",
    "TOKEN_NO_31A",
    "TOKEN_NO_32A",
    "TOKEN_NO_33A",
    "TOKEN_NO_34A",
    "TOKEN_NO_35A",
    "TOKEN_NO_36A",
    "TOKEN_NO_37A",
    "TOKEN_NO_38A",
    "TOKEN_NO_39A",
    "TOKEN_NO_3A",
    "TOKEN_NO_40A",
    "TOKEN_NO_41A",
    "TOKEN_NO_42A",
    "TOKEN_NO_43A",
    "TOKEN_NO_44A",
    "TOKEN_NO_45A",
    "TOKEN_NO_46A",
    "TOKEN_NO_47A",
    "TOKEN_NO_48A",
    "TOKEN_NO_49A",
    "TOKEN_NO_4A",
    "TOKEN_NO_50A",
    "TOKEN_NO_51A",
    "TOKEN_NO_52A",
    "TOKEN_NO_53A",
    "TOKEN_NO_54A",
    "TOKEN_NO_55A",
    "TOKEN_NO_56A",
    "TOKEN_NO_57A",
    "TOKEN_NO_58A",
    "TOKEN_NO_59A",
    "TOKEN_NO_5A",
    "TOKEN_NO_60A",
    "TOKEN_NO_61A",
    "TOKEN_NO_62A",
    "TOKEN_NO_63A",
    "TOKEN_NO_64A",
    "TOKEN_NO_65A",
    "TOKEN_NO_66A",
    "TOKEN_NO_67A",
    "TOKEN_NO_68A",
    "TOKEN_NO_69A",
    "TOKEN_NO_6A",
    "TOKEN_NO_70A",
    "TOKEN_NO_71A",
    "TOKEN_NO_72A",
    "TOKEN_NO_73A",
    "TOKEN_NO_74A",
    "TOKEN_NO_75A",
    "TOKEN_NO_76A",
    "TOKEN_NO_7A",
    "TOKEN_NO_8A",
    "TOKEN_NO_9A",
    "FOLLOW_NEW_N",
    "FACILITY_NAME_DSFH JEDDAH",
    "FACILITY_NAME_DSFH RIYADH",
    "FACILITY_NAME_DSFMC",
    "GENDER_Female",
    "GENDER_Male",
    "VISIT_METHOD_VIRTUAL",
    "APPT_BOOKING_CHANNEL_OTHERS",
    "APPT_BOOKING_CHANNEL_PORTAL",
    "CITY_MECCA",
    "CITY_Others",
    "CITY_RIYADH",
    "CITY_YANBU",
    "VISIT_TYPE_CREDIT",
    "VISIT_TYPE_NO_INFO",
    "VISIT_TYPE_NO_INFO_1",
    "CONTRACT_NAME_Bupa Arabia - SABIC",
    "CONTRACT_NAME_Bupa Arabia - Saudi Aramco",
    "CONTRACT_NAME_Bupa Arabia - Saudi Aramco_2",
    "CONTRACT_NAME_Bupa Arabia Regular",
    "CONTRACT_NAME_Default (Cash Account)",
    "CONTRACT_NAME_Dr Suliman Fakeeh Hospital ( Staff Policy )",
    "CONTRACT_NAME_General Organization For Social Insurance(GOSI)",
    "CONTRACT_NAME_Globemed/Saudi Enaya Cooperative Insurance",
    "CONTRACT_NAME_MedGulf",
    "CONTRACT_NAME_NO_INFO",
    "CONTRACT_NAME_Others",
    "CONTRACT_NAME_Tawuniya",
    "CONTRACT_NAME_TCS/Arabian Shield",
    "CONTRACT_NAME_TCS/Cigna Worldwide Insurance Co.",
    "CONTRACT_NAME_NO_INFO_3",
    "ALLOCATION_PART_OF_DAY_PM",
)

# Aliases from upstream systems → canonical raw field names
_FIELD_ALIASES: Dict[str, str] = {
    "ALLOCATION_DATETIME": "ALLOCATION_DATE_TIME",
    "HOSPITAL_NAME": "FACILITY_NAME",
    "REMARKS": "REMARKS",
}

_CONTRACT_RULES: tuple[tuple[str, str], ...] = (
    ("SABIC", "CONTRACT_NAME_Bupa Arabia - SABIC"),
    ("SAUDI ARAMCO", "CONTRACT_NAME_Bupa Arabia - Saudi Aramco"),
    ("BUPA ARABIA REGULAR", "CONTRACT_NAME_Bupa Arabia Regular"),
    ("CASH", "CONTRACT_NAME_Default (Cash Account)"),
    ("STAFF POLICY", "CONTRACT_NAME_Dr Suliman Fakeeh Hospital ( Staff Policy )"),
    ("GOSI", "CONTRACT_NAME_General Organization For Social Insurance(GOSI)"),
    ("GLOBEMED", "CONTRACT_NAME_Globemed/Saudi Enaya Cooperative Insurance"),
    ("ENAYA", "CONTRACT_NAME_Globemed/Saudi Enaya Cooperative Insurance"),
    ("MEDGULF", "CONTRACT_NAME_MedGulf"),
    ("ARABIAN SHIELD", "CONTRACT_NAME_TCS/Arabian Shield"),
    ("CIGNA", "CONTRACT_NAME_TCS/Cigna Worldwide Insurance Co."),
    ("TAWUNIYA", "CONTRACT_NAME_Tawuniya"),
)


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

    normalized: Dict[str, Any] = {}
    for key, val in raw.items():
        canon = _FIELD_ALIASES.get(key, key)
        if val is None:
            val = ""
        normalized[canon] = val

    if "VIP" not in normalized and "ISVIP" in normalized:
        normalized["VIP"] = normalized["ISVIP"]

    return normalized


def _parse_age_years(val: Any) -> float:
    if val is None or val == "":
        return 0.0
    text = str(val).strip().lower().replace("years", "").replace("year", "")
    if text.endswith("y"):
        text = text[:-1]
    try:
        return float(text.strip())
    except ValueError:
        return _coerce_float(val)


def _day_name(dt: Optional[datetime], fallback: Any = "") -> str:
    if dt is not None:
        return dt.strftime("%A")
    fb = str(fallback or "").strip()
    if fb:
        return fb.title() if fb.isupper() else fb
    return ""


def _normalize_token(token: Any) -> str:
    return str(token or "").strip().upper().replace(" ", "")


def _set_one_hot(row: Dict[str, Any], columns: Iterable[str], prefix: str, value: Any, default_col: str) -> None:
    text = str(value or "").strip()
    target = f"{prefix}_{text}" if text else default_col
    if target not in DELAY_WIDE_COLUMN_SET:
        target = default_col
    for col in columns:
        if col.startswith(f"{prefix}_"):
            row[col] = 1 if col == target else 0


def _match_contract(contract: str) -> str:
    upper = contract.upper()
    if not contract.strip():
        return "CONTRACT_NAME_NO_INFO"
    for needle, col in _CONTRACT_RULES:
        if needle in upper:
            return col
    return "CONTRACT_NAME_Others"


def _match_facility(facility: str) -> str:
    upper = facility.upper()
    if "JEDDAH" in upper or "JED" in upper:
        return "FACILITY_NAME_DSFH JEDDAH"
    if "RIYADH" in upper or "RIY" in upper:
        return "FACILITY_NAME_DSFH RIYADH"
    return "FACILITY_NAME_DSFMC"


def _match_department(department: str) -> str:
    target = f"DEPARTMENT_{department.strip()}"
    if target in DELAY_WIDE_COLUMN_SET:
        return target
    return "DEPARTMENT_Others"


def _has_wide_features(raw: Dict[str, Any]) -> bool:
    hits = sum(1 for col in DELAY_WIDE_COLUMNS if col in raw)
    return hits >= max(10, len(DELAY_WIDE_COLUMNS) // 4)


def _blank_wide_row() -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    for col in DELAY_WIDE_COLUMNS:
        if col.startswith(("AGE_MONTHS", "LEAD_TIME", "ALLOCATION_HOUR", "ALLOCATION_MONTH", "VIP")):
            row[col] = 0
        elif col.startswith(("GIVEN_ON_HOUR", "ALLOCATION_PART_OF_DAY_PM")):
            row[col] = 0
        else:
            row[col] = 0 if col.startswith(
                ("DEPARTMENT_", "TOKEN_NO_", "CITY_", "CONTRACT_NAME_", "FACILITY_NAME_", "GENDER_", "FOLLOW_", "VISIT_")
            ) else ""
    return row


def _parse_fakeeh_delay_age(age_str: Any) -> float:
    """Match Fakeeh delay Flask proxy: '32y' -> months, '18m' -> months."""
    if not age_str:
        return 0.0
    text = str(age_str).strip().lower()
    if text.endswith("y"):
        return float(text[:-1]) * 12
    if text.endswith("m"):
        return float(text[:-1])
    return 0.0


def _parse_fakeeh_delay_datetime(dt_str: Any) -> Optional[datetime]:
    """Parse appointment datetimes (ISO, m/d/Y, d-m-Y, etc.) for delay feature engineering."""
    return _parse_datetime(dt_str)


def _parse_age_years_float(age_str: Any) -> float:
    """Age in years for Azure AutoML delay schema (AGE column)."""
    if not age_str:
        return 0.0
    text = str(age_str).strip().lower()
    if text.endswith("y"):
        return float(text[:-1])
    if text.endswith("m"):
        return float(text[:-1]) / 12.0
    try:
        return float(text)
    except ValueError:
        return 0.0


# Azure AutoML on-disk model (Fakeeh-Delay-Arrival_ksa/model.pkl) input schema — see MLmodel
DELAY_KSA_AUTOML_COLUMNS: tuple[str, ...] = (
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


def prepare_delay_ksa_automl_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map hospital appointment JSON → Fakeeh-Delay-Arrival_ksa Azure AutoML columns.

    This is the on-disk local model schema (MLmodel signature). The cloud Flask proxy
    uses a separate 161-column wide schema via prepare_fakeeh_delay_model_input().
    """
    provider = str(data.get("PROVIDER_NAME") or "")
    department = str(data.get("DEPARTMENT") or "")
    mrno_raw = data.get("MRNO", data.get("STATUS", ""))
    token = str(data.get("TOKEN_NO") or "")
    facility = str(data.get("FACILITY_NAME") or data.get("HOSPITAL_NAME") or "")

    try:
        appt_id = int(data.get("APPT_ALLOCATION_ID") or 0)
    except (TypeError, ValueError):
        appt_id = 0

    try:
        mrno_details = float(mrno_raw) if mrno_raw not in (None, "") else 0.0
    except (TypeError, ValueError):
        mrno_details = 0.0

    alloc_dt = _parse_fakeeh_delay_datetime(data.get("ALLOCATION_DATE_TIME"))

    gender = str(data.get("GENDER") or "").strip().lower()
    if gender in ("female", "f"):
        gender_enc = 1.0
    elif gender in ("male", "m"):
        gender_enc = 0.0
    else:
        gender_enc = -1.0

    visit_method = str(data.get("VISIT_METHOD") or "").lower()
    visit_method_enc = 1.0 if "virtual" in visit_method else 0.0

    row: Dict[str, Any] = {
        "HOSPITAL_ID_details": 1.0,
        "PROVIDER_NAME_details": provider,
        "DEPARTMENT_details": department,
        "MRNO_details": mrno_details,
        "TOKEN_NO_details": token,
        "APPT_ALLOCATION_ID": appt_id,
        "FACILITY_NAME_details": facility,
        "PROVIDER_NAME_delay": provider,
        "DEPARTMENT_delay": department,
        "MRNO_delay": str(mrno_raw or ""),
        "TOKEN_NO_delay": token,
        "HOSPITAL_ID_delay": "1",
        "FACILITY_NAME_delay": facility,
        "ALLOCATION_DATETIME": alloc_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if alloc_dt else "",
        "ALLOCATION_HOUR": alloc_dt.hour if alloc_dt else 0,
        "ALLOCATION_DAY_OF_WEEK": alloc_dt.isoweekday() if alloc_dt else 0,
        "ALLOCATION_MONTH": alloc_dt.month if alloc_dt else 0,
        "IS_WEEKEND": 1 if alloc_dt and alloc_dt.isoweekday() >= 6 else 0,
        "AGE": _parse_age_years_float(data.get("AGE")),
        "GENDER_ENCODED": gender_enc,
        "STATUS_ENCODED": -1.0,
        "VISIT_METHOD_ENCODED": visit_method_enc,
        "PAYMENT_STATUS_ENCODED": -1.0,
    }
    return row


def prepare_fakeeh_delay_model_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Replicate Fakeeh delay Flask proxy prepare_model_input() for cloud + local parity.

    Returns a flat wide row dict (161 features) keyed by model column names.
    """
    row: Dict[str, Any] = {}
    for col in FAKEEH_DELAY_MODEL_COLUMNS:
        row[col] = "" if col in FAKEEH_DELAY_STRING_COLUMNS else 0

    row["AGE_MONTHS"] = float(_parse_fakeeh_delay_age(data.get("AGE")))
    row["VIP"] = int(data.get("VIP", 0) or 0)

    allocation_datetime = _parse_fakeeh_delay_datetime(data.get("ALLOCATION_DATE_TIME"))
    given_on_datetime = _parse_fakeeh_delay_datetime(data.get("GIVEN_ON"))

    if allocation_datetime:
        row["ALLOCATION_MONTH"] = allocation_datetime.month
        row["ALLOCATION_DAY"] = allocation_datetime.day
        row["ALLOCATION_DAYOFWEEK"] = allocation_datetime.isoweekday()
        row["ALLOCATION_HOUR"] = allocation_datetime.hour

    if given_on_datetime:
        row["GIVEN_ON_DAYOFWEEK"] = given_on_datetime.isoweekday()
        row["GIVEN_ON_HOUR"] = given_on_datetime.hour

    if allocation_datetime and given_on_datetime:
        lead_time_minutes = (allocation_datetime - given_on_datetime).total_seconds() / 60.0
        row["LEAD_TIME_MINUTES"] = float(lead_time_minutes)
        row["LEAD_TIME_DAYS"] = float(lead_time_minutes / 1440.0)

    def one_hot(prefix: str, value: Any) -> None:
        if not value:
            return
        key = f"{prefix}_{value}"
        if key not in row:
            return
        if key in FAKEEH_DELAY_STRING_COLUMNS:
            row[key] = value
        else:
            row[key] = 1

    one_hot("DEPARTMENT", data.get("DEPARTMENT"))
    one_hot("TOKEN_NO", data.get("TOKEN_NO"))
    one_hot("FACILITY_NAME", data.get("FACILITY_NAME"))
    one_hot("GENDER", data.get("GENDER"))
    one_hot("VISIT_METHOD", data.get("VISIT_METHOD"))
    one_hot("APPT_BOOKING_CHANNEL", data.get("APPT_BOOKING_CHANNEL"))
    one_hot("CITY", data.get("CITY"))
    one_hot("VISIT_TYPE", data.get("VISIT_TYPE"))
    one_hot("CONTRACT_NAME", data.get("CONTRACT_NAME"))

    if data.get("FOLLOW_NEW") == "N":
        row["FOLLOW_NEW_N"] = 1

    if allocation_datetime and allocation_datetime.hour >= 12:
        row["ALLOCATION_PART_OF_DAY_PM"] = 1

    return row


def prepare_fakeeh_delay_cloud_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Cloud API Gateway body: {"Inputs": {"data": [row]}, "GlobalParameters": 0}."""
    return {
        "Inputs": {"data": [prepare_fakeeh_delay_model_input(data)]},
        "GlobalParameters": 0,
    }


def _is_hospital_appointment(raw: Dict[str, Any]) -> bool:
    """True when payload is raw Fakeeh appointment JSON (not pre-engineered wide row)."""
    return any(
        k in raw
        for k in (
            "ALLOCATION_DATE_TIME",
            "ALLOCATION_DATETIME",
            "MRNO",
            "PROVIDER_NAME",
            "APPT_ALLOCATION_ID",
        )
    )


def _wide_row_from_engineered(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure a complete 161-column wide row for delay_fakeeh_ksa_local model.pkl."""
    # Always engineer from hospital JSON when present (avoids mangling wide rows through automl).
    if _is_hospital_appointment(raw):
        return prepare_fakeeh_delay_model_input(raw)
    if _has_wide_features(raw):
        row: Dict[str, Any] = {}
        for col in FAKEEH_DELAY_MODEL_COLUMNS:
            if col in raw:
                row[col] = raw[col]
            elif col in FAKEEH_DELAY_STRING_COLUMNS:
                row[col] = ""
            else:
                row[col] = 0
        return row
    return prepare_fakeeh_delay_model_input(raw)


def engineer_delay_features(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build input row for delay_fakeeh_ksa_local (161-column wide schema in model.pkl).
    """
    raw = normalize_delay_inputs(inputs)
    return _wide_row_from_engineered(raw)
