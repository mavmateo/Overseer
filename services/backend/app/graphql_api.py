"""GraphQL schema for frontend queries, mutations, and subscriptions."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import AsyncGenerator

import strawberry
from strawberry.fastapi import GraphQLRouter

from .config import Settings, get_settings
from .repository import Repository, get_repository_instance
from .schemas import (
    AlarmRecord,
    AssetSummary,
    CommandCreate,
    CommandRecord,
    ModelDeployRequest,
    ModelVersionRecord,
    SignalSummary,
    SiteHealthRecord,
    SiteSummary,
    TelemetryPoint,
    TelemetryWindow,
)


@strawberry.type
class SignalType:
    signal_id: str
    unit: str
    sampling_class: str


@strawberry.type
class AssetType:
    asset_id: str
    site_id: str
    area_id: str
    name: str
    signals: list[SignalType]


@strawberry.type
class SiteType:
    site_id: str
    name: str
    status: str
    assets: list[AssetType]


@strawberry.type
class TelemetryPointType:
    ts_source: datetime
    signal_id: str
    value: str
    quality: str
    unit: str
    tags: strawberry.scalars.JSON


@strawberry.type
class TelemetryWindowType:
    asset_id: str
    site_id: str
    points: list[TelemetryPointType]


@strawberry.type
class AlarmType:
    alarm_id: str
    site_id: str
    asset_id: str
    severity: str
    message: str
    state: str
    raised_at: datetime
    acknowledged_at: datetime | None


@strawberry.type
class CommandType:
    command_id: str
    site_id: str
    asset_id: str
    target_signal: str
    requested_value: str
    requested_by: str
    priority: str
    approved: bool
    approval_reference: str
    expires_at: datetime
    status: str
    issued_at: datetime


@strawberry.type
class ModelVersionType:
    model_id: str
    version: str
    checksum: str
    input_schema: str
    approval_state: str
    target_scope: str
    rollback_version: str
    deployed_at: datetime
    deployed_by: str


@strawberry.type
class SiteHealthType:
    site_id: str
    connected: bool
    mqtt_connected: bool
    spool_depth: int
    kafka_lag: int
    updated_at: datetime


@strawberry.input
class CommandInput:
    site_id: str
    asset_id: str
    target_signal: str
    requested_value: str
    requested_by: str
    priority: str = "medium"
    approved: bool = False
    approval_reference: str = ""
    expires_at: datetime


@strawberry.input
class ModelDeployInput:
    model_id: str
    version: str
    checksum: str
    input_schema: str
    approval_state: str
    target_scope: str
    rollback_version: str = ""
    deployed_by: str = "platform-admin"


def _signal_type(item: SignalSummary) -> SignalType:
    return SignalType(**item.model_dump())


def _asset_type(item: AssetSummary) -> AssetType:
    return AssetType(
        asset_id=item.asset_id,
        site_id=item.site_id,
        area_id=item.area_id,
        name=item.name,
        signals=[_signal_type(signal) for signal in item.signals],
    )


def _site_type(item: SiteSummary) -> SiteType:
    return SiteType(
        site_id=item.site_id,
        name=item.name,
        status=item.status,
        assets=[_asset_type(asset) for asset in item.assets],
    )


def _telemetry_point_type(item: TelemetryPoint) -> TelemetryPointType:
    return TelemetryPointType(
        ts_source=item.ts_source,
        signal_id=item.signal_id,
        value=str(item.value),
        quality=item.quality,
        unit=item.unit,
        tags=item.tags,
    )


def _telemetry_window_type(item: TelemetryWindow) -> TelemetryWindowType:
    return TelemetryWindowType(
        asset_id=item.asset_id,
        site_id=item.site_id,
        points=[_telemetry_point_type(point) for point in item.points],
    )


def _alarm_type(item: AlarmRecord) -> AlarmType:
    return AlarmType(**item.model_dump())


def _command_type(item: CommandRecord) -> CommandType:
    data = item.model_dump()
    data["requested_value"] = str(data["requested_value"])
    return CommandType(**data)


def _model_version_type(item: ModelVersionRecord) -> ModelVersionType:
    return ModelVersionType(**item.model_dump())


def _site_health_type(item: SiteHealthRecord) -> SiteHealthType:
    return SiteHealthType(**item.model_dump())


def _repo(info: strawberry.Info) -> Repository:
    return info.context["repo"]


@strawberry.type
class Query:
    @strawberry.field
    def site(self, info: strawberry.Info, site_id: str) -> SiteType | None:
        site = _repo(info).get_site(site_id)
        return _site_type(site) if site else None

    @strawberry.field
    def asset(self, info: strawberry.Info, asset_id: str) -> AssetType | None:
        asset = _repo(info).get_asset(asset_id)
        return _asset_type(asset) if asset else None

    @strawberry.field
    def telemetry_window(
        self,
        info: strawberry.Info,
        asset_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 500,
    ) -> TelemetryWindowType:
        return _telemetry_window_type(_repo(info).get_telemetry(asset_id, start=start, end=end, limit=limit))

    @strawberry.field
    def alarms(self, info: strawberry.Info, site_id: str | None = None, state: str | None = None) -> list[AlarmType]:
        return [_alarm_type(alarm) for alarm in _repo(info).get_alarms(site_id=site_id, state=state)]

    @strawberry.field
    def model_versions(self, info: strawberry.Info) -> list[ModelVersionType]:
        return [_model_version_type(item) for item in _repo(info).get_model_versions()]

    @strawberry.field
    def site_health(self, info: strawberry.Info, site_id: str) -> SiteHealthType | None:
        health = _repo(info).get_site_health(site_id)
        return _site_health_type(health) if health else None


@strawberry.type
class Mutation:
    @strawberry.mutation
    def request_command(self, info: strawberry.Info, input: CommandInput) -> CommandType:
        record = _repo(info).create_command(CommandCreate(**input.__dict__))
        return _command_type(record)

    @strawberry.mutation
    def ack_command_override(self, info: strawberry.Info, command_id: str, status: str) -> CommandType | None:
        command = _repo(info).get_command(command_id)
        if command is None:
            return None
        updated = command.model_copy(update={"status": status})
        return _command_type(updated)

    @strawberry.mutation
    def deploy_model(self, info: strawberry.Info, input: ModelDeployInput) -> ModelVersionType:
        deployed = _repo(info).deploy_model(
            ModelDeployRequest(
                model_id=input.model_id,
                version=input.version,
                checksum=input.checksum,
                input_schema=input.input_schema,
                approval_state=input.approval_state,
                target_scope=input.target_scope,
                rollback_version=input.rollback_version,
            ),
            deployed_by=input.deployed_by,
        )
        return _model_version_type(deployed)


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def live_telemetry(self, info: strawberry.Info, asset_id: str) -> AsyncGenerator[TelemetryPointType, None]:
        repo = _repo(info)
        settings: Settings = info.context["settings"]
        while True:
            window = repo.get_telemetry(asset_id, start=datetime.now(UTC) - timedelta(minutes=10), limit=1)
            if window.points:
                yield _telemetry_point_type(window.points[0])
            await asyncio.sleep(settings.subscription_poll_seconds)

    @strawberry.subscription
    async def live_alarms(self, info: strawberry.Info, site_id: str) -> AsyncGenerator[AlarmType, None]:
        repo = _repo(info)
        settings: Settings = info.context["settings"]
        while True:
            alarms = repo.get_alarms(site_id=site_id, state="open")
            for alarm in alarms[:1]:
                yield _alarm_type(alarm)
            await asyncio.sleep(settings.subscription_poll_seconds)

    @strawberry.subscription
    async def command_status(self, info: strawberry.Info, command_id: str) -> AsyncGenerator[CommandType, None]:
        repo = _repo(info)
        settings: Settings = info.context["settings"]
        while True:
            command = repo.get_command(command_id)
            if command:
                yield _command_type(command)
            await asyncio.sleep(settings.subscription_poll_seconds)

    @strawberry.subscription
    async def site_connectivity(self, info: strawberry.Info, site_id: str) -> AsyncGenerator[SiteHealthType, None]:
        repo = _repo(info)
        settings: Settings = info.context["settings"]
        while True:
            health = repo.get_site_health(site_id)
            if health:
                yield _site_health_type(health)
            await asyncio.sleep(settings.subscription_poll_seconds)


def build_graphql_router() -> GraphQLRouter:
    settings = get_settings()
    repository = get_repository_instance()
    schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)

    async def get_context() -> dict[str, object]:
        return {"repo": repository, "settings": settings}

    return GraphQLRouter(schema, context_getter=get_context)
