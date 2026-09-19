"""Tests for environment-backed application configuration."""

from core.config import Settings


def test_settings_are_loaded_from_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:password@postgres:5432/greenhouse",
    )
    monkeypatch.setenv("DATABASE_CONNECT_TIMEOUT_SECONDS", "3")
    monkeypatch.setenv("MQTT_HOST", "mosquitto")
    monkeypatch.setenv("MQTT_PORT", "1883")

    settings = Settings(_env_file=None)

    assert settings.database_url.endswith("/greenhouse")
    assert settings.database_connect_timeout_seconds == 3
    assert settings.mqtt_host == "mosquitto"
    assert settings.mqtt_port == 1883
