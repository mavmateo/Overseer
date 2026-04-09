"""Runtime configuration for the FastAPI application."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="og-iot-backend", alias="PLATFORM_NAME")
    deployment_mode: str = Field(default="dev", alias="DEPLOYMENT_MODE")
    database_url: str = Field(default="", alias="DATABASE_URL")
    kafka_bootstrap_servers: str = Field(default="", alias="KAFKA_BOOTSTRAP_SERVERS")
    mqtt_broker_url: str = Field(default="", alias="MQTT_BROKER_URL")
    graphql_path: str = "/graphql"
    api_port: int = Field(default=8000, alias="API_PORT")
    subscription_poll_seconds: int = 5
    command_timeout_seconds: int = 90


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

