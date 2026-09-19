"""Business flow for sensor ingestion."""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.exceptions import DatabaseOperationError
from repositories.sensor_repository import SensorRepository
from schemas.sensor_sch import SensorDataRequest, SensorDataResponse, StoredSensorData


logger = logging.getLogger(__name__)


class SensorService:
    """Coordinate sensor validation output and persistence."""

    def __init__(self, repository: SensorRepository) -> None:
        self._repository = repository

    def store_sensor_data(
        self,
        session: Session,
        sensor_data: SensorDataRequest,
    ) -> SensorDataResponse:
        try:
            reading = self._repository.create(session, sensor_data)
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            logger.exception("Failed to persist sensor reading")
            raise DatabaseOperationError() from exc

        return SensorDataResponse(data=StoredSensorData(id=reading.id))
