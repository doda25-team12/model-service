"""
Flask API of the SMS Spam detection model model.
"""
import os
import time
import joblib
from flask import Flask, jsonify, request, Response
from flasgger import Swagger
import pandas as pd
import requests

from text_preprocessing import prepare, _extract_message_len, _text_process
from metrics import metrics


# Directory where the model files should be found or placed
MODEL_STORAGE = "output"
os.makedirs(MODEL_STORAGE, exist_ok=True)

# Read environment variables
MODEL_VERSION = os.getenv("MODEL_VERSION")
DOWNLOAD_BASE = os.getenv("MODEL_BASE_URL") or ""

if not MODEL_VERSION:
    raise RuntimeError("A model version must be provided through MODEL_VERSION.")

# File locations
MODEL_FILE = f"model-{MODEL_VERSION}.joblib"
MODEL_FULL_PATH = os.path.join(MODEL_STORAGE, MODEL_FILE)
PREPROC_FULL_PATH = os.path.join(MODEL_STORAGE, "preprocessor.joblib")


# ========== Internal utilities ========== #

def fetch_if_missing(source_url, destination):
    """Retrieve a file from a URL only when it's not already present."""
    if os.path.isfile(destination):
        return

    if not source_url:
        raise RuntimeError(
            f"Missing required file '{destination}' and no download source was given."
        )

    print(f"[model-service] Fetching model artifact: {source_url}")
    response = requests.get(source_url, timeout=30)
    response.raise_for_status()

    with open(destination, "wb") as out:
        out.write(response.content)

    print(f"[model-service] Saved artifact to {destination}")


def prepare_model_files():
    """
    Make sure the model and preprocessor are available.
    If missing, attempt to download them once using the configured source.
    """
    model_ready = os.path.isfile(MODEL_FULL_PATH)
    preproc_ready = os.path.isfile(PREPROC_FULL_PATH)

    # Case 1: Everything is already mounted and ready
    if model_ready and preproc_ready:
        print("[model-service] Using model and preprocessor from mounted storage.")
        return

    # Case 2: Missing files and no download configuration available
    if not DOWNLOAD_BASE:
        raise RuntimeError(
            "Required model files are missing and MODEL_BASE_URL is not configured.\n"
            "Provide the files via a mounted volume or specify a download URL."
        )

    # Case 3: Download model + preprocessor
    bundle_tag = f"model-v{MODEL_VERSION}"
    model_src = f"{DOWNLOAD_BASE}/{bundle_tag}/{MODEL_FILE}"
    preproc_src = f"{DOWNLOAD_BASE}/{bundle_tag}/preprocessor.joblib"

    fetch_if_missing(model_src, MODEL_FULL_PATH)
    fetch_if_missing(preproc_src, PREPROC_FULL_PATH)

    print("[model-service] Model files retrieved successfully.")


# ========== Initialization ========== #

prepare_model_files()
model = joblib.load(MODEL_FULL_PATH)

app = Flask(__name__)
swagger = Swagger(app)


@app.route('/predict', methods=['POST'])
def predict():
    """
    Predict whether an SMS is Spam.
    ---
    consumes:
      - application/json
    parameters:
        - name: input_data
          in: body
          description: message to be classified.
          required: True
          schema:
            type: object
            required: sms
            properties:
                sms:
                    type: string
                    example: This is an example of an SMS.
    responses:
      200:
        description: "The result of the classification: 'spam' or 'ham'."
    """
    start_time = time.time()
    
    input_data = request.get_json()
    sms = input_data.get('sms')
    processed_sms = prepare(sms)
    prediction = model.predict(processed_sms)[0]
    
    # Calculate inference duration
    duration = time.time() - start_time
    
    # Record metrics
    metrics.inc_predictions(prediction)  # 'spam' or 'ham'
    metrics.observe_inference_duration(duration)
    
    # For models that support predict_proba, we could get confidence
    # For now, we are setting a placeholder confidence (1.0 for deterministic prediction)
    metrics.set_confidence(1.0)
    
    res = {
        "result": prediction,
        "classifier": "decision tree",
        "sms": sms
    }
    print(res)
    return jsonify(res)


@app.route('/metrics')
def prometheus_metrics():
    """
    Expose Prometheus metrics endpoint.
    ---
    responses:
      200:
        description: Prometheus metrics in text format
    """
    return Response(metrics.format_metrics(), mimetype='text/plain; charset=utf-8')

if __name__ == '__main__':
    #clf = joblib.load('output/model.joblib')
    port = int(os.getenv("MODEL_SERVICE_PORT", "8081"))
    app.run(host="0.0.0.0", port=port, debug=True)
