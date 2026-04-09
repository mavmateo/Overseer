"""FastAPI entrypoint for the central application layer."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .graphql_api import build_graphql_router
from .repository import Repository, get_repository_instance
from .schemas import CommandCreate, ModelDeployRequest

app = FastAPI(title="Open Industrial IoT Platform", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(build_graphql_router(), prefix=get_settings().graphql_path)


def get_repository(settings: Settings = Depends(get_settings)) -> Repository:
    return get_repository_instance()


@app.get("/healthz")
def healthz(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "mode": settings.deployment_mode}


@app.get("/sites/{site_id}")
def get_site(site_id: str, repository: Repository = Depends(get_repository)):
    site = repository.get_site(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="site not found")
    return site


@app.get("/assets/{asset_id}")
def get_asset(asset_id: str, repository: Repository = Depends(get_repository)):
    asset = repository.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return asset


@app.get("/assets/{asset_id}/telemetry")
def get_asset_telemetry(
    asset_id: str,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    limit: int = Query(default=500, le=5000),
    repository: Repository = Depends(get_repository),
):
    try:
        return repository.get_telemetry(asset_id, start=start, end=end, limit=limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="asset not found") from exc


@app.get("/alarms")
def get_alarms(
    site_id: str | None = Query(default=None),
    state: str | None = Query(default=None),
    repository: Repository = Depends(get_repository),
):
    return repository.get_alarms(site_id=site_id, state=state)


@app.post("/commands", status_code=202)
def create_command(payload: CommandCreate, repository: Repository = Depends(get_repository)):
    return repository.create_command(payload)


@app.get("/commands/{command_id}")
def get_command(command_id: str, repository: Repository = Depends(get_repository)):
    command = repository.get_command(command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="command not found")
    return command


@app.post("/models/deploy", status_code=202)
def deploy_model(
    payload: ModelDeployRequest,
    deployed_by: str = Query(default="platform-admin"),
    repository: Repository = Depends(get_repository),
):
    return repository.deploy_model(payload, deployed_by=deployed_by)


@app.get("/models")
def list_models(repository: Repository = Depends(get_repository)):
    return repository.get_model_versions()


@app.get("/sites/{site_id}/health")
def get_site_health(site_id: str, repository: Repository = Depends(get_repository)):
    health = repository.get_site_health(site_id)
    if health is None:
        raise HTTPException(status_code=404, detail="site not found")
    return health


@app.get("/platform/ingest-status")
def get_ingest_status(repository: Repository = Depends(get_repository)):
    return repository.get_ingest_status()


@app.get("/platform/info")
def platform_info(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "name": settings.app_name,
        "deploymentMode": settings.deployment_mode,
        "generatedAt": datetime.now(UTC).isoformat(),
    }
