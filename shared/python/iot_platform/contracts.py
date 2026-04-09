"""Canonical payload models with lightweight validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .constants import COMMAND_PRIORITIES, QUALITY_LEVELS, SAMPLING_CLASSES


class ValidationError(ValueError):
    """Raised when a contract payload is invalid."""


def _ensure(value: bool, message: str) -> None:
    if not value:
        raise ValidationError(message)


def _parse_ts(value: str) -> str:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"Invalid timestamp: {value}") from exc
    return value


@dataclass(frozen=True)
class TelemetryEnvelope:
    event_id: str
    site_id: str
    asset_id: str
    signal_id: str
    quality: str
    ts_source: str
    ts_ingest: str
    seq: int
    unit: str
    value: float | int | str | bool
    tags: dict[str, str] = field(default_factory=dict)
    trace_id: str = ""

    def __post_init__(self) -> None:
        _ensure(bool(self.event_id), "event_id is required")
        _ensure(bool(self.site_id), "site_id is required")
        _ensure(bool(self.asset_id), "asset_id is required")
        _ensure(bool(self.signal_id), "signal_id is required")
        _ensure(self.quality in QUALITY_LEVELS, "quality is invalid")
        _parse_ts(self.ts_source)
        _parse_ts(self.ts_ingest)
        _ensure(self.seq >= 0, "seq must be non-negative")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TelemetryEnvelope":
        return cls(
            event_id=str(payload["eventId"]),
            site_id=str(payload["siteId"]),
            asset_id=str(payload["assetId"]),
            signal_id=str(payload["signalId"]),
            quality=str(payload["quality"]),
            ts_source=str(payload["ts_source"]),
            ts_ingest=str(payload["ts_ingest"]),
            seq=int(payload["seq"]),
            unit=str(payload.get("unit", "")),
            value=payload["value"],
            tags=dict(payload.get("tags", {})),
            trace_id=str(payload.get("traceId", "")),
        )

    def dedupe_key(self) -> str:
        return f"{self.site_id}:{self.signal_id}:{self.ts_source}:{self.seq}"


@dataclass(frozen=True)
class CommandRequest:
    command_id: str
    site_id: str
    asset_id: str
    target_signal: str
    requested_value: str | float | int | bool
    requested_by: str
    priority: str
    approved: bool
    approval_reference: str
    expires_at: str

    def __post_init__(self) -> None:
        _ensure(bool(self.command_id), "command_id is required")
        _ensure(bool(self.site_id), "site_id is required")
        _ensure(bool(self.asset_id), "asset_id is required")
        _ensure(bool(self.target_signal), "target_signal is required")
        _ensure(bool(self.requested_by), "requested_by is required")
        _ensure(self.priority in COMMAND_PRIORITIES, "priority is invalid")
        _ensure(self.approved or not self.approval_reference, "approval_reference requires approval")
        _parse_ts(self.expires_at)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CommandRequest":
        return cls(
            command_id=str(payload["commandId"]),
            site_id=str(payload["siteId"]),
            asset_id=str(payload["assetId"]),
            target_signal=str(payload["targetSignal"]),
            requested_value=payload["requestedValue"],
            requested_by=str(payload["requestedBy"]),
            priority=str(payload.get("priority", "medium")),
            approved=bool(payload.get("approved", False)),
            approval_reference=str(payload.get("approvalReference", "")),
            expires_at=str(payload["expiresAt"]),
        )


@dataclass(frozen=True)
class DeviceRegistration:
    site_id: str
    asset_id: str
    device_id: str
    protocol: str
    signal_map: dict[str, str]
    units: dict[str, str]
    sampling_class: str
    thresholds: dict[str, float] = field(default_factory=dict)
    ownership_tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _ensure(bool(self.site_id), "site_id is required")
        _ensure(bool(self.asset_id), "asset_id is required")
        _ensure(bool(self.device_id), "device_id is required")
        _ensure(bool(self.protocol), "protocol is required")
        _ensure(bool(self.signal_map), "signal_map is required")
        _ensure(self.sampling_class in SAMPLING_CLASSES, "sampling_class is invalid")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DeviceRegistration":
        return cls(
            site_id=str(payload["siteId"]),
            asset_id=str(payload["assetId"]),
            device_id=str(payload["deviceId"]),
            protocol=str(payload["protocol"]),
            signal_map=dict(payload["signalMap"]),
            units=dict(payload["units"]),
            sampling_class=str(payload["samplingClass"]),
            thresholds=dict(payload.get("thresholds", {})),
            ownership_tags=dict(payload.get("ownershipTags", {})),
        )


@dataclass(frozen=True)
class ModelDeployment:
    model_id: str
    version: str
    checksum: str
    input_schema: str
    approval_state: str
    target_scope: str
    rollback_version: str = ""

    def __post_init__(self) -> None:
        _ensure(bool(self.model_id), "model_id is required")
        _ensure(bool(self.version), "version is required")
        _ensure(bool(self.checksum), "checksum is required")
        _ensure(bool(self.input_schema), "input_schema is required")
        _ensure(self.approval_state in {"draft", "approved", "rejected"}, "approval_state is invalid")
        _ensure(bool(self.target_scope), "target_scope is required")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ModelDeployment":
        return cls(
            model_id=str(payload["modelId"]),
            version=str(payload["version"]),
            checksum=str(payload["checksum"]),
            input_schema=str(payload["inputSchema"]),
            approval_state=str(payload["approvalState"]),
            target_scope=str(payload["targetScope"]),
            rollback_version=str(payload.get("rollbackVersion", "")),
        )

