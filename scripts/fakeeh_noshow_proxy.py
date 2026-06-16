#!/usr/bin/env python3
"""
Fakeeh no-show Flask proxy — cloud inference unchanged + duplicate call to local ML gateway.

Cloud:  POST text/csv → apis.pragyaa.ai (unchanged)
Local:  POST JSON (background thread) → ml-gateway /v1/predict/no_show_fakeeh_ksa_local

The HTTP response contains only the cloud prediction. Local runs in parallel and
logs its result; it never blocks or changes the client response.

Environment:
  LOCAL_GATEWAY_URL      default http://127.0.0.1:8000/v1/predict/no_show_fakeeh_ksa_local
  LOCAL_GATEWAY_ENABLED  default true
  API_GATEWAY_URL        cloud endpoint (unchanged)
  SSL_CERT / SSL_KEY     default /home/sysadmin/fakeeh.care/fullchain.pem + PK.key
  FLASK_USE_SSL          default true (set false for plain HTTP)
  CLOUD_REQUEST_TIMEOUT  default 30 seconds
  FLASK_DEBUG            default false (do not use reloader under nohup)
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone

# Ensure logs appear immediately when stdout is redirected (nohup)
os.environ.setdefault("PYTHONUNBUFFERED", "1")

import pandas as pd
import requests
from flask import Flask, jsonify, request
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from urllib3.util.retry import Retry

from scripts.proxy_env import env_bool, env_get

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
    "API_GATEWAY_URL", "https://apis.pragyaa.ai/predict/predict-show-no-show"
)
API_GATEWAY_URL = env_get(
    "NOSHOW_CLOUD_URL",
    "API_GATEWAY_URL",
    default="https://apis.pragyaa.ai/predict/predict-show-no-show",
)
LOCAL_GATEWAY_URL = env_get(
    "NOSHOW_LOCAL_GATEWAY_URL",
    "LOCAL_GATEWAY_URL",
    default="http://127.0.0.1:8000/v1/predict/no_show_fakeeh_ksa_local",
)
LOCAL_GATEWAY_ENABLED = env_bool("NOSHOW_LOCAL_GATEWAY_ENABLED", "LOCAL_GATEWAY_ENABLED", default="true")
USE_LOCAL_PRIMARY = env_bool("NOSHOW_USE_LOCAL_PRIMARY", "USE_LOCAL_PRIMARY", default="false")
CLOUD_ENABLED = env_bool("NOSHOW_CLOUD_ENABLED", "CLOUD_ENABLED", default="true")

OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "https://10.1.186.40:9200/")
INDEX_NAME = env_get("NOSHOW_OPENSEARCH_INDEX", "OPENSEARCH_INDEX", default="fakeeh-prediction-no-show-index2")
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

REQUIRED_FIELDS = [
    "PROVIDER_NAME",
    "DEPARTMENT",
    "ALLOCATION_DATE_TIME",
    "ALLOCATION_DAY",
    "MRNO",
    "TOKEN_NO",
    "GIVEN_BY",
    "STATUS",
    "AGE",
    "REMARKS",
    "APPT_ALLOCATION_ID",
    "FACILITY_NAME",
    "GENDER",
    "VISIT_METHOD",
    "GIVEN_ON",
    "DOCTORS_NATIONALITY",
    "APPT_BOOKING_CHANNEL",
    "CITY",
    "VISIT_TYPE",
    "CONTRACT_NAME",
    "PAYMENT_STATUS",
]

INCOMING_FIELD_NAMES = [
    "PROVIDER_NAME",
    "DEPARTMENT",
    "ALLOCATION_DATE_TIME",
    "ALLOCATION_DAY",
    "STATUS",
    "TOKEN_NO",
    "GIVEN_BY",
    "FOLLOW_NEW",
    "AGE",
    "REMARKS",
    "APPT_ALLOCATION_ID",
    "NATIONALITY",
    "VIP",
    "FACILITY_NAME",
    "GENDER",
    "VISIT_METHOD",
    "GIVEN_ON",
    "DOCTORS_NATIONALITY",
    "APPT_BOOKING_CHANNEL",
    "CITY",
    "VISIT_TYPE",
    "CONTRACT_NAME",
    "PAYMENT_STATUS",
]


def values_to_csv_row(values: list) -> str:
    """RFC4180 CSV row for SageMaker tabular_serve (handles quotes, Arabic, commas)."""
    output = io.StringIO()
    csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\n").writerow(values)
    return output.getvalue()


def json_to_csv_string(json_request):
    if isinstance(json_request, str):
        json_request = json.loads(json_request)

    values = json_request["data"]["features"]["values"]

    return values_to_csv_row(values[0]).strip()


def save_to_opensearch(input_data, prediction):
    try:
        input_list = input_data.strip('"').split('","')

        prediction_parts = prediction.split(",")
        if len(prediction_parts) < 2:
            raise ValueError("Prediction response format is invalid.")

        prediction_status = prediction_parts[0].strip()
        probability = float(prediction_parts[1].strip())
        logger.info("Prediction status: %s, Probability: %s", prediction_status, probability)

        def format_date(value):
            try:
                return datetime.strptime(value.strip('"'), "%d-%m-%Y %H:%M").strftime(
                    "%d-%m-%Y %H:%M"
                )
            except ValueError:
                return None

        def clean_string(value):
            return value.strip('"') if isinstance(value, str) else value

        processed_data = {
            "PROVIDER_NAME": clean_string(input_list[0]),
            "DEPARTMENT": clean_string(input_list[1]),
            "ALLOCATION_DATE_TIME": format_date(input_list[2]),
            "ALLOCATION_DAY": clean_string(input_list[3]),
            "STATUS": clean_string(input_list[4]),
            "TOKEN_NO": clean_string(input_list[5]),
            "GIVEN_BY": clean_string(input_list[6]),
            "FOLLOW_NEW": clean_string(input_list[7]),
            "AGE": clean_string(input_list[8]),
            "REMARKS": clean_string(input_list[9]),
            "APPT_ALLOCATION_ID": clean_string(input_list[10]),
            "NATIONALITY": clean_string(input_list[11]),
            "VIP": clean_string(input_list[12]) == "1",
            "FACILITY_NAME": clean_string(input_list[13]),
            "GENDER": clean_string(input_list[14]),
            "VISIT_METHOD": clean_string(input_list[15]),
            "GIVEN_ON": format_date(input_list[16]),
            "DOCTORS_NATIONALITY": clean_string(input_list[17]),
            "APPT_BOOKING_CHANNEL": clean_string(input_list[18]),
            "CITY": clean_string(input_list[19]),
            "VISIT_TYPE": clean_string(input_list[20]),
            "CONTRACT_NAME": clean_string(input_list[21]),
            "PAYMENT_STATUS": clean_string(input_list[22]),
            "status": prediction_status,
            "probability": probability,
            "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "API Endpoint",
        }

        url = f"{OPENSEARCH_URL}{INDEX_NAME}/_doc/"
        response = session.post(
            url,
            json=processed_data,
            headers=HEADERS,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            verify=False,
            timeout=OPENSEARCH_TIMEOUT,
        )

        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to index data: {response.status_code} {response.text}")

        print("Data successfully indexed in OpenSearch.")

    except Exception as e:
        print(f"Error saving data to OpenSearch: {e}")


def invoke_api_gateway(csv_data: str):
    headers = {"Content-Type": "text/csv; charset=utf-8"}
    try:
        body = csv_data.encode("utf-8") if isinstance(csv_data, str) else csv_data
        logger.info("Calling cloud API (timeout=%ss): %s", CLOUD_REQUEST_TIMEOUT, API_GATEWAY_URL)
        response = requests.post(
            API_GATEWAY_URL,
            data=body,
            headers=headers,
            timeout=CLOUD_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        logger.error("Cloud API timed out after %ss", CLOUD_REQUEST_TIMEOUT)
        return None
    except requests.exceptions.RequestException as e:
        logger.error("Error calling API Gateway: %s", str(e))
        return None


def invoke_local_gateway_async(cloud_inputs: dict) -> None:
    """Fire-and-forget duplicate to ml-gateway; does not block the cloud response."""

    def _run() -> None:
        payload = {
            "client_id": "fakeeh-flask-proxy",
            "inputs": cloud_inputs,
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
                    "Local gateway (async) HTTP %s: %s",
                    response.status_code,
                    body.get("detail", response.text),
                )
                return
            body = response.json() if response.content else {}
            logger.info("Local gateway (async) prediction: %s", body.get("prediction"))
        except requests.exceptions.RequestException as e:
            logger.error("Local gateway (async) error: %s", e)

    thread = threading.Thread(target=_run, name="local-gateway-dup", daemon=True)
    thread.start()


def invoke_local_gateway_sync(cloud_inputs: dict) -> str:
    """Local gateway inference (blocking). Returns SageMaker-style CSV string."""
    payload = {"client_id": "fakeeh-flask-proxy", "inputs": cloud_inputs}
    response = requests.post(
        LOCAL_GATEWAY_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    response.raise_for_status()
    body = response.json() if response.content else {}
    pred = body.get("prediction")
    return pred if isinstance(pred, str) else ("" if pred is None else str(pred))


def to_epoch(date_val):
    try:
        return int(pd.to_datetime(date_val).timestamp() * 1000)
    except Exception:
        return ""


def build_cloud_inputs(incoming_json: dict) -> tuple[dict, list, str]:
    """Build the same 21-field row + CSV string used for cloud inference."""
    raw_values = incoming_json["data"]["features"]["values"][0]
    incoming_dict = dict(zip(INCOMING_FIELD_NAMES, raw_values))

    if "ALLOCATION_DATE_TIME" in incoming_dict:
        incoming_dict["ALLOCATION_DATE_TIME"] = to_epoch(incoming_dict["ALLOCATION_DATE_TIME"])

    if "GIVEN_ON" in incoming_dict:
        incoming_dict["GIVEN_ON"] = to_epoch(incoming_dict["GIVEN_ON"])

    ordered_values = [incoming_dict.get(field, "") for field in REQUIRED_FIELDS]
    cloud_inputs = dict(zip(REQUIRED_FIELDS, ordered_values))
    input_csv = values_to_csv_row(ordered_values)
    return cloud_inputs, ordered_values, input_csv


@app.before_request
def log_request_info():
    logger.info("Handling request: %s %s", request.method, request.url)
    logger.info("Request headers: %s", request.headers)


@app.after_request
def log_response_info(response):
    logger.info("Response status: %s", response.status)
    return response


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "fakeeh-noshow-proxy"}), 200


@app.route("/predict/getPrediction", methods=["POST"])
def predict():
    try:
        incoming_json = request.json
        input_data = request.json
        logger.info("Received JSON data: %s", input_data)

        if (
            incoming_json is None
            or "data" not in incoming_json
            or incoming_json["data"] is None
            or "features" not in incoming_json["data"]
            or incoming_json["data"]["features"] is None
            or "values" not in incoming_json["data"]["features"]
            or incoming_json["data"]["features"]["values"] is None
        ):
            raise ValueError("Incoming JSON is missing required keys or contains None values.")

        cloud_inputs, _ordered_values, input_csv = build_cloud_inputs(incoming_json)
        data = json_to_csv_string(input_data)

        prediction = None

        if USE_LOCAL_PRIMARY:
            logger.info("Calling local gateway (primary): %s", LOCAL_GATEWAY_URL)
            try:
                prediction = invoke_local_gateway_sync(cloud_inputs)
                logger.info("Received prediction from local gateway: %s", prediction)
            except Exception:
                logger.exception("Local gateway (primary) failed")
                prediction = None

        if prediction is None and CLOUD_ENABLED:
            # In cloud-primary mode, optionally fire local in background for comparison
            if (not USE_LOCAL_PRIMARY) and LOCAL_GATEWAY_ENABLED:
                invoke_local_gateway_async(cloud_inputs)

            prediction = invoke_api_gateway(input_csv)
            logger.info("Received prediction from API Gateway: %s", prediction)
            if not prediction:
                return jsonify({"error": "No prediction received from API Gateway (timeout or upstream error)"}), 504

        save_to_opensearch(data, prediction)

        # EXACT same output formatting regardless of source
        return jsonify({"prediction": prediction.rstrip("\n") + "\n"}), 200

    except Exception as e:
        logger.error("Exception occurred: %s", str(e))
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(env_get("NOSHOW_FLASK_PORT", "FLASK_PORT", default="5010"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")

    ssl_cert = os.getenv("SSL_CERT", "/home/sysadmin/fakeeh.care/fullchain.pem")
    ssl_key = os.getenv("SSL_KEY", "/home/sysadmin/fakeeh.care/PK.key")
    use_ssl = env_bool("NOSHOW_FLASK_USE_SSL", "FLASK_USE_SSL", default="true")

    ssl_context = None
    if use_ssl:
        if os.path.isfile(ssl_cert) and os.path.isfile(ssl_key):
            ssl_context = (ssl_cert, ssl_key)
            logger.info("HTTPS  https://%s:%s/predict/getPrediction", host, port)
        else:
            logger.error(
                "SSL cert/key not found (%s, %s) — falling back to HTTP. "
                "Use curl http://... or set SSL_CERT/SSL_KEY.",
                ssl_cert,
                ssl_key,
            )
            logger.info("HTTP   http://%s:%s/predict/getPrediction", host, port)
    else:
        logger.info("HTTP   http://%s:%s/predict/getPrediction (FLASK_USE_SSL=false)", host, port)

    app.run(
        host=host,
        port=port,
        debug=debug,
        ssl_context=ssl_context,
        use_reloader=False,
        threaded=True,
    )
