"""MQTT-to-Kafka store-and-forward service."""

from __future__ import annotations

import json
import logging
import threading
import time
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from iot_platform.constants import KAFKA_TOPICS
from iot_platform.contracts import CommandRequest, TelemetryEnvelope, ValidationError
from iot_platform.topics import ParsedTopic, TopicError, parse_mqtt_topic

from .buffer import SpoolBuffer
from .config import get_settings
from .publisher import build_kafka_producer, publish_buffered_record, reset_kafka_producer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("site-forwarder")


def _kafka_topic_for(channel: str) -> str:
    mapping = {
        "telemetry": KAFKA_TOPICS["telemetry"],
        "event": KAFKA_TOPICS["events"],
        "alarm": KAFKA_TOPICS["alarms"],
        "state": KAFKA_TOPICS["asset_state"],
        "command/request": KAFKA_TOPICS["command_request"],
        "command/ack": KAFKA_TOPICS["command_ack"],
    }
    return mapping[channel]


def _message_key(topic: ParsedTopic, payload: dict) -> str:
    if "eventId" in payload:
        return str(payload["eventId"])
    if topic.channel == "telemetry":
        envelope = TelemetryEnvelope.from_dict(payload)
        return envelope.dedupe_key()
    if topic.channel == "command/request":
        command = CommandRequest.from_dict(payload)
        return command.command_id
    return f"{topic.site_id}:{topic.asset_id}:{payload.get('signalId', topic.channel)}:{payload.get('ts_source', payload.get('timestamp', 'na'))}"


class Forwarder:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.buffer = SpoolBuffer(self.settings.spool_path)
        self.mqtt_client = self._build_mqtt_client()
        self.kafka_producer = build_kafka_producer(self.settings.kafka_bootstrap_servers)
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)

    def _build_mqtt_client(self) -> mqtt.Client:
        parsed = urlparse(self.settings.mqtt_broker_url)
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"forwarder-{self.settings.site_id or 'site'}")
        if self.settings.mqtt_username:
            client.username_pw_set(self.settings.mqtt_username, self.settings.mqtt_password)
        client.user_data_set({"host": parsed.hostname or "localhost", "port": parsed.port or 1883})
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        return client

    def on_connect(self, client: mqtt.Client, _userdata, _flags, reason_code, _properties) -> None:
        LOGGER.info("Connected to MQTT broker with reason code %s", reason_code)
        client.subscribe(self.settings.mqtt_topic_filter, qos=1)

    def on_message(self, _client: mqtt.Client, _userdata, message: mqtt.MQTTMessage) -> None:
        try:
            topic = parse_mqtt_topic(message.topic)
            payload = json.loads(message.payload.decode("utf-8"))
            message_key = _message_key(topic, payload)
            kafka_topic = _kafka_topic_for(topic.channel)
            self.buffer.enqueue(kafka_topic, message_key, json.dumps(payload, separators=(",", ":")))
            LOGGER.info("Buffered %s message for %s", topic.channel, kafka_topic)
        except (json.JSONDecodeError, TopicError, ValidationError) as exc:
            LOGGER.error("Rejected message on topic %s: %s", message.topic, exc)

    def _flush_loop(self) -> None:
        while True:
            pending = self.buffer.pending(self.settings.flush_batch_size)
            if not pending:
                time.sleep(self.settings.flush_interval_seconds)
                continue
            for record in pending:
                try:
                    publish_buffered_record(
                        self.kafka_producer,
                        record,
                        self.settings.kafka_flush_timeout_seconds,
                    )
                    self.buffer.mark_sent(record.row_id)
                except Exception as exc:  # pragma: no cover - network-dependent
                    self.kafka_producer = reset_kafka_producer(
                        self.kafka_producer,
                        self.settings.kafka_bootstrap_servers,
                    )
                    self.buffer.mark_failed(record.row_id, str(exc))
                    LOGGER.warning("Kafka publish failed for row %s: %s", record.row_id, exc)
                    break

    def run(self) -> None:
        mqtt_target = self.mqtt_client.user_data_get()
        self._flush_thread.start()
        self.mqtt_client.connect(mqtt_target["host"], mqtt_target["port"], keepalive=30)
        self.mqtt_client.loop_forever()


def main() -> None:
    Forwarder().run()


if __name__ == "__main__":
    main()
