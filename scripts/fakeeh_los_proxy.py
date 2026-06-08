#!/usr/bin/env python3
"""
Fakeeh Length-of-Stay Flask proxy.

Cloud (primary): POST encoded payload → apis.pragyaa.ai/stay/predict
Local (async):   POST encoded payload → ml-gateway los_fakeeh_ksa_local

Client response is cloud-only.  Local runs in a background thread.

Feature engineering (normalize → encode → LOS_GROUP) mirrors the
LengthOfStay reference proxy exactly, producing the same final_payload
that is sent to both the cloud API and the local gateway.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

os.environ.setdefault("PYTHONUNBUFFERED", "1")

import requests
from flask import Flask, jsonify, request
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.sagemaker_format import parse_regression_prediction  # noqa: E402

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (all overridable via env vars)
# ---------------------------------------------------------------------------
CLOUD_REQUEST_TIMEOUT = int(os.getenv("CLOUD_REQUEST_TIMEOUT", "30"))
OPENSEARCH_TIMEOUT = int(os.getenv("OPENSEARCH_TIMEOUT", "15"))

API_GATEWAY_URL = os.getenv("LOS_CLOUD_URL", "https://apis.pragyaa.ai/stay/predict")
LOCAL_GATEWAY_URL = os.getenv(
    "LOS_LOCAL_GATEWAY_URL",
    "http://127.0.0.1:8000/v1/predict/los_fakeeh_ksa_local",
)
LOCAL_GATEWAY_ENABLED = os.getenv("LOCAL_GATEWAY_ENABLED", "true").lower() in (
    "1", "true", "yes",
)

OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "https://10.1.186.40:9200/")
INDEX_NAME = os.getenv("LOS_OPENSEARCH_INDEX", "length-of-stay-index")
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
USERNAME = os.getenv("OPENSEARCH_USER", "admin")
PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "admin")

# Path to derived_mapping.json (override via env var; falls back to scripts/ dir)
DERIVED_MAPPING_PATH = os.getenv(
    "LOS_DERIVED_MAPPING_PATH",
    str(Path(__file__).resolve().parent / "derived_mapping.json"),
)

# Optional encoder import — only needed if derived_mapping.json is present
try:
    _encoder_dir = str(Path(DERIVED_MAPPING_PATH).parent)
    if _encoder_dir not in sys.path:
        sys.path.insert(0, _encoder_dir)
    from los_encoder import LOSDataEncoder  # type: ignore
    import pandas as pd  # required by LOSDataEncoder
    _encoder = LOSDataEncoder(DERIVED_MAPPING_PATH) if os.path.isfile(DERIVED_MAPPING_PATH) else None
    if _encoder:
        logger.info("LOSDataEncoder loaded from %s", DERIVED_MAPPING_PATH)
    else:
        logger.warning("derived_mapping.json not found at %s — encoder disabled", DERIVED_MAPPING_PATH)
except Exception as _enc_err:
    logger.warning("LOSDataEncoder unavailable (%s) — encoded fields will use rule-based fallback", _enc_err)
    _encoder = None
    pd = None  # type: ignore

# ---------------------------------------------------------------------------
# Retry-enabled session for OpenSearch
# ---------------------------------------------------------------------------
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE"],
)
_adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", _adapter)
session.mount("https://", _adapter)

# ---------------------------------------------------------------------------
# EXACT model schema (keys + defaults, keeps order)
# ---------------------------------------------------------------------------
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

FIELDS_STRIP_UNITS = {
    "SODIUM",
    "BLOOD_UREA_NITROGEN",
    "C_REACTIVE_PROTEIN",
    "CREATININE",
    "PLATELETS_COUNT",
}

# ---------------------------------------------------------------------------
# Feature-engineering helpers (identical logic to LengthOfStay reference proxy)
# ---------------------------------------------------------------------------

def _derive_age_group(age) -> str:
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


def _get_age_group(age) -> Optional[str]:
    if age is None:
        return None
    try:
        a = int(age)
    except Exception:
        return None
    if a <= 12:
        return "Child"
    if 13 <= a <= 39:
        return "Young_Adult"
    if 40 <= a <= 49:
        return "Adult"
    if 50 <= a <= 64:
        return "Middle_Aged"
    return "Senior"


def _parse_bool_like(val) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    s = str(val).strip().lower()
    if s in ("yes", "y", "true", "1", "t"):
        return True
    return False


def _available_flag(val) -> int:
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
            return 1 if float(m.group()) != 0 else 0
        except Exception:
            return 1
    return 1


def _coerce_to_type(value, default):
    if isinstance(default, bool):
        return bool(_parse_bool_like(value))
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


def _strip_units(value):
    if isinstance(value, str):
        m = re.search(r"[-+]?\d*\.?\d+", value)
        if m:
            try:
                return float(m.group())
            except ValueError:
                return value
    return value


def _clean_primary(value):
    if isinstance(value, str):
        return re.sub(r"[,\s]*unspecified\s*$", "", value, flags=re.IGNORECASE)
    return value


def _predict_los_group(
    age_group_encoded: int,
    ip_in_previous_30_days_encoded: int,
    hospitalization_previous_year: int,
    admission_type_encoded: int,
    admission_level_encoded: int,
    room_type_encoded: int,
) -> str:
    score = 0
    if age_group_encoded == 0:
        score += 1
    elif age_group_encoded == 2:
        score += 1
    elif age_group_encoded == 3:
        score += 2
    if ip_in_previous_30_days_encoded == 1:
        score += 2
    if hospitalization_previous_year > 1:
        score += 1
    long_stay = [1, 3, 4, 11, 12, 16, 17, 20]
    medium_stay = [2, 5, 6, 7, 8, 10, 13, 18, 21]
    if admission_level_encoded in long_stay:
        score += 2
    elif admission_level_encoded in medium_stay:
        score += 1
    if room_type_encoded == 1:
        score += 2
    elif room_type_encoded in [2, 3]:
        score += 1
    if score <= 3:
        return "SHORT"
    if score <= 6:
        return "MEDIUM"
    return "LONG"


def _encode_los_group(los_group: str) -> int:
    return {"SHORT": 0, "MEDIUM": 1, "LONG": 2}.get(str(los_group).upper(), 0)


def _normalize_raw_payload(incoming: dict):
    """
    Returns (cleaned_raw, cleaned_for_encoding).
    Identical logic to the LengthOfStay reference proxy.
    """
    incoming_lc = {str(k).lower(): k for k in incoming.keys()}
    cleaned_raw: dict = {}

    for k, default in DEFAULT_INPUT_SCHEMA.items():
        if k.endswith("_encoded") or k.endswith("_available"):
            continue
        incoming_key = incoming_lc.get(k.lower(), k)
        val = incoming.get(incoming_key, default)
        if k in FIELDS_STRIP_UNITS:
            val = _strip_units(val)
        if k == "PRIMARY":
            val = _clean_primary(val)
        coerced = _coerce_to_type(val, default)
        if k == "AGE" and isinstance(coerced, float):
            coerced = int(coerced)
        cleaned_raw[k] = coerced

    if not cleaned_raw.get("AGE_GROUP"):
        cleaned_raw["AGE_GROUP"] = _derive_age_group(cleaned_raw.get("AGE", 0))

    cleaned_raw["EXPIRED"] = _parse_bool_like(cleaned_raw.get("EXPIRED"))
    cleaned_raw["IP_IN_PREVIOUS_30_DAYS"] = _parse_bool_like(cleaned_raw.get("IP_IN_PREVIOUS_30_DAYS"))

    cleaned_for_encoding = dict(cleaned_raw)
    cleaned_for_encoding["EXPIRED"] = "Yes" if cleaned_raw["EXPIRED"] else "No"
    cleaned_for_encoding["IP_IN_PREVIOUS_30_DAYS"] = "Yes" if cleaned_raw["IP_IN_PREVIOUS_30_DAYS"] else "No"

    return cleaned_raw, cleaned_for_encoding


def _build_final_payload(cleaned_raw: dict, cleaned_for_encoding: dict) -> dict:
    """
    Run encoder (if available) then compute availability flags, LOS_GROUP,
    PRIMARY_encoded ICD mapping — mirrors LengthOfStay reference proxy exactly.
    """
    # Encoder step
    if _encoder is not None and pd is not None:
        try:
            df_enc = pd.DataFrame([cleaned_for_encoding])
            encoded_df = _encoder.transform(df_enc)
            model_payload = encoded_df.to_dict(orient="records")[0]
        except Exception as enc_err:
            logger.warning("Encoder failed (%s), using rule-based fallback", enc_err)
            model_payload = dict(cleaned_for_encoding)
    else:
        model_payload = dict(cleaned_for_encoding)

    # Recompute availability flags (overrides encoder)
    model_payload["SODIUM_available"] = _available_flag(cleaned_raw.get("SODIUM"))
    model_payload["BLOOD_UREA_NITROGEN_available"] = _available_flag(cleaned_raw.get("BLOOD_UREA_NITROGEN"))
    model_payload["C_REACTIVE_PROTEIN_available"] = _available_flag(cleaned_raw.get("C_REACTIVE_PROTEIN"))
    model_payload["CREATININE_available"] = _available_flag(cleaned_raw.get("CREATININE"))
    model_payload["PLATELETS_COUNT_available"] = _available_flag(cleaned_raw.get("PLATELETS_COUNT"))

    # Build final payload from schema order
    final_payload: dict = {}
    for key, default in DEFAULT_INPUT_SCHEMA.items():
        if key in cleaned_raw and not (key.endswith("_encoded") or key.endswith("_available")):
            final_payload[key] = cleaned_raw.get(key, default)
        elif key in model_payload:
            final_payload[key] = _coerce_to_type(model_payload.get(key, default), default)
        else:
            final_payload[key] = default

    # PRIMARY_encoded: ICD mapping from derived_mapping.json
    try:
        if os.path.isfile(DERIVED_MAPPING_PATH):
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
                            codes = [c.strip().upper() for c in k.split(",")]
                            if icd_code in codes:
                                final_payload["PRIMARY_encoded"] = v
                                found = True
                                break
                    if not found:
                        icd_prefix = icd_code[:4] if "." in icd_code else icd_code[:3]
                        for k, v in primary_map.items():
                            if isinstance(k, str):
                                codes = [c.strip().upper() for c in k.split(",")]
                                if any(c.startswith(icd_prefix) for c in codes):
                                    final_payload["PRIMARY_encoded"] = v
                                    break
    except Exception as e:
        logger.warning("Could not update PRIMARY_encoded from mapping.json: %s", e)

    # LOS_GROUP rule-based prediction
    final_payload["LOS_GROUP"] = _predict_los_group(
        age_group_encoded=final_payload.get("AGE_GROUP_encoded", 0),
        ip_in_previous_30_days_encoded=final_payload.get("IP_IN_PREVIOUS_30_DAYS_encoded", 0),
        hospitalization_previous_year=final_payload.get("HOSPITALIZATION_PREVIOUS_YEAR", 0),
        admission_type_encoded=final_payload.get("ADMISSION_TYPE_encoded", 0),
        admission_level_encoded=final_payload.get("ADMISSION_LEVEL_encoded", 0),
        room_type_encoded=final_payload.get("ROOM_TYPE_encoded", 0),
    )
    final_payload["LOS_GROUP_encoded"] = _encode_los_group(final_payload["LOS_GROUP"])

    return final_payload


# ---------------------------------------------------------------------------
# OpenSearch
# ---------------------------------------------------------------------------

def save_to_opensearch(input_data: dict, prediction) -> None:
    try:
        def sg(key):
            return input_data.get(key) if isinstance(input_data, dict) else None

        doc = {
            "MRNO": str(sg("MRNO")) if sg("MRNO") is not None else None,
            "AGE": sg("AGE"),
            "MARITAL_STATUS": sg("MARITAL_STATUS"),
            "NATIONALITY": sg("NATIONALITY"),
            "BMI": sg("BMI"),
            "ADMISSION_TYPE": sg("ADMISSION_TYPE"),
            "ADMISSION_LEVEL": sg("ADMISSION_LEVEL"),
            "ROOM_TYPE": sg("ROOM_TYPE"),
            "SOURCE_OF_ADMN": sg("SOURCE_OF_ADMN"),
            "PRIMARY": sg("PRIMARY"),
            "SECONDARY": sg("SECONDARY"),
            "SURGERY_NAME": sg("SURGERY_NAME"),
            "PAYER": sg("PAYER"),
            "PREVIOUS_IP": sg("PREVIOUS_IP"),
            "EXPIRED": sg("EXPIRED"),
            "LOS_GROUP": sg("LOS_GROUP"),
            "IP_IN_PREVIOUS_30_DAYS": sg("IP_IN_PREVIOUS_30_DAYS"),
            "HOSPITALIZATION_PREVIOUS_YEAR": sg("HOSPITALIZATION_PREVIOUS_YEAR"),
            "LOS_Prediction": float(prediction) if prediction is not None else None,
            "ingest_ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        url = f"{OPENSEARCH_URL.rstrip('/')}/{INDEX_NAME}/_doc/"
        resp = session.post(
            url,
            json=doc,
            headers=HEADERS,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            verify=False,
            timeout=OPENSEARCH_TIMEOUT,
        )
        if not (200 <= resp.status_code < 300):
            raise RuntimeError(f"Failed to index data: {resp.status_code} {resp.text}")
        logger.info("Indexed LOS prediction in OpenSearch")
    except Exception as e:
        logger.error("Error saving data to OpenSearch: %s", e)


# ---------------------------------------------------------------------------
# Local gateway (async, fire-and-forget)
# ---------------------------------------------------------------------------

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


def invoke_local_gateway_async(final_payload: dict) -> None:
    def _run() -> None:
        payload = {"client_id": "fakeeh-flask-los-proxy", "inputs": final_payload}
        try:
            response = requests.post(
                LOCAL_GATEWAY_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120,
            )
            if response.status_code != 200:
                body = response.json() if response.content else {}
                logger.warning(
                    "Local LOS gateway HTTP %s: %s",
                    response.status_code,
                    body.get("detail", response.text),
                )
                return
            body = response.json() if response.content else {}
            days = _local_los_days(body)
            if days is not None:
                logger.info("Local LOS gateway prediction: %.4f days", days)
            else:
                logger.info("Local LOS gateway prediction: %s", body.get("prediction"))
        except requests.RequestException as e:
            logger.error("Local LOS gateway error: %s", e)

    threading.Thread(target=_run, name="local-los-dup", daemon=True).start()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "fakeeh-los-proxy"}), 200


@app.route("/predict/lengthOfStay", methods=["POST"])
def get_length_of_stay():
    try:
        data = request.get_json()
        if not data:
            logger.warning("Empty/invalid JSON payload")
            return jsonify({"error": "Invalid or missing JSON payload"}), 400

        logger.info("Raw LOS request: %s", json.dumps(data, default=str))

        # Add AGE_GROUP if missing
        if "AGE_GROUP" not in data:
            age_key = next((k for k in data if k.lower() == "age"), None)
            data["AGE_GROUP"] = _get_age_group(data[age_key]) if age_key else ""

        # Feature engineering
        cleaned_raw, cleaned_for_encoding = _normalize_raw_payload(data)
        final_payload = _build_final_payload(cleaned_raw, cleaned_for_encoding)

        logger.info("Final LOS payload: %s", json.dumps(final_payload, default=str))

        # Fire local gateway in background
        if LOCAL_GATEWAY_ENABLED:
            invoke_local_gateway_async(final_payload)

        # Cloud call — flat final_payload (same as original LengthOfStay proxy)
        logger.info("Calling cloud LOS API (timeout=%ss): %s", CLOUD_REQUEST_TIMEOUT, API_GATEWAY_URL)
        resp = requests.post(
            API_GATEWAY_URL,
            json=final_payload,
            headers={"Content-Type": "application/json"},
            timeout=CLOUD_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        logger.info("Cloud LOS response %s: %s", resp.status_code, resp.text)

        try:
            outer = resp.json()
        except Exception:
            return jsonify({"error": "Invalid JSON from cloud API", "raw": resp.text}), 502

        # Parse prediction from outer or nested body
        predicted_los = None
        if "body" in outer:
            try:
                inner = json.loads(outer["body"]) if isinstance(outer["body"], str) else outer["body"]
            except Exception:
                inner = {}
            predicted_los = (
                inner.get("Predicted_length_of_stay")
                or inner.get("predicted_los")
                or inner.get("predicted_length_of_stay")
            )
        if predicted_los is None:
            predicted_los = (
                outer.get("Predicted_length_of_stay")
                or outer.get("predicted_los")
                or outer.get("predicted_length_of_stay")
            )

        if predicted_los is None:
            logger.error("Predicted_length_of_stay not found in response: %s", json.dumps(outer, default=str))
            return jsonify({"error": "Predicted_length_of_stay not found in cloud response"}), 500

        save_to_opensearch(final_payload, predicted_los)

        return app.response_class(
            response=json.dumps({"Length of Stay": round(float(predicted_los), 2)}, indent=4),
            status=200,
            mimetype="application/json",
        )

    except requests.exceptions.Timeout:
        logger.exception("Cloud LOS API timed out")
        return jsonify({"error": "Request to cloud API timed out"}), 504
    except requests.exceptions.RequestException as e:
        logger.exception("Request exception")
        return jsonify({"error": f"Request exception: {str(e)}"}), 500
    except Exception as e:
        logger.exception("Internal server error")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5015"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")

    ssl_cert = os.getenv("SSL_CERT", "/home/sysadmin/fakeeh.care/fullchain.pem")
    ssl_key = os.getenv("SSL_KEY", "/home/sysadmin/fakeeh.care/PK.key")
    use_ssl = os.getenv("FLASK_USE_SSL", "true").lower() in ("1", "true", "yes")

    ssl_context = None
    if use_ssl:
        if os.path.isfile(ssl_cert) and os.path.isfile(ssl_key):
            ssl_context = (ssl_cert, ssl_key)
            logger.info("HTTPS  https://%s:%s/predict/lengthOfStay", host, port)
        else:
            logger.error(
                "SSL cert/key not found (%s, %s) — falling back to HTTP",
                ssl_cert, ssl_key,
            )
            logger.info("HTTP   http://%s:%s/predict/lengthOfStay", host, port)
    else:
        logger.info("HTTP   http://%s:%s/predict/lengthOfStay", host, port)

    app.run(
        host=host,
        port=port,
        debug=debug,
        ssl_context=ssl_context,
        use_reloader=False,
        threaded=True,
    )
