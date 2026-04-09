"""Run TensorFlow inference against telemetry envelopes from stdin."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf


def score_lines(model_path: str) -> None:
    model = tf.keras.models.load_model(model_path)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        window = np.array(payload["window"], dtype="float32").reshape(1, -1)
        reconstruction = model.predict(window, verbose=0)
        error = float(np.mean(np.square(window - reconstruction)))
        result = {
            "modelId": payload.get("modelId", "vibration-anomaly"),
            "assetId": payload["assetId"],
            "signalId": payload["signalId"],
            "score": error,
            "threshold": payload.get("threshold", 0.15),
            "anomalous": error > payload.get("threshold", 0.15),
        }
        print(json.dumps(result))


if __name__ == "__main__":
    score_lines(sys.argv[1] if len(sys.argv) > 1 else "artifacts/models/vibration-anomaly/2026.04.09/model.keras")

