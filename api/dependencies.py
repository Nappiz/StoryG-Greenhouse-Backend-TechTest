"""Shared FastAPI dependencies."""

from fastapi import Request

from mqtt.client import MQTTClient


def get_mqtt_client(request: Request) -> MQTTClient:
    """Return the lifecycle-managed MQTT client."""
    return request.app.state.mqtt_client
