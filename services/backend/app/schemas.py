"""Pydantic models for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TelemetryPoint(BaseModel):
    ts_source: datetime
    signal_id: str
    value: float | int | str | bool
    quality: str
    unit: str
    tags: dict[str, str] = Field(default_factory=dict)


class TelemetryWindow(BaseModel):
    asset_id: str
    site_id: str
    points: list[TelemetryPoint]


class SignalSummary(BaseModel):
    signal_id: str
    unit: str
    sampling_class: str


class AssetSummary(BaseModel):
    asset_id: str
    site_id: str
    area_id: str
    name: str
    signals: list[SignalSummary] = Field(default_factory=list)


class SiteSummary(BaseModel):
    site_id: str
    name: str
    status: str
    assets: list[AssetSummary] = Field(default_factory=list)


class AlarmRecord(BaseModel):
    alarm_id: str
    site_id: str
    asset_id: str
    severity: str
    message: str
    state: str
    raised_at: datetime
    acknowledged_at: datetime | None = None


class CommandCreate(BaseModel):
    site_id: str
    asset_id: str
    target_signal: str
    requested_value: Any
    requested_by: str
    priority: str = "medium"
    approved: bool = False
    approval_reference: str = ""
    expires_at: datetime


class CommandRecord(CommandCreate):
    command_id: str
    status: str
    issued_at: datetime


class ModelDeployRequest(BaseModel):
    model_id: str
    version: str
    checksum: str
    input_schema: str
    approval_state: str
    target_scope: str
    rollback_version: str = ""


class ModelVersionRecord(ModelDeployRequest):
    deployed_at: datetime
    deployed_by: str


class SiteHealthRecord(BaseModel):
    site_id: str
    connected: bool
    mqtt_connected: bool
    spool_depth: int
    kafka_lag: int
    updated_at: datetime


class IngestStatusRecord(BaseModel):
    total_sites: int
    degraded_sites: int
    total_spool_depth: int
    kafka_connected: bool
    updated_at: datetime

