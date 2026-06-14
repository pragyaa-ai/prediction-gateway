#!/usr/bin/env python3
"""
Fakeeh Length-of-Stay Flask proxy.

Core logic matches length_of_stay_api.py exactly (encode → cloud → OpenSearch).
Additions: SSL (same certs as delay proxy), async local ml-gateway call.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

os.environ.setdefault("PYTHONUNBUFFERED", "1")

import pandas as pd
import requests
from flask import Flask, jsonify, request
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from adapters.sagemaker_format import parse_regression_prediction  # noqa: E402
from los_encoder import LOSDataEncoder  # noqa: E402 — must live in scripts/
from proxy_env import env_bool, env_get  # noqa: E402

app = Flask(__name__)

# API Gateway / Lambda endpoint
API_GATEWAY_URL = env_get("LOS_CLOUD_URL", "API_GATEWAY_URL", default="https://apis.pragyaa.ai/stay/predict")

# OpenSearch Configuration (default 10.1.186.40 — override via OPENSEARCH_URL)
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "https://10.1.186.40:9200/")
INDEX_NAME = os.getenv("LOS_OPENSEARCH_INDEX", "length-of-stay-index")
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
USERNAME = os.getenv("OPENSEARCH_USER", "admin")
PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "admin")

# Local ml-gateway (async, does not affect client response)
LOCAL_GATEWAY_URL = env_get(
    "LOS_LOCAL_GATEWAY_URL", "LOCAL_GATEWAY_URL",
    default="http://127.0.0.1:8000/v1/predict/los_fakeeh_ksa_local",
)
USE_LOCAL_AS_PRIMARY = env_bool("LOS_USE_LOCAL_PRIMARY", "USE_LOCAL_PRIMARY", default="false")
CLOUD_ENABLED = env_bool("LOS_CLOUD_ENABLED", "CLOUD_ENABLED", default="true")
LOCAL_GATEWAY_ENABLED = env_bool("LOS_LOCAL_GATEWAY_ENABLED", "LOCAL_GATEWAY_ENABLED", default="true")

# Setup retry strategy for OpenSearch requests
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE"],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)

# Path to derived mapping JSON (always relative to this script's directory)
DERIVED_MAPPING_PATH = os.getenv(
    "LOS_DERIVED_MAPPING_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "derived_mapping.json"),
)

# Initialize encoder
encoder = LOSDataEncoder(DERIVED_MAPPING_PATH)

# Logging setup (console + file) — same as original
_log_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(_log_dir, "length_of_stay_api.log"), mode="a"),
    ],
    force=True,
)

# EXACT model schema required (keeps order)
DEFAULT_INPUT_SCHEMA = {
    "Column1": 0,
    "MRNO": 0,
    "AGE": 0,
    "MARITAL_STATUS": "",
    "NATIONALITY": "",
    "BMI": 0.0,
    "ADMISSION_TYPE": "",
    "ADMISSION_LEVEL": "",
    "ROOM_TYPE": "",
    "SOURCE_OF_ADMN": "",
    "PRIMARY": "",
    "SECONDARY": "",
    "SURGERY_NAME": "",
    "PAYER": "",
    "PREVIOUS_IP": 0,
    "SODIUM": 0.0,
    "GLUCOSE": "",
    "BLOOD_UREA_NITROGEN": 0.0,
    "C_REACTIVE_PROTEIN": 0.0,
    "CREATININE": 0.0,
    "WBC": "",
    "PLATELETS_COUNT": 0.0,
    "HEMATOGY_TESTS": "",
    "CHEMISTRY_TESTS": "",
    "IMMUNOLOGY_TESTS": "",
    "CULTURE_TESTS": "",
    "OXYGEN_SATURATION": 0.0,
    "TEMPERATURE": 0.0,
    "BPSYSTOLIC": 0.0,
    "BPDIASTOLIC": 0.0,
    "PULSE": 0.0,
    "RESPIRATION": 0.0,
    "RADIOLOGY_TESTS": "",
    "TOTAL_MEDICINE_ORDERED": 0,
    "MEDICATION_TYPE": "",
    "CLINICAL_WARNING": "",
    "EXPIRED": False,
    "LOS_GROUP": "",
    "IP_IN_PREVIOUS_30_DAYS": False,
    "HOSPITALIZATION_PREVIOUS_YEAR": 0,
    "ADMISSION_TYPE_encoded": 0,
    "ADMISSION_LEVEL_encoded": 0,
    "ROOM_TYPE_encoded": 0,
    "SOURCE_OF_ADMN_encoded": 0,
    "PRIMARY_encoded": 0,
    "EXPIRED_encoded": 0,
    "LOS_GROUP_encoded": 0,
    "IP_IN_PREVIOUS_30_DAYS_encoded": 0,
    "AGE_GROUP": "",
    "AGE_GROUP_encoded": 0,
    "SODIUM_available": 0,
    "BLOOD_UREA_NITROGEN_available": 0,
    "C_REACTIVE_PROTEIN_available": 0,
    "CREATININE_available": 0,
    "PLATELETS_COUNT_available": 0,
}


def derive_age_group(age):
    """Derive AGE_GROUP label from numeric AGE (fallback if AGE_GROUP missing)."""
    try:
        a = int(age)
    except Exception:
        return ""
    if a <= 12:
        return "Child"
    if a <= 35:
        return "Young_Adult"
    if a <= 45:
        return "Adult"
    if a <= 64:
        return "Middle_Aged"
    return "Senior"


def parse_bool_like(val):
    """Convert various representations to a boolean."""
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    s = str(val).strip().lower()
    if s in ("yes", "y", "true", "1", "t"):
        return True
    if s in ("no", "n", "false", "0", "f", "na", ""):
        return False
    return True


def available_flag(val):
    """
    Robust presence check:
    - If numeric and non-zero -> present
    - If string: try to parse first number; if none, non-empty -> present
    - Empty / null / '0' / 'na' -> not present
    """
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return 1 if val != 0 else 0
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "null", "na"):
        return 0
    m = re.search(r"-?\d+\.?\d*", s)
    if m:
        try:
            num = float(m.group())
            return 1 if num != 0 else 0
        except Exception:
            return 1
    return 1


def coerce_to_type(value, default):
    """Attempt to coerce a value to the default type; fallback to default."""
    if isinstance(default, bool):
        return bool(parse_bool_like(value))
    if isinstance(default, int):
        try:
            return int(value)
        except Exception:
            return default
    if isinstance(default, float):
        try:
            return float(value)
        except Exception:
            return default
    if isinstance(default, str):
        return str(value).strip() if value is not None else default
    return value


FIELDS_STRIP_UNITS = {
    "SODIUM",
    "BLOOD_UREA_NITROGEN",
    "C_REACTIVE_PROTEIN",
    "CREATININE",
    "PLATELETS_COUNT",
}


def normalize_raw_payload(incoming: dict):
    """
    Normalize + type-cast the incoming raw payload to raw fields expected by model.
    Returns two dicts:
      - cleaned_raw: types as per schema (EXPIRED and IP_IN_PREVIOUS_30_DAYS as bool)
      - cleaned_for_encoding: same as cleaned_raw but with EXPIRED and IP_IN_PREVIOUS_30_DAYS as 'Yes'/'No' strings
    """

    def strip_units(value):
        if isinstance(value, str):
            match = re.search(r"[-+]?\d*\.?\d+", value)
            if match:
                try:
                    return float(match.group())
                except ValueError:
                    return value
        return value

    def clean_primary(value):
        if isinstance(value, str):
            return re.sub(r"[,\s]*unspecified\s*$", "", value, flags=re.IGNORECASE)
        return value

    incoming_lc = {str(k).lower(): k for k in incoming.keys()}
    cleaned_raw = {}
    for k, default in DEFAULT_INPUT_SCHEMA.items():
        if k.endswith("_encoded") or k.endswith("_available"):
            continue
        incoming_key = incoming_lc.get(k.lower(), k)
        val = incoming.get(incoming_key, default)
        if k in FIELDS_STRIP_UNITS:
            val = strip_units(val)
        if k == "PRIMARY":
            val = clean_primary(val)
        coerced = coerce_to_type(val, default)
        if k == "AGE" and isinstance(coerced, float):
            coerced = int(coerced)
        cleaned_raw[k] = coerced

    if not cleaned_raw.get("AGE_GROUP"):
        cleaned_raw["AGE_GROUP"] = derive_age_group(cleaned_raw.get("AGE", 0))

    cleaned_raw["EXPIRED"] = parse_bool_like(cleaned_raw.get("EXPIRED"))
    cleaned_raw["IP_IN_PREVIOUS_30_DAYS"] = parse_bool_like(cleaned_raw.get("IP_IN_PREVIOUS_30_DAYS"))

    cleaned_for_encoding = dict(cleaned_raw)
    cleaned_for_encoding["EXPIRED"] = "Yes" if cleaned_raw["EXPIRED"] else "No"
    cleaned_for_encoding["IP_IN_PREVIOUS_30_DAYS"] = "Yes" if cleaned_raw["IP_IN_PREVIOUS_30_DAYS"] else "No"

    return cleaned_raw, cleaned_for_encoding


def predict_los_group(
    age_group_encoded,
    ip_in_previous_30_days_encoded,
    hospitalization_previous_year,
    admission_type_encoded,
    admission_level_encoded,
    room_type_encoded,
):
    score = 0
    if age_group_encoded in [1, 4]:
        score += 0
    elif age_group_encoded == 0:
        score += 1
    elif age_group_encoded == 2:
        score += 1
    elif age_group_encoded == 3:
        score += 2

    if ip_in_previous_30_days_encoded == 1:
        score += 2
    if hospitalization_previous_year > 1:
        score += 1

    long_stay_levels = [1, 3, 4, 11, 12, 16, 17, 20]
    medium_stay_levels = [2, 5, 6, 7, 8, 10, 13, 18, 21]
    if admission_level_encoded in long_stay_levels:
        score += 2
    elif admission_level_encoded in medium_stay_levels:
        score += 1

    if room_type_encoded == 1:
        score += 2
    elif room_type_encoded in [2, 3]:
        score += 1

    if score <= 3:
        return "SHORT"
    if 4 <= score <= 6:
        return "MEDIUM"
    return "LONG"


def get_age_group(age):
    if age is None:
        return None
    try:
        age = int(age)
    except Exception:
        return None
    if age <= 12:
        return "Child"
    if 13 <= age <= 39:
        return "Young_Adult"
    if 40 <= age <= 49:
        return "Adult"
    if 50 <= age <= 64:
        return "Middle_Aged"
    return "Senior"


INPUT_TO_OS_FIELD_MAP = {
    "mrno": "MRNO",
    "age": "AGE",
    "maritaL_STATUS": "MARITAL_STATUS",
    "nationality": "NATIONALITY",
    "bmi": "BMI",
    "admissioN_TYPE": "ADMISSION_TYPE",
    "admissioN_LEVEL": "ADMISSION_LEVEL",
    "rooM_TYPE": "ROOM_TYPE",
    "sourcE_OF_ADMN": "SOURCE_OF_ADMN",
    "primary": "PRIMARY",
    "secondary": "SECONDARY",
    "surgerY_NAME": "SURGERY_NAME",
    "payer": "PAYER",
    "previouS_IP": "PREVIOUS_IP",
    "sodium": "SODIUM",
    "glucose": "GLUCOSE",
    "blooD_UREA_NITROGEN": "BLOOD_UREA_NITROGEN",
    "c_REACTIVE_PROTEIN": "C_REACTIVE_PROTEIN",
    "creatinine": "CREATININE",
    "wbc": "WBC",
    "plateletS_COUNT": "PLATELETS_COUNT",
    "hematogY_TESTS": "HEMATOLOGY_TESTS",
    "chemistrY_TESTS": "CHEMISTRY_TESTS",
    "immunologY_TESTS": "IMMUNOLOGY_TESTS",
    "culturE_TESTS": "CULTURE_TESTS",
    "oxygeN_SATURATION": "OXYGEN_SATURATION",
    "temperature": "TEMPERATURE",
    "bpsystolic": "BPSYSTOLIC",
    "bpdiaSTOLIC": "BPDIASTOLIC",
    "pulse": "PULSE",
    "respiration": "RESPIRATION",
    "radiologY_TESTS": "RADIOLOGY_TESTS",
    "totaL_MEDICINE_ORDERED": "TOTAL_MEDICINE_ORDERED",
    "medicatioN_TYPE": "MEDICATION_TYPE",
    "clinicaL_WARNING": "CLINICAL_WARNING",
    "expired": "EXPIRED",
    "loS_GROUP": "LOS_GROUP",
    "iP_IN_PREVIOUS_30_DAYS": "IP_IN_PREVIOUS_30_DAYS",
    "hospitalizatioN_PREVIOUS_YEAR": "HOSPITALIZATION_PREVIOUS_YEAR",
}


def save_to_opensearch(input_data: dict, prediction: float):
    """Save raw API input data + LOS prediction to OpenSearch."""
    try:
        os_data = {
            os_field: input_data.get(api_key, None)
            for api_key, os_field in INPUT_TO_OS_FIELD_MAP.items()
        }
        os_data["LOS_Prediction"] = float(prediction)
        os_data["timestamp"] = datetime.utcnow().isoformat()

        url = f"{OPENSEARCH_URL}{INDEX_NAME}/_doc/"
        response = session.post(
            url,
            json=os_data,
            headers=HEADERS,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            verify=False,
        )
        if response.status_code not in (200, 201):
            raise Exception(f"Failed to index data: {response.status_code} {response.text}")
        logging.info("Data successfully indexed in OpenSearch.")
    except Exception as e:
        logging.error("Error saving data to OpenSearch: %s", e)


def _local_los_days(gateway_body: dict) -> Optional[float]:
    raw = gateway_body.get("prediction")
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        parsed = parse_regression_prediction(raw)
        if parsed and parsed.get("predicted_value") is not None:
            return float(parsed["predicted_value"])
        try:
            return float(raw.split(",")[0])
        except (TypeError, ValueError, IndexError):
            return None
    return None


def invoke_local_gateway(final_payload: dict) -> float:
    response = requests.post(
        LOCAL_GATEWAY_URL,
        json={"client_id": "fakeeh-flask-los-proxy", "inputs": final_payload},
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    if response.status_code != 200:
        body = response.json() if response.content else {}
        raise RuntimeError(
            f"Local LOS gateway HTTP {response.status_code}: "
            f"{body.get('detail', response.text)}"
        )
    days = _local_los_days(response.json() if response.content else {})
    if days is None:
        raise RuntimeError("Local LOS gateway returned no parseable prediction")
    logging.info("Local LOS gateway prediction: %.4f days", days)
    return days


def invoke_local_gateway_async(final_payload: dict) -> None:
    def _run() -> None:
        try:
            invoke_local_gateway(final_payload)
        except Exception as e:
            logging.error("Local LOS gateway error: %s", e)

    threading.Thread(target=_run, name="local-los-dup", daemon=True).start()


def invoke_cloud_gateway(final_payload: dict) -> Optional[float]:
    headers = {"Content-Type": "application/json"}
    resp = requests.post(API_GATEWAY_URL, json=final_payload, headers=headers, timeout=15)
    logging.info("Lambda response: %s %s", resp.status_code, resp.text)
    if resp.status_code != 200:
        raise RuntimeError(f"Cloud LOS HTTP {resp.status_code}: {resp.text}")
    outer = resp.json()
    if "body" in outer:
        inner = json.loads(outer["body"]) if isinstance(outer["body"], str) else outer["body"]
        return (
            inner.get("Predicted_length_of_stay")
            or inner.get("predicted_los")
            or inner.get("predicted_length_of_stay")
        )
    return outer.get("Predicted_length_of_stay")


def format_los_client_response(predicted_los) -> tuple:
    """Same JSON shape whether prediction came from cloud or local."""
    return jsonify({"Length of Stay": round(float(predicted_los), 2)}), 200


def resolve_los_prediction(final_payload: dict) -> float:
    predicted_los = None
    if USE_LOCAL_AS_PRIMARY:
        if LOCAL_GATEWAY_ENABLED:
            try:
                predicted_los = invoke_local_gateway(final_payload)
            except Exception as e:
                logging.warning("Local LOS primary failed: %s", e)
        if predicted_los is None and CLOUD_ENABLED:
            predicted_los = invoke_cloud_gateway(final_payload)
    else:
        if CLOUD_ENABLED:
            predicted_los = invoke_cloud_gateway(final_payload)
        if LOCAL_GATEWAY_ENABLED:
            invoke_local_gateway_async(final_payload)
        if predicted_los is None and LOCAL_GATEWAY_ENABLED:
            predicted_los = invoke_local_gateway(final_payload)
    if predicted_los is None:
        raise RuntimeError("No LOS prediction from local or cloud")
    return float(predicted_los)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "fakeeh-los-proxy"}), 200


@app.route("/predict/lengthOfStay", methods=["POST"])
def get_length_of_stay():
    try:
        data = request.get_json()
        if not data:
            logging.warning("Empty/invalid json payload")
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        logging.info("📥 Raw request received: %s", json.dumps(data, indent=2, default=str))

        if "age" in data:
            data["AGE_GROUP"] = get_age_group(data["age"])
        else:
            data["AGE_GROUP"] = ""

        logging.info("Updated request:\n%s", json.dumps(data, indent=2, default=str))

        cleaned_raw, cleaned_for_encoding = normalize_raw_payload(data)
        logging.info("Cleaned raw payload: %s", json.dumps(cleaned_raw, indent=2, default=str))

        df_enc = pd.DataFrame([cleaned_for_encoding])
        encoded_df = encoder.transform(df_enc)
        model_payload = encoded_df.to_dict(orient="records")[0]
        logging.info("Encoded payload (from encoder): %s", json.dumps(model_payload, indent=2, default=str))

        model_payload["SODIUM_available"] = available_flag(cleaned_raw.get("SODIUM"))
        model_payload["BLOOD_UREA_NITROGEN_available"] = available_flag(cleaned_raw.get("BLOOD_UREA_NITROGEN"))
        model_payload["C_REACTIVE_PROTEIN_available"] = available_flag(cleaned_raw.get("C_REACTIVE_PROTEIN"))
        model_payload["CREATININE_available"] = available_flag(cleaned_raw.get("CREATININE"))
        model_payload["PLATELETS_COUNT_available"] = available_flag(cleaned_raw.get("PLATELETS_COUNT"))

        final_payload = {}
        for key, default in DEFAULT_INPUT_SCHEMA.items():
            if key in cleaned_raw and not (key.endswith("_encoded") or key.endswith("_available")):
                final_payload[key] = cleaned_raw.get(key, default)
            elif key in model_payload:
                val = model_payload.get(key, default)
                final_payload[key] = coerce_to_type(val, default)
            else:
                final_payload[key] = default

        try:
            with open(DERIVED_MAPPING_PATH, "r", encoding="utf-8") as f:
                mapping = json.load(f)
            primary_map = mapping.get("PRIMARY_encoded", {})
            primary_val = cleaned_raw.get("PRIMARY", "")
            final_payload["PRIMARY_encoded"] = primary_map.get(primary_val, final_payload["PRIMARY_encoded"])
            if final_payload["PRIMARY_encoded"] in (0, -1) and primary_val:
                icd_match = re.search(r"\b([A-Z]\d{2}(?:\.\d{1,2})?)\b", primary_val, re.IGNORECASE)
                if icd_match:
                    icd_code = icd_match.group(1).upper()
                    found = False
                    for k, v in primary_map.items():
                        if isinstance(k, str):
                            codes = [code.strip().upper() for code in k.split(",")]
                            if icd_code in codes:
                                final_payload["PRIMARY_encoded"] = v
                                logging.info(
                                    "Mapped PRIMARY_encoded using ICD code '%s' found in mapping key '%s' from PRIMARY: %s",
                                    icd_code, k, primary_val,
                                )
                                found = True
                                break
                    if not found:
                        icd_prefix = icd_code[:4] if "." in icd_code else icd_code[:3]
                        for k, v in primary_map.items():
                            if isinstance(k, str):
                                codes = [code.strip().upper() for code in k.split(",")]
                                if any(code.startswith(icd_prefix) for code in codes):
                                    final_payload["PRIMARY_encoded"] = v
                                    logging.info(
                                        "Mapped PRIMARY_encoded using ICD prefix '%s' from PRIMARY: %s",
                                        icd_prefix, primary_val,
                                    )
                                    found = True
                                    break
                        if not found:
                            logging.warning(
                                "Could not map PRIMARY_encoded using ICD code '%s' from PRIMARY: %s",
                                icd_code, primary_val,
                            )
                else:
                    logging.warning("Could not extract ICD code from PRIMARY: %s", primary_val)
            else:
                logging.info("PRIMARY_encoded found directly for PRIMARY: %s", primary_val)
        except Exception as e:
            logging.warning("Could not update PRIMARY_encoded from mapping.json: %s", e)

        final_payload["LOS_GROUP"] = predict_los_group(
            age_group_encoded=final_payload.get("AGE_GROUP_encoded", 0),
            ip_in_previous_30_days_encoded=final_payload.get("IP_IN_PREVIOUS_30_DAYS_encoded", 0),
            hospitalization_previous_year=final_payload.get("HOSPITALIZATION_PREVIOUS_YEAR", 0),
            admission_type_encoded=final_payload.get("ADMISSION_TYPE_encoded", 0),
            admission_level_encoded=final_payload.get("ADMISSION_LEVEL_encoded", 0),
            room_type_encoded=final_payload.get("ROOM_TYPE_encoded", 0),
        )

        def encode_los_group(los_group):
            mapping = {"SHORT": 0, "MEDIUM": 1, "LONG": 2}
            return mapping.get(str(los_group).upper(), 0)

        final_payload["LOS_GROUP_encoded"] = encode_los_group(final_payload.get("LOS_GROUP", "SHORT"))

        logging.info("🚀 Final payload (sent to Lambda): %s", json.dumps(final_payload, indent=2, default=str))

        predicted_los = resolve_los_prediction(final_payload)
        save_to_opensearch(data, predicted_los)
        return format_los_client_response(predicted_los)

    except requests.exceptions.Timeout:
        logging.exception("Request to API Gateway timed out")
        return jsonify({"error": "Request to API Gateway timed out"}), 504
    except requests.exceptions.RequestException as e:
        logging.exception("Request exception")
        return jsonify({"error": f"Request exception: {str(e)}"}), 500
    except Exception as e:
        logging.exception("Internal server error")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


if __name__ == "__main__":
    host = env_get("LOS_FLASK_HOST", "FLASK_HOST", default="0.0.0.0")
    port = int(env_get("LOS_FLASK_PORT", "FLASK_PORT", default="5015"))
    debug = env_bool("LOS_FLASK_DEBUG", "FLASK_DEBUG", default="false")

    ssl_cert = env_get("LOS_SSL_CERT", "SSL_CERT", default="/home/sysadmin/fakeeh.care/fullchain.pem")
    ssl_key = env_get("LOS_SSL_KEY", "SSL_KEY", default="/home/sysadmin/fakeeh.care/PK.key")
    use_ssl = env_bool("LOS_FLASK_USE_SSL", "FLASK_USE_SSL", default="true")

    ssl_context = None
    if use_ssl and os.path.isfile(ssl_cert) and os.path.isfile(ssl_key):
        ssl_context = (ssl_cert, ssl_key)
        logging.info("HTTPS  https://%s:%s/predict/lengthOfStay", host, port)
    else:
        logging.info("HTTP   http://%s:%s/predict/lengthOfStay", host, port)

    app.run(host=host, port=port, debug=debug, ssl_context=ssl_context, use_reloader=False, threaded=True)
