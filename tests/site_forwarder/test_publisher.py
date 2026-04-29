import pathlib
import sys
import unittest


SITE_FORWARDER_ROOT = pathlib.Path(__file__).resolve().parents[2] / "services" / "site-forwarder"
if str(SITE_FORWARDER_ROOT) not in sys.path:
    sys.path.insert(0, str(SITE_FORWARDER_ROOT))

from app.buffer import BufferedRecord  # noqa: E402
from app.publisher import build_kafka_producer, publish_buffered_record, reset_kafka_producer  # noqa: E402


class FakeProducer:
    def __init__(self, flush_result: int = 0, delivery_error: str | None = None) -> None:
        self.flush_result = flush_result
        self.delivery_error = delivery_error
        self.produced: list[tuple[str, bytes, bytes]] = []
        self.flush_calls: list[float | None] = []
        self.poll_calls: list[float] = []
        self.purge_calls = 0

    def produce(self, topic: str, key: bytes, value: bytes, on_delivery) -> None:
        self.produced.append((topic, key, value))
        on_delivery(self.delivery_error, None)

    def flush(self, timeout: float | None = None) -> int:
        self.flush_calls.append(timeout)
        return self.flush_result

    def poll(self, timeout: float = 0.0) -> int:
        self.poll_calls.append(timeout)
        return 0

    def purge(self) -> None:
        self.purge_calls += 1


class PublisherTests(unittest.TestCase):
    def test_publish_buffered_record_raises_timeout_when_messages_remain_queued(self) -> None:
        producer = FakeProducer(flush_result=1)
        record = BufferedRecord(row_id=42, kafka_topic="raw.telemetry", key="site:signal", payload='{"value":1}')

        with self.assertRaisesRegex(
            TimeoutError,
            "1 Kafka message\\(s\\) remained undelivered after flush timeout",
        ):
            publish_buffered_record(producer, record, 5.0)

        self.assertEqual(producer.produced, [("raw.telemetry", b"site:signal", b'{"value":1}')])
        self.assertEqual(producer.flush_calls, [5.0])

    def test_publish_buffered_record_surfaces_delivery_error(self) -> None:
        producer = FakeProducer(delivery_error="broker unavailable")
        record = BufferedRecord(row_id=7, kafka_topic="raw.events", key="evt-7", payload='{"eventId":"evt-7"}')

        with self.assertRaisesRegex(RuntimeError, "broker unavailable"):
            publish_buffered_record(producer, record, 5.0)

        self.assertEqual(producer.flush_calls, [5.0])

    def test_reset_kafka_producer_purges_old_queue_and_builds_a_fresh_instance(self) -> None:
        old_producer = FakeProducer(flush_result=3)
        new_producer = FakeProducer()
        builder_configs: list[dict[str, object]] = []

        def builder(config: dict[str, object]) -> FakeProducer:
            builder_configs.append(config)
            return new_producer

        replacement = reset_kafka_producer(
            old_producer,
            "kafka:9092",
            producer_builder=builder,
        )

        self.assertIs(replacement, new_producer)
        self.assertEqual(old_producer.purge_calls, 1)
        self.assertEqual(old_producer.poll_calls, [0])
        self.assertEqual(
            builder_configs,
            [
                {
                    "bootstrap.servers": "kafka:9092",
                    "enable.idempotence": True,
                    "acks": "all",
                    "compression.type": "lz4",
                }
            ],
        )

    def test_build_kafka_producer_uses_override_builder(self) -> None:
        built: list[dict[str, object]] = []

        def builder(config: dict[str, object]) -> FakeProducer:
            built.append(config)
            return FakeProducer()

        producer = build_kafka_producer("kafka:9092", producer_builder=builder)

        self.assertIsInstance(producer, FakeProducer)
        self.assertEqual(built[0]["bootstrap.servers"], "kafka:9092")


if __name__ == "__main__":
    unittest.main()
