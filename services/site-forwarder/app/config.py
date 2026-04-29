"""Configuration for the edge site forwarder."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mqtt_broker_url: str = Field(default="mqtt://mosquitto:1883", alias="MQTT_BROKER_URL")
    mqtt_username: str = Field(default="", alias="MQTT_USERNAME")
    mqtt_password: str = Field(default="", alias="MQTT_PASSWORD")
    mqtt_topic_filter: str = "site/+/area/+/asset/+/#"
    kafka_bootstrap_servers: str = Field(default="kafka:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_flush_timeout_seconds: float = Field(default=5.0, alias="KAFKA_FLUSH_TIMEOUT_SECONDS")
    spool_path: str = Field(default="/data/site-forwarder/buffer.db", alias="STORE_BUFFER_PATH")
    flush_interval_seconds: int = 3
    flush_batch_size: int = 250
    site_id: str = Field(default="", alias="SITE_ID")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
