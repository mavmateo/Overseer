"""Kafka publishing helpers for the store-and-forward bridge."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from .buffer import BufferedRecord

try:
    from confluent_kafka import Producer as _ConfluentProducer
except ModuleNotFoundError:  # pragma: no cover - exercised in unit tests without optional deps
    _ConfluentProducer = None


class ProducerLike(Protocol):
    def produce(
        self,
        topic: str,
        key: bytes,
        value: bytes,
        on_delivery: Callable[[object, object], None],
    ) -> None: ...

    def flush(self, timeout: float | None = None) -> int: ...

    def poll(self, timeout: float = 0.0) -> int: ...

    def purge(self) -> None: ...


def _producer_config(bootstrap_servers: str) -> dict[str, Any]:
    return {
        "bootstrap.servers": bootstrap_servers,
        "enable.idempotence": True,
        "acks": "all",
        "compression.type": "lz4",
    }


def build_kafka_producer(
    bootstrap_servers: str,
    producer_builder: Callable[[dict[str, Any]], ProducerLike] | None = None,
) -> ProducerLike:
    builder = producer_builder
    if builder is None:
        if _ConfluentProducer is None:  # pragma: no cover - exercised in unit tests without optional deps
            raise RuntimeError("confluent-kafka is required to build the Kafka producer")
        builder = _ConfluentProducer
    return builder(_producer_config(bootstrap_servers))


def publish_buffered_record(
    producer: ProducerLike,
    record: BufferedRecord,
    flush_timeout_seconds: float,
) -> None:
    delivery_errors: list[str] = []

    def _delivery_report(error, _msg) -> None:
        if error is not None:
            delivery_errors.append(str(error))

    producer.produce(
        record.kafka_topic,
        key=record.key.encode("utf-8"),
        value=record.payload.encode("utf-8"),
        on_delivery=_delivery_report,
    )
    remaining = producer.flush(timeout=flush_timeout_seconds)
    if remaining > 0:
        raise TimeoutError(f"{remaining} Kafka message(s) remained undelivered after flush timeout")
    if delivery_errors:
        raise RuntimeError("; ".join(delivery_errors))


def reset_kafka_producer(
    producer: ProducerLike,
    bootstrap_servers: str,
    producer_builder: Callable[[dict[str, Any]], ProducerLike] | None = None,
) -> ProducerLike:
    try:
        producer.purge()
        producer.poll(0)
    except Exception:  # pragma: no cover - defensive cleanup path
        pass
    return build_kafka_producer(bootstrap_servers, producer_builder=producer_builder)
