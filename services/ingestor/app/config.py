"""Configuration for the TimescaleDB ingestor."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="postgresql://postgres:postgres@timescaledb:5432/og_iot", alias="DATABASE_URL")
    kafka_bootstrap_servers: str = Field(default="kafka:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_group_id: str = Field(default="og-timescale-ingestor", alias="KAFKA_GROUP_ID")
    kafka_auto_offset_reset: str = Field(default="earliest", alias="KAFKA_AUTO_OFFSET_RESET")
    kafka_topics: str = Field(
        default="raw.telemetry,raw.alarms,raw.events,asset.state,command.request,command.ack,analytics.inference",
        alias="KAFKA_TOPICS",
    )
    poll_timeout_seconds: float = 1.0
    idle_sleep_seconds: float = 0.2
    log_level: str = Field(default="INFO", alias="INGESTOR_LOG_LEVEL")

    @property
    def topic_list(self) -> list[str]:
        return [topic.strip() for topic in self.kafka_topics.split(",") if topic.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

