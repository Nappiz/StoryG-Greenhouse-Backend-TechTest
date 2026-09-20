"""Sensor ingestion API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database.connection import get_db_session
from repositories.sensor_repository import SensorRepository
from schemas.error_sch import ErrorResponse
from schemas.sensor_sch import SensorDataRequest, SensorDataResponse
from services.sensor_service import SensorService

router = APIRouter(tags=["Sensors"])


def get_sensor_service() -> SensorService:
    """Build the sensor service and its repository dependency."""
    return SensorService(SensorRepository())


@router.post(
    "/sensor-data",
    response_model=SensorDataResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def store_sensor_data(
    payload: SensorDataRequest,
    session: Annotated[Session, Depends(get_db_session)],
    service: Annotated[SensorService, Depends(get_sensor_service)],
) -> SensorDataResponse:
    """Validate and persist one sensor reading."""
    return service.store_sensor_data(session, payload)
