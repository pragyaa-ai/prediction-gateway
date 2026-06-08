"""
Column schema for the local LOS (Length-of-Stay) Azure AutoML pipeline.

LOS_MODEL_COLUMNS  – ordered tuple matching the model's training schema
                     (same order as DEFAULT_INPUT_SCHEMA in fakeeh_los_proxy.py)
LOS_STRING_COLUMNS – fields that must remain strings (empty-string default on
                     missing/None); all other columns are coerced to numeric.
LOS_BOOL_TO_INT    – fields that arrive as Python booleans and must be
                     converted to 0/1 integers before building the DataFrame.
"""
from __future__ import annotations

LOS_MODEL_COLUMNS: tuple[str, ...] = (
    "Column1",
    "MRNO",
    "AGE",
    "MARITAL_STATUS",
    "NATIONALITY",
    "BMI",
    "ADMISSION_TYPE",
    "ADMISSION_LEVEL",
    "ROOM_TYPE",
    "SOURCE_OF_ADMN",
    "PRIMARY",
    "SECONDARY",
    "SURGERY_NAME",
    "PAYER",
    "PREVIOUS_IP",
    "SODIUM",
    "GLUCOSE",
    "BLOOD_UREA_NITROGEN",
    "C_REACTIVE_PROTEIN",
    "CREATININE",
    "WBC",
    "PLATELETS_COUNT",
    "HEMATOGY_TESTS",
    "CHEMISTRY_TESTS",
    "IMMUNOLOGY_TESTS",
    "CULTURE_TESTS",
    "OXYGEN_SATURATION",
    "TEMPERATURE",
    "BPSYSTOLIC",
    "BPDIASTOLIC",
    "PULSE",
    "RESPIRATION",
    "RADIOLOGY_TESTS",
    "TOTAL_MEDICINE_ORDERED",
    "MEDICATION_TYPE",
    "CLINICAL_WARNING",
    "EXPIRED",
    "LOS_GROUP",
    "IP_IN_PREVIOUS_30_DAYS",
    "HOSPITALIZATION_PREVIOUS_YEAR",
    "ADMISSION_TYPE_encoded",
    "ADMISSION_LEVEL_encoded",
    "ROOM_TYPE_encoded",
    "SOURCE_OF_ADMN_encoded",
    "PRIMARY_encoded",
    "EXPIRED_encoded",
    "LOS_GROUP_encoded",
    "IP_IN_PREVIOUS_30_DAYS_encoded",
    "AGE_GROUP",
    "AGE_GROUP_encoded",
    "SODIUM_available",
    "BLOOD_UREA_NITROGEN_available",
    "C_REACTIVE_PROTEIN_available",
    "CREATININE_available",
    "PLATELETS_COUNT_available",
)

LOS_STRING_COLUMNS: frozenset[str] = frozenset({
    "MARITAL_STATUS",
    "NATIONALITY",
    "ADMISSION_TYPE",
    "ADMISSION_LEVEL",
    "ROOM_TYPE",
    "SOURCE_OF_ADMN",
    "PRIMARY",
    "SECONDARY",
    "SURGERY_NAME",
    "PAYER",
    "GLUCOSE",
    "WBC",
    "HEMATOGY_TESTS",
    "CHEMISTRY_TESTS",
    "IMMUNOLOGY_TESTS",
    "CULTURE_TESTS",
    "RADIOLOGY_TESTS",
    "MEDICATION_TYPE",
    "CLINICAL_WARNING",
    "LOS_GROUP",
    "AGE_GROUP",
})

# These fields arrive as Python booleans from the proxy; the AutoML pipeline
# expects integer 0/1 values, not Python True/False.
LOS_BOOL_TO_INT: frozenset[str] = frozenset({"EXPIRED", "IP_IN_PREVIOUS_30_DAYS"})
