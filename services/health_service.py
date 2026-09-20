"""Live dependency health evaluation."""

import logging
from collections.abc import Callable

from sqlalchemy.exc import SQLAlchemyError

from mqtt.client import MQTTClient
from schemas.health_sch import HealthResponse, ServiceStatuses

logger = logging.getLogger(__name__)


class HealthService:
    """Combine a live database query with current MQTT connection state."""

    def __init__(
        self,
        database_check: Callable[[], None],
        mqtt_client: MQTTClient,
    ) -> None:
        self._database_check = database_check
        self._mqtt_client = mqtt_client

    def get_status(self) -> HealthResponse:
        database_status = "connected"
        try:
            self._database_check()
        except SQLAlchemyError:
            logger.exception("Database health check failed")
            database_status = "disconnected"

        mqtt_status = self._mqtt_client.status
        overall_status = (
            "healthy"
            if database_status == "connected" and mqtt_status == "connected"
            else "degraded"
        )
        return HealthResponse(
            status=overall_status,
            services=ServiceStatuses(
                database=database_status,
                mqtt=mqtt_status,
            ),
        )
