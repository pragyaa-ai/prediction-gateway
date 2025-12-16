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
    Azure format: {data: [[features...]]} or direct feature dict
    """
    # Build the input exactly as Azure expects it
    # Using the exact field names from the sample data
    return {
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


# Registry of all mapper functions
INPUT_MAPPERS = {
    "credit_v2": credit_v2_input,
    "fraud_v1": fraud_v1_input,
    "los_fakeeh": los_fakeeh_input,
}

OUTPUT_MAPPERS = {
    "credit_v2": credit_v2_output,
    "fraud_v1": fraud_v1_output,
    "los_fakeeh": los_fakeeh_output,
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
