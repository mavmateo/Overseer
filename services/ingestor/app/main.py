"""Consume Kafka topics and persist them into TimescaleDB."""

from __future__ import annotations

import json
import logging
import signal
import time
from types import FrameType

from confluent_kafka import Consumer, KafkaException, Message

from iot_platform.contracts import ValidationError

from .config import get_settings
from .processors import build_operations
from .repository import DatabaseWriter

LOGGER = logging.getLogger("timescale-ingestor")


class IngestorService:
    def __init__(self) -> None:
        self.settings = get_settings()
        logging.basicConfig(
            level=getattr(logging, self.settings.log_level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(message)s",
        )
        self.writer = DatabaseWriter(self.settings)
        self.consumer = Consumer(
            {
                "bootstrap.servers": self.settings.kafka_bootstrap_servers,
                "group.id": self.settings.kafka_group_id,
                "auto.offset.reset": self.settings.kafka_auto_offset_reset,
                "enable.auto.commit": False,
            }
        )
        self.running = True

    def handle_shutdown(self, signum: int, _frame: FrameType | None) -> None:
        LOGGER.info("Received signal %s, stopping ingestor", signum)
        self.running = False

    def start(self) -> None:
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        self.consumer.subscribe(self.settings.topic_list)
        LOGGER.info("Subscribed to topics: %s", ", ".join(self.settings.topic_list))
        try:
            while self.running:
                message = self.consumer.poll(self.settings.poll_timeout_seconds)
                if message is None:
                    time.sleep(self.settings.idle_sleep_seconds)
                    continue
                self._handle_message(message)
        finally:
            self.consumer.close()
            self.writer.close()

    def _handle_message(self, message: Message) -> None:
        if message.error():
            LOGGER.warning("Kafka consumer error: %s", message.error())
            return
        topic = message.topic()
        try:
            payload = json.loads(message.value().decode("utf-8"))
            operations = build_operations(topic, payload)
            self.writer.apply(operations)
            self.consumer.commit(message=message, asynchronous=False)
            LOGGER.info("Ingested topic=%s partition=%s offset=%s", topic, message.partition(), message.offset())
        except (json.JSONDecodeError, ValidationError, KafkaException, KeyError, ValueError) as exc:
            # Commit poison messages after logging so one bad event does not stall the partition forever.
            LOGGER.error(
                "Rejected topic=%s partition=%s offset=%s error=%s payload=%s",
                topic,
                message.partition(),
                message.offset(),
                exc,
                message.value().decode("utf-8", errors="replace"),
            )
            self.consumer.commit(message=message, asynchronous=False)
        except Exception as exc:  # pragma: no cover - integration/runtime path
            LOGGER.exception(
                "Failed topic=%s partition=%s offset=%s due to transient error: %s",
                topic,
                message.partition(),
                message.offset(),
                exc,
            )


def main() -> None:
    IngestorService().start()


if __name__ == "__main__":
    main()

