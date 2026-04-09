"""Shared contracts and topic helpers for the industrial IoT platform."""

from .constants import KAFKA_TOPICS, MQTT_CHANNELS
from .contracts import (
    CommandRequest,
    DeviceRegistration,
    ModelDeployment,
    TelemetryEnvelope,
    ValidationError,
)
from .topics import build_mqtt_topic, parse_mqtt_topic

__all__ = [
    "KAFKA_TOPICS",
    "MQTT_CHANNELS",
    "CommandRequest",
    "DeviceRegistration",
    "ModelDeployment",
    "TelemetryEnvelope",
    "ValidationError",
    "build_mqtt_topic",
    "parse_mqtt_topic",
]

