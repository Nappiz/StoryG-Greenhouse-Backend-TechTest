"""Long-lived MQTT client managed by the FastAPI application lifecycle."""

from __future__ import annotations

import logging
from threading import Event, Lock

import paho.mqtt.client as mqtt

from core.exceptions import MQTTUnavailableError

logger = logging.getLogger(__name__)


class MQTTClient:
    """Own a single Paho network loop and expose its connection state."""

    def __init__(self, host: str, port: int, keepalive: int = 60) -> None:
        self._host = host
        self._port = port
        self._keepalive = keepalive
        self._connected = Event()
        self._lifecycle_lock = Lock()
        self._started = False
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

    @property
    def is_connected(self) -> bool:
        """Return whether the broker has acknowledged the current connection."""
        return self._connected.is_set()

    @property
    def status(self) -> str:
        """Return the API-facing connection state."""
        return "connected" if self.is_connected else "disconnected"

    def start(self) -> None:
        """Start one asynchronous connection and Paho network loop."""
        with self._lifecycle_lock:
            if self._started:
                return
            self._client.connect_async(self._host, self._port, self._keepalive)
            self._client.loop_start()
            self._started = True

    def stop(self) -> None:
        """Disconnect cleanly and stop the network loop."""
        with self._lifecycle_lock:
            if not self._started:
                return
            if self.is_connected:
                self._client.disconnect()
            self._client.loop_stop()
            self._connected.clear()
            self._started = False

    def wait_until_connected(self, timeout: float = 5.0) -> bool:
        """Wait briefly for broker acknowledgement, primarily for diagnostics."""
        return self._connected.wait(timeout)

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int = 1,
        timeout: float = 5.0,
    ) -> None:
        """Publish and wait for broker acknowledgement at the requested QoS."""
        if not self.is_connected:
            raise MQTTUnavailableError()

        try:
            result = self._client.publish(
                topic,
                payload=payload,
                qos=qos,
                retain=False,
            )
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise MQTTUnavailableError()
            result.wait_for_publish(timeout=timeout)
            if not result.is_published():
                raise MQTTUnavailableError()
        except MQTTUnavailableError:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            logger.exception("MQTT publish failed for topic %s", topic)
            raise MQTTUnavailableError() from exc

    def _on_connect(
        self,
        _client: mqtt.Client,
        _userdata: object,
        _connect_flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        if reason_code == 0:
            self._connected.set()
            logger.info("Connected to MQTT broker at %s:%s", self._host, self._port)
            return

        self._connected.clear()
        logger.warning("MQTT connection rejected: %s", reason_code)

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: object,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        _properties: mqtt.Properties | None,
    ) -> None:
        self._connected.clear()
        if reason_code != 0:
            logger.warning("Unexpected MQTT disconnect: %s", reason_code)
