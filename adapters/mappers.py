from typing import Dict, Any


def credit_v2_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform gateway inputs to Azure ML format for credit risk model v2
    
    Expected inputs: {age: int, income: int, credit_score: int}
    Azure format: {data: [[age, income, credit_score]]}
    """
    return {
        "data": [[
            inputs["age"],
            inputs["income"],
            inputs["credit_score"]
        ]]
    }


def credit_v2_output(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform Azure ML response to standardized gateway format
    
    Assumes Azure returns: {"prediction": "high_risk", "score": 0.82}
    Or: {"result": [...]}
    """
    # Handle different Azure response formats
    if "prediction" in response and "score" in response:
        return {
            "prediction": response["prediction"],
            "score": response.get("score")
        }
    elif "result" in response:
        # If Azure returns array format
        result = response["result"]
        if isinstance(result, list) and len(result) > 0:
            return {
                "prediction": result[0],
                "score": result[1] if len(result) > 1 else None
            }
    
    # Fallback - return as-is
    return {
        "prediction": response.get("prediction", response),
        "score": response.get("score")
    }


def fraud_v1_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform gateway inputs to Azure ML format for fraud detection model v1
    
    Expected inputs: {transaction_amount: float, merchant_id: str, ...}
    Customize based on actual fraud model requirements
    """
    return {
        "data": [[
            inputs.get("transaction_amount", 0),
            inputs.get("merchant_id", ""),
            inputs.get("user_age", 0),
            inputs.get("transaction_hour", 0)
        ]]
    }


def fraud_v1_output(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform Azure ML fraud detection response to standardized format
    """
    if "is_fraud" in response:
        return {
            "prediction": "fraud" if response["is_fraud"] else "legitimate",
            "score": response.get("fraud_score")
        }
    elif "result" in response:
        result = response["result"]
        if isinstance(result, list) and len(result) > 0:
            return {
                "prediction": "fraud" if result[0] else "legitimate",
                "score": result[1] if len(result) > 1 else None
            }
    
    return {
        "prediction": response.get("prediction", response),
        "score": response.get("score")
    }


def los_fakeeh_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform gateway inputs to Azure ML format for Length of Stay (LOS) model - Fakeeh KSA
    
    Expected inputs: Complete patient record with demographics, vitals, tests, etc.
    Azure format: {Inputs: {data: [[features...]]}} - Note capital I in Inputs
    """
    # Build the input exactly as Azure expects it
    # Using the exact field names from the sample data
    return {
        "Inputs": {
            "data": [{
                "MARITAL_STATUS": inputs.get("MARITAL_STATUS", ""),
                "NATIONALITY": inputs.get("NATIONALITY", ""),
                "Column1": inputs.get("Column1", 0),
                "BMI": inputs.get("BMI", 0.0),
                "MRNO": inputs.get("MRNO", 0),
                "AGE": inputs.get("AGE", 0),
                "AGE_GROUP": inputs.get("AGE_GROUP", ""),
                "AGE_GROUP_encoded": inputs.get("AGE_GROUP_encoded", 0),
                "ADMISSION_TYPE": inputs.get("ADMISSION_TYPE", ""),
                "ADMISSION_TYPE_encoded": inputs.get("ADMISSION_TYPE_encoded", 0),
                "ADMISSION_LEVEL": inputs.get("ADMISSION_LEVEL", ""),
                "ADMISSION_LEVEL_encoded": inputs.get("ADMISSION_LEVEL_encoded", 0),
                "ROOM_TYPE": inputs.get("ROOM_TYPE", ""),
                "ROOM_TYPE_encoded": inputs.get("ROOM_TYPE_encoded", 0),
                "SOURCE_OF_ADMN": inputs.get("SOURCE_OF_ADMN", ""),
                "SOURCE_OF_ADMN_encoded": inputs.get("SOURCE_OF_ADMN_encoded", 0),
                "PRIMARY": inputs.get("PRIMARY", ""),
                "PRIMARY_encoded": inputs.get("PRIMARY_encoded", 0),
                "SECONDARY": inputs.get("SECONDARY", ""),
                "SURGERY_NAME": inputs.get("SURGERY_NAME", ""),
                "PAYER": inputs.get("PAYER", ""),
                "PREVIOUS_IP": inputs.get("PREVIOUS_IP", 0),
                "SODIUM": inputs.get("SODIUM", 0),
                "SODIUM_available": inputs.get("SODIUM_available", 0),
                "GLUCOSE": inputs.get("GLUCOSE", ""),
                "BLOOD_UREA_NITROGEN": inputs.get("BLOOD_UREA_NITROGEN", 0),
                "BLOOD_UREA_NITROGEN_available": inputs.get("BLOOD_UREA_NITROGEN_available", 0),
                "C_REACTIVE_PROTEIN": inputs.get("C_REACTIVE_PROTEIN", 0),
                "C_REACTIVE_PROTEIN_available": inputs.get("C_REACTIVE_PROTEIN_available", 0),
                "CREATININE": inputs.get("CREATININE", 0),
                "CREATININE_available": inputs.get("CREATININE_available", 0),
                "WBC": inputs.get("WBC", ""),
                "PLATELETS_COUNT": inputs.get("PLATELETS_COUNT", 0),
                "PLATELETS_COUNT_available": inputs.get("PLATELETS_COUNT_available", 0),
                "HEMATOGY_TESTS": inputs.get("HEMATOGY_TESTS", ""),
                "CHEMISTRY_TESTS": inputs.get("CHEMISTRY_TESTS", ""),
                "IMMUNOLOGY_TESTS": inputs.get("IMMUNOLOGY_TESTS", ""),
                "CULTURE_TESTS": inputs.get("CULTURE_TESTS", ""),
                "OXYGEN_SATURATION": inputs.get("OXYGEN_SATURATION", 0),
                "TEMPERATURE": inputs.get("TEMPERATURE", 0.0),
                "BPSYSTOLIC": inputs.get("BPSYSTOLIC", 0),
                "BPDIASTOLIC": inputs.get("BPDIASTOLIC", 0),
                "PULSE": inputs.get("PULSE", 0),
                "RESPIRATION": inputs.get("RESPIRATION", 0),
                "RADIOLOGY_TESTS": inputs.get("RADIOLOGY_TESTS", ""),
                "TOTAL_MEDICINE_ORDERED": inputs.get("TOTAL_MEDICINE_ORDERED", 0),
                "MEDICATION_TYPE": inputs.get("MEDICATION_TYPE", ""),
                "CLINICAL_WARNING": inputs.get("CLINICAL_WARNING", ""),
                "EXPIRED": inputs.get("EXPIRED", False),
                "EXPIRED_encoded": inputs.get("EXPIRED_encoded", 0),
                "LOS_GROUP": inputs.get("LOS_GROUP", ""),
                "LOS_GROUP_encoded": inputs.get("LOS_GROUP_encoded", 0),
                "IP_IN_PREVIOUS_30_DAYS": inputs.get("IP_IN_PREVIOUS_30_DAYS", False),
                "IP_IN_PREVIOUS_30_DAYS_encoded": inputs.get("IP_IN_PREVIOUS_30_DAYS_encoded", 0),
                "HOSPITALIZATION_PREVIOUS_YEAR": inputs.get("HOSPITALIZATION_PREVIOUS_YEAR", 0)
            }]
        }
    }


def los_fakeeh_output(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform Azure ML LOS response to standardized gateway format
    
    Assumes Azure returns predicted length of stay category and confidence
    Example: {"prediction": "LONG", "score": 0.85} or {"result": ["LONG", 0.85]}
    """
    # Handle different Azure response formats
    if "prediction" in response:
        return {
            "prediction": response["prediction"],
            "score": response.get("score"),
            "los_category": response.get("prediction"),
            "confidence": response.get("score")
        }
    elif "result" in response:
        result = response["result"]
        if isinstance(result, list) and len(result) > 0:
            return {
                "prediction": result[0],
                "score": result[1] if len(result) > 1 else None,
                "los_category": result[0],
                "confidence": result[1] if len(result) > 1 else None
            }
    elif "Results" in response:
        # Handle Azure ML Studio format
        results = response["Results"]
        if isinstance(results, dict):
            # Extract the first result
            first_key = list(results.keys())[0] if results else None
            if first_key and isinstance(results[first_key], dict):
                values = results[first_key].get("value", {}).get("Values", [[]])[0]
                if len(values) > 0:
                    return {
                        "prediction": values[-1] if values else "UNKNOWN",
                        "score": None,
                        "los_category": values[-1] if values else "UNKNOWN"
                    }
    
    # Fallback - return as-is with best guess
    return {
        "prediction": response.get("prediction", str(response)),
        "score": response.get("score"),
        "los_category": response.get("prediction", "UNKNOWN")
    }


def no_show_fakeeh_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform gateway inputs to AWS SageMaker format for No-Show prediction model - Fakeeh KSA
    
    Expected inputs: Patient appointment details with 21 features in specific order
    SageMaker Canvas format: features array in exact order
    
    Feature order (21 fields):
    1. PROVIDER_NAME, 2. DEPARTMENT, 3. ALLOCATION_DATE_TIME, 4. ALLOCATION_DAY,
    5. MRNO, 6. TOKEN_NO, 7. GIVEN_BY, 8. FOLLOW_NEW, 9. AGE, 10. REMARKS,
    11. APPT_ALLOCATION_ID, 12. FACILITY_NAME, 13. GENDER, 14. VISIT_METHOD,
    15. GIVEN_ON, 16. DOCTORS_NATIONALITY, 17. APPT_BOOKING_CHANNEL, 18. CITY,
    19. VISIT_TYPE, 20. CONTRACT_NAME, 21. PAYMENT_STATUS
    
    Note: All datetime fields are sent as-is (strings). AutoGluon will handle type conversion.
    """
    from datetime import datetime

    def to_unix_timestamp(val):
        if not val:
            return 0
        if isinstance(val, (int, float)):
            return int(val)
        try:
            # Accept both 'YYYY-MM-DD HH:MM:SS' and ISO formats
            return int(datetime.strptime(str(val).strip(), "%Y-%m-%d %H:%M:%S").timestamp())
        except Exception:
            try:
                return int(datetime.fromisoformat(str(val).strip()).timestamp())
            except Exception:
                return 0

    def to_int(val):
        try:
            return int(val)
        except Exception:
            return 0

    features = [
        str(inputs.get("PROVIDER_NAME", "")),
        str(inputs.get("DEPARTMENT", "")),
        to_unix_timestamp(inputs.get("ALLOCATION_DATE_TIME", "")),
        str(inputs.get("ALLOCATION_DAY", "")),
        to_int(inputs.get("MRNO", "")),
        str(inputs.get("TOKEN_NO", "")),
        str(inputs.get("GIVEN_BY", "")),
        str(inputs.get("FOLLOW_NEW", "")),
        str(inputs.get("AGE", "")),
        str(inputs.get("REMARKS", "")),
        to_int(inputs.get("APPT_ALLOCATION_ID", "")),
        str(inputs.get("FACILITY_NAME", "")),
        str(inputs.get("GENDER", "")),
        str(inputs.get("VISIT_METHOD", "")),
        to_unix_timestamp(inputs.get("GIVEN_ON", "")),
        str(inputs.get("DOCTORS_NATIONALITY", "")),
        str(inputs.get("APPT_BOOKING_CHANNEL", "")),
        str(inputs.get("CITY", "")),
        str(inputs.get("VISIT_TYPE", "")),
        str(inputs.get("CONTRACT_NAME", "")),
        str(inputs.get("PAYMENT_STATUS", ""))
    ]

    return {
        "data": {
            "features": {
                "values": [features]
            }
        }
    }


def no_show_fakeeh_output(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform AWS SageMaker No-Show response to standardized gateway format
    
    Assumes SageMaker returns prediction probability and classification
    Example: {"predictions": [{"score": 0.85, "predicted_label": "NO_SHOW"}]}
    """
    # Handle different SageMaker response formats
    if "predictions" in response:
        predictions = response["predictions"]
        if isinstance(predictions, list) and len(predictions) > 0:
            pred = predictions[0]
            if isinstance(pred, dict):
                return {
                    "prediction": pred.get("predicted_label", pred.get("prediction", "UNKNOWN")),
                    "score": pred.get("score", pred.get("probability")),
                    "no_show_probability": pred.get("score", pred.get("probability"))
                }
            else:
                # Simple prediction value
                return {
                    "prediction": str(pred),
                    "score": None,
                    "no_show_probability": None
                }
    
    # Handle single prediction format
    if "prediction" in response:
        return {
            "prediction": response["prediction"],
            "score": response.get("score", response.get("probability")),
            "no_show_probability": response.get("score", response.get("probability"))
        }
    
    # Fallback - return as-is
    return {
        "prediction": str(response),
        "score": None,
        "no_show_probability": None
    }


def delay_local_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw / integration appointment JSON to delay AutoML pipeline columns."""
    from adapters.delay_features import engineer_delay_features

    return engineer_delay_features(inputs)


def delay_fakeeh_dubai_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform gateway inputs to Azure ML format for Delay Prediction model - Fakeeh Dubai

    Expected inputs: Appointment details for delay prediction
    Azure format: {input_data: pandas DataFrame structure}
    """
    # Debug: print what we received
    print(f"DEBUG: inputs type: {type(inputs)}")
    print(f"DEBUG: inputs: {inputs}")
    
    return {
        "input_data": {
            "columns": [
                "HOSPITAL_ID_details", "PROVIDER_NAME_details", "DEPARTMENT_details",
                "MRNO_details", "TOKEN_NO_details", "APPT_ALLOCATION_ID",
                "FACILITY_NAME_details", "PROVIDER_NAME_delay", "DEPARTMENT_delay",
                "MRNO_delay", "TOKEN_NO_delay", "HOSPITAL_ID_delay",
                "FACILITY_NAME_delay", "ALLOCATION_DATETIME", "ALLOCATION_HOUR",
                "ALLOCATION_DAY_OF_WEEK", "ALLOCATION_MONTH", "IS_WEEKEND",
                "AGE", "GENDER_ENCODED", "STATUS_ENCODED",
                "VISIT_METHOD_ENCODED", "PAYMENT_STATUS_ENCODED"
            ],
            "index": [0],
            "data": [[
                1.0, "Mohamed Lotfy Ahmed", "GENERAL PEDIATRICS",
                "10155995", "7W", "1237535",
                "Fakeeh University Hospital", "Mohamed Lotfy Ahmed", "GENERAL PEDIATRICS",
                "10155995", "7W", 1.0,
                "Fakeeh University Hospital", "2025-02-13T00:00:00Z", 0,
                3, 2, 0,
                2.0, 0.0, -1.0,
                0.0, -1.0
            ]]
        }
    }


def delay_fakeeh_dubai_output(response: Any) -> Dict[str, Any]:
    """
    Transform Azure ML delay prediction response to standardized gateway format

    Assumes Azure returns delay prediction and confidence score
    Example: {"prediction": "ON_TIME", "score": 0.75} or {"result": ["DELAYED", 0.85]}
    """
    prediction_val = None
    
    # If response is a list, handle it
    if isinstance(response, list):
        if len(response) > 0:
            val = response[0]
            if isinstance(val, (list, dict)):
                # Nested list or dict from Azure
                if isinstance(val, list) and len(val) > 0:
                    prediction_val = val[0]
                elif isinstance(val, dict):
                    prediction_val = val.get("prediction", val.get("result", str(val)))
            else:
                prediction_val = val
    
    # Handle dictionary response
    elif isinstance(response, dict):
        prediction_val = response.get("prediction", response.get("result", str(response)))
    
    else:
        # Final fallback for any other type
        prediction_val = str(response)

    # Format prediction as integer + " minutes" if it's a number
    try:
        if isinstance(prediction_val, (int, float, str)):
            # Try to convert to float first
            num_val = float(prediction_val)
            # Round down/strip decimal part
            int_val = int(num_val)
            prediction_val = f"{int_val} minutes"
    except (ValueError, TypeError):
        pass

    return {
        "prediction": prediction_val,
        "score": None,
        "latency_ms": None
    }


# Column order must match models/local-models/cost-estimation-ksa/model.joblib training
_COST_ESTIMATION_COLUMNS = (
    "WEIGHT_IN_KG",
    "HEIGHT_IN_CM",
    "ICD_CODE",
    "HEARTRATE",
    "RESPIRATORYRATE",
    "TEMPERATURE",
    "TYPE_OF_PROCEDURE_CLINICALPROCEDURE",
    "SUBCATEGORY_CLINICALPROCEDURE",
    "NUMBER_OF_PROCEDURES",
    "LENGTH_OF_STAY_DAYS",
    "ROOM_TYPE",
    "DISCHARGEDISPOSITION",
    "BLOOD_PRESSURE_UPPER",
    "BLOOD_PRESSURE_LOWER",
    "SURGERY_NAME",
    "ISCREDIT",
    "LOS_days",
    "AGE_GROUP",
    "NUM_PRIMARY_DIAG",
    "NUM_SECONDARY_DIAG",
    "ICU_FLAG",
    "IS_SURGERY",
    "IS_FEMALE",
    "BMI_CAT",
    "IS_SELF_PAY",
    "HAS_CARDIAC_PROC",
)


def _coerce_cost_feature(val: Any) -> float:
    """Coerce a cost-model feature to float; missing/invalid values become 0."""
    if val is None:
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


def cost_estimation_ksa_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build one row for the on-disk cost estimation RandomForest (26 features).

    Accepts any subset of the 26 fields; anything not sent defaults to 0.
    Non-numeric strings (e.g. ICD codes, room types) are treated as 0 because
    the trained model expects numeric columns only.
    """
    row: Dict[str, Any] = {}
    for col in _COST_ESTIMATION_COLUMNS:
        row[col] = _coerce_cost_feature(inputs.get(col))
    return {"_local_records": [row]}


def cost_estimation_ksa_output(response: Dict[str, Any]) -> Dict[str, Any]:
    pred = response.get("prediction")
    try:
        pred = float(pred)
    except (TypeError, ValueError):
        pass
    return {"prediction": pred, "score": response.get("score")}


def no_show_bundle_local_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw / SageMaker-style inputs; engineering happens in local_inference."""
    from adapters.noshow_features import normalize_noshow_inputs

    return normalize_noshow_inputs(inputs)


def no_show_bundle_local_output(response: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw classifier output to gateway fields (binary 0/1)."""
    pred = response.get("prediction")
    score = response.get("score")
    if pred == 1:
        label = "NO_SHOW"
    elif pred == 0:
        label = "SHOW"
    else:
        label = str(pred)
    return {"prediction": label, "score": score, "no_show_probability": score}


# ---------------------------------------------------------------------------
# Azure AutoML local pipeline mappers (los_local / delay_local)
# ---------------------------------------------------------------------------
# These models take raw inputs as a pd.DataFrame row directly – no pre-mapping
# needed before the pipeline's own DataTransformer.  Inputs are passed through
# unchanged; the output is a numeric regression value.


def azure_automl_noop_input(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Pass-through: the pipeline's DataTransformer handles all preprocessing."""
    return inputs


def los_local_output(response: Dict[str, Any]) -> Dict[str, Any]:
    """Convert raw predicted LOS (continuous days) to gateway response."""
    pred = response.get("prediction")
    try:
        days = float(pred)
        if days <= 1:
            category = "SHORT"
        elif days <= 3:
            category = "MEDIUM"
        else:
            category = "LONG"
        label = f"{round(days, 2)} days ({category})"
    except (TypeError, ValueError):
        label = str(pred)
    return {"prediction": label, "score": response.get("score"), "los_days": pred}


def delay_local_output(response: Dict[str, Any]) -> Dict[str, Any]:
    """Convert raw predicted delay (continuous minutes) to gateway response."""
    pred = response.get("prediction")
    try:
        minutes = float(pred)
        label = f"{int(minutes)} minutes"
    except (TypeError, ValueError):
        label = str(pred)
    return {"prediction": label, "score": response.get("score"), "delay_minutes": pred}


# Registry of all mapper functions
INPUT_MAPPERS = {
    "credit_v2": credit_v2_input,
    "fraud_v1": fraud_v1_input,
    "los_fakeeh": los_fakeeh_input,
    "no_show_fakeeh": no_show_fakeeh_input,
    "delay_fakeeh_dubai": delay_fakeeh_dubai_input,
    "cost_estimation_ksa": cost_estimation_ksa_input,
    "no_show_bundle_local": no_show_bundle_local_input,
    "azure_automl_noop": azure_automl_noop_input,
    "delay_local": delay_local_input,
}

OUTPUT_MAPPERS = {
    "credit_v2": credit_v2_output,
    "fraud_v1": fraud_v1_output,
    "los_fakeeh": los_fakeeh_output,
    "no_show_fakeeh": no_show_fakeeh_output,
    "delay_fakeeh_dubai": delay_fakeeh_dubai_output,
    "cost_estimation_ksa": cost_estimation_ksa_output,
    "no_show_bundle_local": no_show_bundle_local_output,
    "los_local": los_local_output,
    "delay_local": delay_local_output,
}


def get_input_mapper(mapper_name: str):
    """Get input mapper function by name"""
    mapper = INPUT_MAPPERS.get(mapper_name)
    if not mapper:
        raise ValueError(f"Input mapper '{mapper_name}' not found")
    return mapper


def get_output_mapper(mapper_name: str):
    """Get output mapper function by name"""
    mapper = OUTPUT_MAPPERS.get(mapper_name)
    if not mapper:
        raise ValueError(f"Output mapper '{mapper_name}' not found")
    return mapper
