"""Train a simple TensorFlow autoencoder against synthetic vibration data."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import tensorflow as tf


def build_dataset() -> np.ndarray:
    x = np.linspace(0, 6 * np.pi, 2048)
    base = np.sin(x) + np.random.normal(0, 0.08, size=x.shape)
    windows = np.lib.stride_tricks.sliding_window_view(base, 32)
    return windows.astype("float32")


def main() -> None:
    dataset = build_dataset()
    train = dataset[:1500]
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(32,)),
            tf.keras.layers.Dense(16, activation="relu"),
            tf.keras.layers.Dense(8, activation="relu"),
            tf.keras.layers.Dense(16, activation="relu"),
            tf.keras.layers.Dense(32),
        ]
    )
    model.compile(optimizer="adam", loss="mse")
    model.fit(train, train, epochs=5, batch_size=64, verbose=2)

    output_dir = Path("artifacts/models/vibration-anomaly/2026.04.09")
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save(output_dir / "model.keras")
    manifest = {
        "modelId": "vibration-anomaly",
        "version": "2026.04.09",
        "checksum": "replace-during-ci-signing",
        "inputSchema": "telemetry-envelope-v1",
        "approvalState": "draft",
        "targetScope": "site-alpha",
        "rollbackVersion": "2026.03.15",
        "generatedAt": datetime.now(UTC).isoformat(),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

