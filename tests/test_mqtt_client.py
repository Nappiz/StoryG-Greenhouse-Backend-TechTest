"""Tests for MQTT lifecycle state tracking."""

from mqtt.client import MQTTClient


def test_mqtt_connection_state_follows_callbacks() -> None:
    client = MQTTClient("localhost", 1883)

    assert client.status == "disconnected"

    client._on_connect(None, None, None, 0, None)  # type: ignore[arg-type]
    assert client.is_connected is True
    assert client.status == "connected"

    client._on_disconnect(None, None, None, 1, None)  # type: ignore[arg-type]
    assert client.is_connected is False
    assert client.status == "disconnected"
