"""Persistence operations for sensor readings."""

from sqlalchemy.orm import Session

from database.models import SensorReading
from schemas.sensor_sch import SensorDataRequest


class SensorRepository:
    """Store sensor readings through a caller-owned SQLAlchemy session."""

    def create(
        self,
        session: Session,
        sensor_data: SensorDataRequest,
    ) -> SensorReading:
        reading = SensorReading(
            device_id=sensor_data.device_id,
            temperature=sensor_data.temperature,
            humidity=sensor_data.humidity,
            recorded_at=sensor_data.timestamp,
        )
        session.add(reading)
        session.flush()
        return reading
