"""Helpers for building and parsing MQTT topic names."""

from __future__ import annotations

from dataclasses import dataclass

from .constants import MQTT_CHANNELS


class TopicError(ValueError):
    """Raised when a topic is invalid."""


@dataclass(frozen=True)
class ParsedTopic:
    site_id: str
    area_id: str
    asset_id: str
    channel: str


def build_mqtt_topic(site_id: str, area_id: str, asset_id: str, channel: str) -> str:
    if channel not in MQTT_CHANNELS:
        raise TopicError(f"Unsupported channel: {channel}")
    for value_name, value in {
        "site_id": site_id,
        "area_id": area_id,
        "asset_id": asset_id,
    }.items():
        if not value or "/" in value:
            raise TopicError(f"{value_name} must be non-empty and slash-free")
    return f"site/{site_id}/area/{area_id}/asset/{asset_id}/{channel}"


def parse_mqtt_topic(topic: str) -> ParsedTopic:
    parts = topic.split("/")
    if len(parts) < 8:
        raise TopicError(f"Topic has too few segments: {topic}")
    if parts[0] != "site" or parts[2] != "area" or parts[4] != "asset":
        raise TopicError(f"Topic is not canonical: {topic}")
    channel = "/".join(parts[6:])
    if channel not in MQTT_CHANNELS:
        raise TopicError(f"Unsupported channel: {channel}")
    return ParsedTopic(
        site_id=parts[1],
        area_id=parts[3],
        asset_id=parts[5],
        channel=channel,
    )

