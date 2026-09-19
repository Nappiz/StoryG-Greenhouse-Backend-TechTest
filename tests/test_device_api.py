"""High-value tests for device command validation and MQTT publication."""

import asyncio
import json
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient, Response

from api.dependencies import get_mqtt_client
from app.main import app
from core.exceptions import MQTTUnavailableError


class RecordingMQTTClient:
    """Record publish arguments without using a network broker."""

    status = "connected"

    def __init__(self) -> None:
        self.published: list[tuple[str, str, int]] = []

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int,
    ) -> None:
        self.published.append((topic, payload, qos))


class UnavailableMQTTClient(RecordingMQTTClient):
    status = "disconnected"

    def publish(
        self,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        raise MQTTUnavailableError()


def post_device(payload: dict[str, object]) -> Response:
    async def send_request() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.post("/device-control", json=payload)

    return asyncio.run(send_request())


@pytest.fixture(autouse=True)
def clear_dependencies() -> None:
    yield
    app.dependency_overrides.clear()


def test_device_on_is_published_as_structured_qos_one_event() -> None:
    mqtt_client = RecordingMQTTClient()
    app.dependency_overrides[get_mqtt_client] = lambda: mqtt_client

    response = post_device({"device_id": "fan-001", "command": "ON"})

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Device control command published successfully",
        "data": {"device_id": "fan-001", "command": "ON"},
    }
    assert len(mqtt_client.published) == 1
    topic, raw_event, qos = mqtt_client.published[0]
    event = json.loads(raw_event)
    assert topic == "greenhouse/control/fan-001"
    assert qos == 1
    assert event["device_id"] == "fan-001"
    assert event["command"] == "ON"
    assert datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))


@pytest.mark.parametrize(
    "payload",
    [
        {"command": "ON"},
        {"device_id": "fan-001", "command": "START"},
    ],
)
def test_invalid_device_command_is_rejected(payload: dict[str, object]) -> None:
    mqtt_client = RecordingMQTTClient()
    app.dependency_overrides[get_mqtt_client] = lambda: mqtt_client

    response = post_device(payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert mqtt_client.published == []


def test_broker_unavailable_returns_safe_consistent_error() -> None:
    app.dependency_overrides[get_mqtt_client] = UnavailableMQTTClient

    response = post_device({"device_id": "fan-001", "command": "OFF"})

    assert response.status_code == 503
    assert response.json() == {
        "success": False,
        "error": {
            "code": "MQTT_UNAVAILABLE",
            "message": "MQTT broker is unavailable",
        },
    }
