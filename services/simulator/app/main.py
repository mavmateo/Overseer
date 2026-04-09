"""Industrial dummy sensor publisher."""

from __future__ import annotations

import json
import logging
import math
import os
import random
import time
from datetime import UTC, datetime
from itertools import count
from urllib.parse import urlparse
from uuid import uuid4

import paho.mqtt.client as mqtt

from iot_platform.topics import build_mqtt_topic

from .profiles import ASSET_PROFILES, AssetProfile, SignalProfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("simulator")

MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "mqtt://mosquitto:1883")
SITE_ID = os.getenv("SITE_ID", "site-alpha")
QUALITY = os.getenv("DEFAULT_SIGNAL_QUALITY", "good")


def _payload(asset: AssetProfile, signal: SignalProfile, sequence: int, step: int) -> dict:
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    value = signal.base_value + math.sin(step / 5.0) * signal.amplitude + random.uniform(-0.35, 0.35)
    return {
        "eventId": f"evt-{uuid4().hex[:16]}",
        "siteId": SITE_ID,
        "assetId": asset.asset_id,
        "signalId": signal.signal_id,
        "quality": QUALITY,
        "ts_source": now,
        "ts_ingest": now,
        "seq": sequence,
        "unit": signal.unit,
        "value": round(value, 3),
        "tags": {"area": asset.area_id, "equipmentClass": asset.equipment_class},
        "traceId": f"trace-{uuid4().hex[:12]}",
    }


def _alarm_payload(asset: AssetProfile, signal: SignalProfile, telemetry: dict) -> dict | None:
    threshold_breaches = {
        "bearing_temp": telemetry["value"] > 82,
        "vibration_rms": telemetry["value"] > 4.5,
        "h2s_ppm": telemetry["value"] > 7,
    }
    if not threshold_breaches.get(signal.signal_id):
        return None
    return {
        "eventId": f"alm-{uuid4().hex[:16]}",
        "siteId": SITE_ID,
        "assetId": asset.asset_id,
        "signalId": signal.signal_id,
        "quality": "bad",
        "ts_source": telemetry["ts_source"],
        "ts_ingest": telemetry["ts_ingest"],
        "seq": telemetry["seq"],
        "unit": telemetry["unit"],
        "value": telemetry["value"],
        "tags": {"severity": "high", "message": f"{signal.signal_id} threshold exceeded"},
        "traceId": telemetry["traceId"],
    }


def _connect_client() -> mqtt.Client:
    parsed = urlparse(MQTT_BROKER_URL)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="dummy-simulator")
    client.connect(parsed.hostname or "localhost", parsed.port or 1883, keepalive=30)
    client.loop_start()
    return client


def run() -> None:
    client = _connect_client()
    sequences = {
        (asset.asset_id, signal.signal_id): count(start=1)
        for asset in ASSET_PROFILES
        for signal in asset.signals
    }
    step = 0
    while True:
        step += 1
        for asset in ASSET_PROFILES:
            for signal in asset.signals:
                if step % signal.sampling_seconds != 0:
                    continue
                sequence = next(sequences[(asset.asset_id, signal.signal_id)])
                telemetry = _payload(asset, signal, sequence, step)
                telemetry_topic = build_mqtt_topic(SITE_ID, asset.area_id, asset.asset_id, "telemetry")
                client.publish(telemetry_topic, json.dumps(telemetry), qos=1)
                alarm = _alarm_payload(asset, signal, telemetry)
                if alarm:
                    alarm_topic = build_mqtt_topic(SITE_ID, asset.area_id, asset.asset_id, "alarm")
                    client.publish(alarm_topic, json.dumps(alarm), qos=1)
                    LOGGER.info("Published alarm for %s %s", asset.asset_id, signal.signal_id)
        time.sleep(1)


if __name__ == "__main__":
    run()
