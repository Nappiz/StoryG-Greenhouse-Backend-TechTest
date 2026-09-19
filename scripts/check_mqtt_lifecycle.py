"""Verify the FastAPI-managed MQTT client against the configured broker."""

import asyncio

from app.main import app
from mqtt.client import MQTTClient


async def check_lifecycle() -> int:
    mqtt_client: MQTTClient

    async with app.router.lifespan_context(app):
        mqtt_client = app.state.mqtt_client
        connected = await asyncio.to_thread(
            mqtt_client.wait_until_connected,
            5.0,
        )
        print(f"MQTT state during application lifecycle: {mqtt_client.status}")
        if not connected:
            return 1

    print(f"MQTT state after application shutdown: {mqtt_client.status}")
    return 0 if mqtt_client.status == "disconnected" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(check_lifecycle()))
