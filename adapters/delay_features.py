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

    row = _blank_wide_row()

    alloc_dt = _parse_datetime(raw.get("ALLOCATION_DATE_TIME") or raw.get("ALLOCATION_DATETIME"))
    given_dt = _parse_datetime(raw.get("GIVEN_ON"))

    age_years = _parse_age_years(raw.get("AGE"))
    row["AGE_MONTHS"] = age_years * 12.0

    if alloc_dt and given_dt:
        delta_min = max(0.0, (alloc_dt - given_dt).total_seconds() / 60.0)
        row["LEAD_TIME_MINUTES"] = delta_min
        row["LEAD_TIME_DAYS"] = delta_min / (60.0 * 24.0)

    row["ALLOCATION_DAY"] = _day_name(alloc_dt, raw.get("ALLOCATION_DAY"))
    row["ALLOCATION_DAYOFWEEK"] = _day_name(alloc_dt, raw.get("ALLOCATION_DAY"))
    row["ALLOCATION_HOUR"] = alloc_dt.hour if alloc_dt else 0
    row["ALLOCATION_MONTH"] = alloc_dt.month if alloc_dt else 0
    row["ALLOCATION_PART_OF_DAY_PM"] = 1 if alloc_dt and alloc_dt.hour >= 12 else 0

    row["GIVEN_ON_DAYOFWEEK"] = _day_name(given_dt, "")
    row["GIVEN_ON_HOUR"] = given_dt.hour if given_dt else 0

    vip_val = raw.get("ISVIP", raw.get("VIP", 0))
    row["VIP"] = 1 if str(vip_val).strip() in ("1", "true", "True", "YES", "Y") else 0

    # One-hot groups
    dept_col = _match_department(str(raw.get("DEPARTMENT", "")))
    for col in DELAY_WIDE_COLUMNS:
        if col.startswith("DEPARTMENT_"):
            row[col] = 1 if col == dept_col else 0

    token = _normalize_token(raw.get("TOKEN_NO"))
    token_col = f"TOKEN_NO_{token}" if f"TOKEN_NO_{token}" in DELAY_WIDE_COLUMN_SET else ""
    for col in DELAY_WIDE_COLUMNS:
        if col.startswith("TOKEN_NO_"):
            row[col] = 1 if token_col and col == token_col else 0

    city = str(raw.get("CITY", "")).strip().upper()
    city_col = "CITY_Others"
    if "MECCA" in city or "MAKKAH" in city:
        city_col = "CITY_MECCA"
    elif "RIYADH" in city:
        city_col = "CITY_RIYADH"
    elif "YANBU" in city:
        city_col = "CITY_YANBU"
    for col in DELAY_WIDE_COLUMNS:
        if col.startswith("CITY_"):
            row[col] = 1 if col == city_col else 0

    contract_col = _match_contract(str(raw.get("CONTRACT_NAME", "")))
    for col in DELAY_WIDE_COLUMNS:
        if col.startswith("CONTRACT_NAME_"):
            row[col] = 1 if col == contract_col else 0

    facility_col = _match_facility(str(raw.get("FACILITY_NAME", "") or raw.get("HOSPITAL_NAME", "")))
    for col in DELAY_WIDE_COLUMNS:
        if col.startswith("FACILITY_NAME_"):
            row[col] = 1 if col == facility_col else 0

    gender = str(raw.get("GENDER", "")).strip().upper()
    row["GENDER_Male"] = 1 if gender in ("M", "MALE") else 0
    row["GENDER_Female"] = 1 if gender in ("F", "FEMALE") else 0

    follow = str(raw.get("FOLLOW_NEW", "")).strip().upper()
    row["FOLLOW_NEW_N"] = 1 if follow in ("N", "NEW") else 0

    visit_method = str(raw.get("VISIT_METHOD", "")).strip().upper()
    row["VISIT_METHOD_VIRTUAL"] = 1 if any(x in visit_method for x in ("VIRTUAL", "TELE", "ONLINE")) else 0

    visit_type = str(raw.get("VISIT_TYPE", "")).strip().upper()
    if "CREDIT" in visit_type:
        row["VISIT_TYPE_CREDIT"] = 1
    elif not visit_type:
        row["VISIT_TYPE_NO_INFO"] = 1
    else:
        row["VISIT_TYPE_NO_INFO_1"] = 1

    channel = str(raw.get("APPT_BOOKING_CHANNEL", "")).strip().upper()
    if "PORTAL" in channel or "APP" in channel or "MOBILE" in channel:
        row["APPT_BOOKING_CHANNEL_PORTAL"] = 1
    else:
        row["APPT_BOOKING_CHANNEL_OTHERS"] = 1

    # Explicit overrides from caller
    for col in DELAY_WIDE_COLUMNS:
        if col in raw:
            row[col] = raw[col]

    return row
