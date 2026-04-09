"""Topic-to-table transformations for Kafka payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from iot_platform.contracts import CommandRequest, TelemetryEnvelope, ValidationError


def _parse_timestamp(raw: str | None, *, default_now: bool = False) -> datetime:
    if raw:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)
    if default_now:
        return datetime.now(UTC)
    raise ValidationError("timestamp is required")


def _numeric_value(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise ValidationError(f"Telemetry value is not numeric: {value}") from exc
    raise ValidationError(f"Unsupported telemetry value type: {type(value)!r}")


@dataclass(frozen=True)
class DbOperation:
    sql: str
    params: tuple[Any, ...]


def build_operations(topic: str, payload: dict[str, Any]) -> list[DbOperation]:
    handlers = {
        "raw.telemetry": _measurement_operations,
        "raw.alarms": _alarm_operations,
        "raw.events": _event_operations,
        "asset.state": _asset_state_operations,
        "command.request": _command_request_operations,
        "command.ack": _command_ack_operations,
        "analytics.inference": _model_score_operations,
    }
    handler = handlers.get(topic)
    if handler is None:
        raise ValidationError(f"No processor configured for topic: {topic}")
    return handler(payload)


def _measurement_operations(payload: dict[str, Any]) -> list[DbOperation]:
    telemetry = TelemetryEnvelope.from_dict(payload)
    return [
        DbOperation(
            sql="""
                INSERT INTO measurements (
                    ts_source, ts_ingest, event_id, site_id, asset_id,
                    signal_id, seq, quality, unit, value, tags, trace_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (ts_source, asset_id, signal_id, seq) DO UPDATE
                SET ts_ingest = EXCLUDED.ts_ingest,
                    quality = EXCLUDED.quality,
                    unit = EXCLUDED.unit,
                    value = EXCLUDED.value,
                    tags = EXCLUDED.tags,
                    trace_id = EXCLUDED.trace_id
            """,
            params=(
                _parse_timestamp(telemetry.ts_source),
                _parse_timestamp(telemetry.ts_ingest),
                telemetry.event_id,
                telemetry.site_id,
                telemetry.asset_id,
                telemetry.signal_id,
                telemetry.seq,
                telemetry.quality,
                telemetry.unit,
                _numeric_value(telemetry.value),
                _to_json(telemetry.tags),
                telemetry.trace_id,
            ),
        )
    ]


def _alarm_operations(payload: dict[str, Any]) -> list[DbOperation]:
    telemetry = TelemetryEnvelope.from_dict(payload)
    severity = str(payload.get("tags", {}).get("severity", "medium"))
    message = str(payload.get("tags", {}).get("message", f"{telemetry.signal_id} threshold exceeded"))
    return [
        DbOperation(
            sql="""
                INSERT INTO alarms (
                    raised_at, alarm_id, site_id, asset_id, severity,
                    message, state, acknowledged_at, payload
                ) VALUES (%s, %s, %s, %s, %s, %s, 'open', NULL, %s::jsonb)
                ON CONFLICT (raised_at, alarm_id) DO UPDATE
                SET severity = EXCLUDED.severity,
                    message = EXCLUDED.message,
                    payload = EXCLUDED.payload
            """,
            params=(
                _parse_timestamp(telemetry.ts_source),
                telemetry.event_id,
                telemetry.site_id,
                telemetry.asset_id,
                severity,
                message,
                _to_json(payload),
            ),
        )
    ]


def _event_operations(payload: dict[str, Any]) -> list[DbOperation]:
    event_id = str(payload.get("eventId", payload.get("id", f"evt-{datetime.now(UTC).timestamp()}")))
    site_id = str(payload.get("siteId", "unknown-site"))
    asset_id = str(payload.get("assetId", "unknown-asset"))
    event_type = str(payload.get("eventType", payload.get("type", "generic-event")))
    ts_source = _parse_timestamp(payload.get("ts_source") or payload.get("timestamp"), default_now=True)
    return [
        DbOperation(
            sql="""
                INSERT INTO events (ts_source, event_id, site_id, asset_id, event_type, payload)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (ts_source, event_id) DO UPDATE
                SET payload = EXCLUDED.payload,
                    event_type = EXCLUDED.event_type
            """,
            params=(ts_source, event_id, site_id, asset_id, event_type, _to_json(payload)),
        )
    ]


def _asset_state_operations(payload: dict[str, Any]) -> list[DbOperation]:
    ts_source = _parse_timestamp(payload.get("ts_source") or payload.get("timestamp"), default_now=True)
    site_id = str(payload["siteId"])
    asset_id = str(payload["assetId"])
    state = str(payload.get("state", payload.get("value", "unknown")))
    return [
        DbOperation(
            sql="""
                INSERT INTO asset_state (ts_source, site_id, asset_id, state, payload)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (ts_source, asset_id) DO UPDATE
                SET state = EXCLUDED.state,
                    payload = EXCLUDED.payload
            """,
            params=(ts_source, site_id, asset_id, state, _to_json(payload)),
        )
    ]


def _command_request_operations(payload: dict[str, Any]) -> list[DbOperation]:
    command = CommandRequest.from_dict(payload)
    issued_at = _parse_timestamp(payload.get("issuedAt"), default_now=True)
    status = "approved" if command.approved else "pending-approval"
    return [
        DbOperation(
            sql="""
                INSERT INTO command_log (
                    issued_at, command_id, site_id, asset_id, target_signal,
                    requested_value, requested_by, priority, approved,
                    approval_reference, expires_at, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (issued_at, command_id) DO UPDATE
                SET requested_value = EXCLUDED.requested_value,
                    approved = EXCLUDED.approved,
                    approval_reference = EXCLUDED.approval_reference,
                    status = EXCLUDED.status
            """,
            params=(
                issued_at,
                command.command_id,
                command.site_id,
                command.asset_id,
                command.target_signal,
                str(command.requested_value),
                command.requested_by,
                command.priority,
                command.approved,
                command.approval_reference,
                _parse_timestamp(command.expires_at),
                status,
            ),
        )
    ]


def _command_ack_operations(payload: dict[str, Any]) -> list[DbOperation]:
    command_id = str(payload["commandId"])
    issued_at = _parse_timestamp(payload.get("issuedAt"), default_now=True)
    status = str(payload.get("status", "acknowledged"))
    return [
        DbOperation(
            sql="""
                INSERT INTO command_log (
                    issued_at, command_id, site_id, asset_id, target_signal,
                    requested_value, requested_by, priority, approved,
                    approval_reference, expires_at, status
                ) VALUES (%s, %s, %s, %s, '', '', 'system', 'medium', TRUE, '', %s, %s)
                ON CONFLICT (issued_at, command_id) DO UPDATE
                SET status = EXCLUDED.status
            """,
            params=(
                issued_at,
                command_id,
                str(payload.get("siteId", "unknown-site")),
                str(payload.get("assetId", "unknown-asset")),
                _parse_timestamp(payload.get("expiresAt"), default_now=True),
                status,
            ),
        )
    ]


def _model_score_operations(payload: dict[str, Any]) -> list[DbOperation]:
    ts_source = _parse_timestamp(payload.get("ts_source") or payload.get("timestamp"), default_now=True)
    score = payload.get("score")
    if score is None:
        raise ValidationError("score is required for analytics.inference")
    return [
        DbOperation(
            sql="""
                INSERT INTO model_scores (
                    ts_source, model_id, site_id, asset_id, signal_id, score, anomalous, payload
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (ts_source, model_id, asset_id, signal_id) DO UPDATE
                SET score = EXCLUDED.score,
                    anomalous = EXCLUDED.anomalous,
                    payload = EXCLUDED.payload
            """,
            params=(
                ts_source,
                str(payload.get("modelId", "unknown-model")),
                str(payload["siteId"]),
                str(payload["assetId"]),
                str(payload["signalId"]),
                float(score),
                bool(payload.get("anomalous", False)),
                _to_json(payload),
            ),
        )
    ]


def _to_json(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, separators=(",", ":"), sort_keys=True)

