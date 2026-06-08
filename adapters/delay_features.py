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
    """Match Fakeeh delay Flask proxy date parsing."""
    if not dt_str:
        return None
    text = str(dt_str).strip()
    for fmt in ("%m/%d/%Y %H:%M", "%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return _parse_datetime(dt_str)


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


def engineer_delay_features(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the wide feature row expected by delay_fakeeh_ksa_local (161 columns).
    """
    raw = normalize_delay_inputs(inputs)

    if _has_wide_features(raw):
        row = _blank_wide_row()
        for col in DELAY_WIDE_COLUMNS:
            if col in raw:
                row[col] = raw[col]
        return row

    return prepare_fakeeh_delay_model_input(raw)
