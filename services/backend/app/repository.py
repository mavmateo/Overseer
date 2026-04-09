"""Repository layer with an in-memory fallback and optional TimescaleDB reads."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from .config import Settings
from .schemas import (
    AlarmRecord,
    AssetSummary,
    CommandCreate,
    CommandRecord,
    IngestStatusRecord,
    ModelDeployRequest,
    ModelVersionRecord,
    SignalSummary,
    SiteHealthRecord,
    SiteSummary,
    TelemetryPoint,
    TelemetryWindow,
)


class Repository(Protocol):
    def get_site(self, site_id: str) -> SiteSummary | None: ...
    def get_asset(self, asset_id: str) -> AssetSummary | None: ...
    def get_telemetry(
        self,
        asset_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ) -> TelemetryWindow: ...
    def get_alarms(self, site_id: str | None = None, state: str | None = None) -> list[AlarmRecord]: ...
    def create_command(self, payload: CommandCreate) -> CommandRecord: ...
    def get_command(self, command_id: str) -> CommandRecord | None: ...
    def deploy_model(self, payload: ModelDeployRequest, deployed_by: str) -> ModelVersionRecord: ...
    def get_model_versions(self) -> list[ModelVersionRecord]: ...
    def get_site_health(self, site_id: str) -> SiteHealthRecord | None: ...
    def get_ingest_status(self) -> IngestStatusRecord: ...


class MemoryRepository:
    def __init__(self) -> None:
        now = datetime.now(UTC).replace(microsecond=0)
        self.assets = {
            "crusher-01": AssetSummary(
                asset_id="crusher-01",
                site_id="site-alpha",
                area_id="processing",
                name="Primary Crusher 01",
                signals=[
                    SignalSummary(signal_id="motor_current", unit="A", sampling_class="1s"),
                    SignalSummary(signal_id="bearing_temp", unit="C", sampling_class="5s"),
                    SignalSummary(signal_id="vibration_rms", unit="mm/s", sampling_class="1s"),
                ],
            ),
            "pump-07": AssetSummary(
                asset_id="pump-07",
                site_id="site-alpha",
                area_id="dewatering",
                name="Dewatering Pump 07",
                signals=[
                    SignalSummary(signal_id="discharge_pressure", unit="bar", sampling_class="1s"),
                    SignalSummary(signal_id="flow_rate", unit="m3/h", sampling_class="1s"),
                ],
            ),
        }
        self.sites = {
            "site-alpha": SiteSummary(
                site_id="site-alpha",
                name="Site Alpha",
                status="connected",
                assets=list(self.assets.values()),
            )
        }
        self.telemetry: dict[str, list[TelemetryPoint]] = {
            "crusher-01": [
                TelemetryPoint(
                    ts_source=now - timedelta(seconds=offset * 5),
                    signal_id="motor_current",
                    value=42.1 + offset,
                    quality="good",
                    unit="A",
                    tags={"area": "processing"},
                )
                for offset in range(10)
            ]
        }
        self.alarms = [
            AlarmRecord(
                alarm_id="alm-1001",
                site_id="site-alpha",
                asset_id="crusher-01",
                severity="medium",
                message="Bearing temperature high",
                state="open",
                raised_at=now - timedelta(minutes=12),
                acknowledged_at=None,
            )
        ]
        self.commands: dict[str, CommandRecord] = {}
        self.model_versions = [
            ModelVersionRecord(
                model_id="vibration-anomaly",
                version="2026.04.09",
                checksum="sha256:demo",
                input_schema="telemetry-envelope-v1",
                approval_state="approved",
                target_scope="site-alpha",
                rollback_version="2026.03.15",
                deployed_at=now,
                deployed_by="platform-admin",
            )
        ]

    def get_site(self, site_id: str) -> SiteSummary | None:
        return self.sites.get(site_id)

    def get_asset(self, asset_id: str) -> AssetSummary | None:
        return self.assets.get(asset_id)

    def get_telemetry(
        self,
        asset_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ) -> TelemetryWindow:
        asset = self.assets[asset_id]
        points = self.telemetry.get(asset_id, [])
        filtered = [
            point
            for point in points
            if (start is None or point.ts_source >= start) and (end is None or point.ts_source <= end)
        ]
        return TelemetryWindow(asset_id=asset_id, site_id=asset.site_id, points=filtered[:limit])

    def get_alarms(self, site_id: str | None = None, state: str | None = None) -> list[AlarmRecord]:
        alarms = self.alarms
        if site_id:
            alarms = [alarm for alarm in alarms if alarm.site_id == site_id]
        if state:
            alarms = [alarm for alarm in alarms if alarm.state == state]
        return alarms

    def create_command(self, payload: CommandCreate) -> CommandRecord:
        record = CommandRecord(
            command_id=f"cmd-{uuid4().hex[:12]}",
            status="approved" if payload.approved else "pending-approval",
            issued_at=datetime.now(UTC).replace(microsecond=0),
            **payload.model_dump(),
        )
        self.commands[record.command_id] = record
        return record

    def get_command(self, command_id: str) -> CommandRecord | None:
        return self.commands.get(command_id)

    def deploy_model(self, payload: ModelDeployRequest, deployed_by: str) -> ModelVersionRecord:
        record = ModelVersionRecord(
            **payload.model_dump(),
            deployed_at=datetime.now(UTC).replace(microsecond=0),
            deployed_by=deployed_by,
        )
        self.model_versions.insert(0, record)
        return record

    def get_model_versions(self) -> list[ModelVersionRecord]:
        return self.model_versions

    def get_site_health(self, site_id: str) -> SiteHealthRecord | None:
        if site_id not in self.sites:
            return None
        return SiteHealthRecord(
            site_id=site_id,
            connected=True,
            mqtt_connected=True,
            spool_depth=0,
            kafka_lag=0,
            updated_at=datetime.now(UTC).replace(microsecond=0),
        )

    def get_ingest_status(self) -> IngestStatusRecord:
        return IngestStatusRecord(
            total_sites=len(self.sites),
            degraded_sites=0,
            total_spool_depth=0,
            kafka_connected=True,
            updated_at=datetime.now(UTC).replace(microsecond=0),
        )


class TimescaleRepository:
    def __init__(self, settings: Settings) -> None:
        self._dsn = settings.database_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def get_site(self, site_id: str) -> SiteSummary | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT site_id, site_name AS name, status FROM site_health WHERE site_id = %s ORDER BY updated_at DESC LIMIT 1",
                (site_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return SiteSummary(site_id=row["site_id"], name=row["name"], status=row["status"], assets=[])

    def get_asset(self, asset_id: str) -> AssetSummary | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT asset_id, site_id, area_id, name
                FROM asset_registry
                WHERE asset_id = %s
                """,
                (asset_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                """
                SELECT signal_id, unit, sampling_class
                FROM signal_registry
                WHERE asset_id = %s
                ORDER BY signal_id
                """,
                (asset_id,),
            )
            signals = [SignalSummary(**signal) for signal in cur.fetchall()]
            return AssetSummary(signals=signals, **row)

    def get_telemetry(
        self,
        asset_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ) -> TelemetryWindow:
        asset = self.get_asset(asset_id)
        if asset is None:
            raise KeyError(asset_id)
        start = start or datetime.now(UTC) - timedelta(hours=1)
        end = end or datetime.now(UTC)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT ts_source, signal_id, value, quality, unit, tags
                FROM measurements
                WHERE asset_id = %s
                  AND ts_source BETWEEN %s AND %s
                ORDER BY ts_source DESC
                LIMIT %s
                """,
                (asset_id, start, end, limit),
            )
            points = [TelemetryPoint(**row) for row in cur.fetchall()]
            return TelemetryWindow(asset_id=asset_id, site_id=asset.site_id, points=points)

    def get_alarms(self, site_id: str | None = None, state: str | None = None) -> list[AlarmRecord]:
        clauses: list[str] = []
        params: list[str] = []
        if site_id:
            clauses.append("site_id = %s")
            params.append(site_id)
        if state:
            clauses.append("state = %s")
            params.append(state)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT alarm_id, site_id, asset_id, severity, message, state, raised_at, acknowledged_at
                FROM alarms
                {where}
                ORDER BY raised_at DESC
                LIMIT 200
                """,
                params,
            )
            return [AlarmRecord(**row) for row in cur.fetchall()]

    def create_command(self, payload: CommandCreate) -> CommandRecord:
        command_id = f"cmd-{uuid4().hex[:12]}"
        status = "approved" if payload.approved else "pending-approval"
        issued_at = datetime.now(UTC).replace(microsecond=0)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO command_log (
                    command_id, site_id, asset_id, target_signal, requested_value,
                    requested_by, priority, approved, approval_reference, expires_at,
                    status, issued_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    command_id,
                    payload.site_id,
                    payload.asset_id,
                    payload.target_signal,
                    str(payload.requested_value),
                    payload.requested_by,
                    payload.priority,
                    payload.approved,
                    payload.approval_reference,
                    payload.expires_at,
                    status,
                    issued_at,
                ),
            )
            conn.commit()
        return CommandRecord(command_id=command_id, status=status, issued_at=issued_at, **payload.model_dump())

    def get_command(self, command_id: str) -> CommandRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT command_id, site_id, asset_id, target_signal, requested_value,
                       requested_by, priority, approved, approval_reference, expires_at,
                       status, issued_at
                FROM command_log
                WHERE command_id = %s
                """,
                (command_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            row["requested_value"] = row.pop("requested_value")
            return CommandRecord(**row)

    def deploy_model(self, payload: ModelDeployRequest, deployed_by: str) -> ModelVersionRecord:
        deployed_at = datetime.now(UTC).replace(microsecond=0)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_registry (
                    model_id, version, checksum, input_schema,
                    approval_state, target_scope, rollback_version,
                    deployed_at, deployed_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payload.model_id,
                    payload.version,
                    payload.checksum,
                    payload.input_schema,
                    payload.approval_state,
                    payload.target_scope,
                    payload.rollback_version,
                    deployed_at,
                    deployed_by,
                ),
            )
            conn.commit()
        return ModelVersionRecord(**payload.model_dump(), deployed_at=deployed_at, deployed_by=deployed_by)

    def get_model_versions(self) -> list[ModelVersionRecord]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT model_id, version, checksum, input_schema, approval_state,
                       target_scope, rollback_version, deployed_at, deployed_by
                FROM model_registry
                ORDER BY deployed_at DESC
                """,
            )
            return [ModelVersionRecord(**row) for row in cur.fetchall()]

    def get_site_health(self, site_id: str) -> SiteHealthRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT site_id, connected, mqtt_connected, spool_depth, kafka_lag, updated_at
                FROM site_health
                WHERE site_id = %s
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (site_id,),
            )
            row = cur.fetchone()
            return SiteHealthRecord(**row) if row else None

    def get_ingest_status(self) -> IngestStatusRecord:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total_sites,
                       COUNT(*) FILTER (WHERE NOT connected OR spool_depth > 0) AS degraded_sites,
                       COALESCE(SUM(spool_depth), 0) AS total_spool_depth,
                       TRUE AS kafka_connected,
                       NOW() AT TIME ZONE 'UTC' AS updated_at
                FROM (
                    SELECT DISTINCT ON (site_id) site_id, connected, spool_depth
                    FROM site_health
                    ORDER BY site_id, updated_at DESC
                ) latest
                """,
            )
            row = cur.fetchone()
            return IngestStatusRecord(**row)


def create_repository(settings: Settings) -> Repository:
    if settings.database_url:
        return TimescaleRepository(settings)
    return MemoryRepository()


@lru_cache(maxsize=1)
def get_repository_instance() -> Repository:
    return create_repository(Settings())
