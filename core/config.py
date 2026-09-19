"""Environment-backed application settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    database_url: str = Field(validation_alias="DATABASE_URL", min_length=1)
    database_connect_timeout_seconds: int = Field(
        validation_alias="DATABASE_CONNECT_TIMEOUT_SECONDS",
        ge=1,
        le=30,
    )
    mqtt_host: str = Field(validation_alias="MQTT_HOST", min_length=1)
    mqtt_port: int = Field(validation_alias="MQTT_PORT", ge=1, le=65535)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per application process."""
    return Settings()
