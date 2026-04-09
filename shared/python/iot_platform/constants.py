"""Platform-wide constants for topics and defaults."""

MQTT_CHANNELS = {
    "telemetry",
    "event",
    "alarm",
    "state",
    "command/request",
    "command/ack",
}

KAFKA_TOPICS = {
    "telemetry": "raw.telemetry",
    "events": "raw.events",
    "alarms": "raw.alarms",
    "asset_state": "asset.state",
    "command_request": "command.request",
    "command_ack": "command.ack",
    "analytics_features": "analytics.features",
    "analytics_inference": "analytics.inference",
    "platform_audit": "platform.audit",
    "security_audit": "security.audit",
}

QUALITY_LEVELS = {"good", "uncertain", "bad"}
SAMPLING_CLASSES = {"subsecond", "1s", "5s", "15s", "60s", "300s"}
COMMAND_PRIORITIES = {"low", "medium", "high", "critical"}

