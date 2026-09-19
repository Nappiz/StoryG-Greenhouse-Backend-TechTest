"""Business flow for greenhouse device control."""

import json
from collections.abc import Callable
from datetime import datetime, timezone

from mqtt.client import MQTTClient
from schemas.device_sch import (
    DeviceControlRequest,
    DeviceControlResponse,
    PublishedDeviceCommand,
)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


class DeviceService:
    """Build and publish structured device-control events."""

    def __init__(
        self,
        mqtt_client: MQTTClient,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._mqtt_client = mqtt_client
        self._clock = clock

    def send_command(
        self,
        command: DeviceControlRequest,
    ) -> DeviceControlResponse:
        topic = f"greenhouse/control/{command.device_id}"
        timestamp = self._clock().astimezone(timezone.utc)
        event = {
            "device_id": command.device_id,
            "command": command.command,
            "timestamp": timestamp.isoformat(timespec="seconds").replace(
                "+00:00",
                "Z",
            ),
        }
        self._mqtt_client.publish(
            topic,
            json.dumps(event, separators=(",", ":")),
            qos=1,
        )

        return DeviceControlResponse(
            data=PublishedDeviceCommand(
                device_id=command.device_id,
                command=command.command,
            )
        )
