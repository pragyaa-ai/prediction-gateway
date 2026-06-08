#!/usr/bin/env python3
"""
Fakeeh delayed-arrival Flask proxy.

Cloud (primary): POST JSON → apis.pragyaa.ai/arrive/get-delayed-time
Local (async):   POST raw appointment JSON → ml-gateway delay_fakeeh_ksa_local

Client response is cloud-only. Local runs in a background thread.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYTHONUNBUFFERED", "1")

import requests
from flask import Flask, jsonify, request
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.delay_features import (  # noqa: E402
    prepare_fakeeh_delay_cloud_payload,
    prepare_fakeeh_delay_model_input,
)

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

CLOUD_REQUEST_TIMEOUT = int(os.getenv("CLOUD_REQUEST_TIMEOUT", "30"))
OPENSEARCH_TIMEOUT = int(os.getenv("OPENSEARCH_TIMEOUT", "15"))

API_GATEWAY_URL = os.getenv(
    "API_GATEWAY_URL", "https://apis.pragyaa.ai/arrive/get-delayed-time"
)
LOCAL_GATEWAY_URL = os.getenv(
    "LOCAL_GATEWAY_URL",
    "http://127.0.0.1:8000/v1/predict/delay_fakeeh_ksa_local",
)
LOCAL_GATEWAY_ENABLED = os.getenv("LOCAL_GATEWAY_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)

OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "https://10.1.186.40:9200/")
INDEX_NAME = os.getenv("OPENSEARCH_INDEX", "delayed-arrival-index")
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
USERNAME = os.getenv("OPENSEARCH_USER", "admin")
PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "admin")

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


def save_to_opensearch(input_data: dict, prediction) -> None:
    try:
        def safe_get(key):
            return input_data.get(key) if isinstance(input_data, dict) else None

        def fmt_date_to_ddMMyyyy_HHMM(dt_str):
            if not dt_str:
                return None
            for fmt_in in ("%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
                try:
                    dt = datetime.strptime(str(dt_str), fmt_in)
                    return dt.strftime("%d/%m/%Y %H:%M")
                except ValueError:
                    continue
            return None

        doc = {
            "MRNO": str(safe_get("MRNO")) if safe_get("MRNO") is not None else None,
            "PROVIDER_NAME": safe_get("PROVIDER_NAME"),
            "DEPARTMENT": safe_get("DEPARTMENT"),
            "APPT_ALLOCATION_ID": (
                str(safe_get("APPT_ALLOCATION_ID"))
                if safe_get("APPT_ALLOCATION_ID") is not None
                else None
            ),
            "ALLOCATION_DATE_TIME": fmt_date_to_ddMMyyyy_HHMM(safe_get("ALLOCATION_DATE_TIME")),
            "ALLOCATION_DAY": safe_get("ALLOCATION_DAY"),
            "TOKEN_NO": str(safe_get("TOKEN_NO")) if safe_get("TOKEN_NO") is not None else None,
            "VIP": int(safe_get("VIP")) if safe_get("VIP") is not None else None,
            "GIVEN_BY": safe_get("GIVEN_BY"),
            "FOLLOW_NEW": safe_get("FOLLOW_NEW"),
            "AGE": safe_get("AGE"),
            "NATIONALITY": safe_get("NATIONALITY"),
            "FACILITY_NAME": safe_get("FACILITY_NAME"),
            "GENDER": safe_get("GENDER"),
            "VISIT_METHOD": safe_get("VISIT_METHOD"),
            "GIVEN_ON": fmt_date_to_ddMMyyyy_HHMM(safe_get("GIVEN_ON")),
            "DOCTORS_NATIONALITY": safe_get("DOCTORS_NATIONALITY"),
            "APPT_BOOKING_CHANNEL": safe_get("APPT_BOOKING_CHANNEL"),
            "CITY": safe_get("CITY"),
            "PAYMENT_STATUS": safe_get("PAYMENT_STATUS"),
            "VISIT_TYPE": safe_get("VISIT_TYPE"),
            "CONTRACT_NAME": safe_get("CONTRACT_NAME"),
            "Delay_Prediction": float(prediction) if prediction is not None else None,
            "ingest_ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        url = f"{OPENSEARCH_URL.rstrip('/')}/{INDEX_NAME}/_doc/"
        response = session.post(
            url,
            json=doc,
            headers=HEADERS,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            verify=False,
            timeout=OPENSEARCH_TIMEOUT,
        )
        if not (200 <= response.status_code < 300):
            raise RuntimeError(f"Failed to index data: {response.status_code} {response.text}")
        logger.info("Indexed delay prediction in OpenSearch")
    except Exception as e:
        logger.error("Error saving data to OpenSearch: %s", e)


def invoke_local_gateway_async(raw_input: dict) -> None:
    def _run() -> None:
        # Same 161-column wide row the cloud API receives
        payload = {
            "client_id": "fakeeh-flask-delay-proxy",
            "inputs": prepare_fakeeh_delay_model_input(raw_input),
        }
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
                    "Local delay gateway HTTP %s: %s",
                    response.status_code,
                    body.get("detail", response.text),
                )
                return
            body = response.json() if response.content else {}
            logger.info("Local delay gateway prediction: %s", body.get("prediction"))
        except requests.RequestException as e:
            logger.error("Local delay gateway error: %s", e)

    threading.Thread(target=_run, name="local-delay-dup", daemon=True).start()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "fakeeh-delay-proxy"}), 200


@app.route("/arrive/get-delayed-time", methods=["POST"])
def predict():
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object body")

        logger.info("Received delay payload: %s", data)
        payload = prepare_fakeeh_delay_cloud_payload(data)
        logger.info("Cloud payload: %s", json.dumps(payload))

        if LOCAL_GATEWAY_ENABLED:
            invoke_local_gateway_async(data)

        logger.info("Calling cloud API (timeout=%ss): %s", CLOUD_REQUEST_TIMEOUT, API_GATEWAY_URL)
        response = requests.post(API_GATEWAY_URL, json=payload, timeout=CLOUD_REQUEST_TIMEOUT)
        response.raise_for_status()
        model_response = response.json()
        predicted_time = model_response.get("body", {}).get("delayed_arrival")

        save_to_opensearch(data, predicted_time)

        return app.response_class(
            response=json.dumps({"Predicted Delayed Time": predicted_time}, indent=4),
            status=200,
            mimetype="application/json",
        )
    except Exception as e:
        logger.exception("Delay prediction failed")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5030"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")

    ssl_cert = os.getenv("SSL_CERT", "/home/sysadmin/fakeeh.care/fullchain.pem")
    ssl_key = os.getenv("SSL_KEY", "/home/sysadmin/fakeeh.care/PK.key")
    use_ssl = os.getenv("FLASK_USE_SSL", "true").lower() in ("1", "true", "yes")

    ssl_context = None
    if use_ssl:
        if os.path.isfile(ssl_cert) and os.path.isfile(ssl_key):
            ssl_context = (ssl_cert, ssl_key)
            logger.info("HTTPS  https://%s:%s/arrive/get-delayed-time", host, port)
        else:
            logger.error(
                "SSL cert/key not found (%s, %s) — falling back to HTTP",
                ssl_cert,
                ssl_key,
            )
            logger.info("HTTP   http://%s:%s/arrive/get-delayed-time", host, port)
    else:
        logger.info("HTTP   http://%s:%s/arrive/get-delayed-time", host, port)

    app.run(host=host, port=port, debug=debug, ssl_context=ssl_context, use_reloader=False, threaded=True)
