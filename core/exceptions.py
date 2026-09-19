"""Application-level exceptions exposed through stable API error codes."""


class ApplicationError(RuntimeError):
    """Base class for expected failures safe to expose to API clients."""

    code = "APPLICATION_ERROR"
    default_message = "The request could not be completed"
    status_code = 500

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class DatabaseOperationError(ApplicationError):
    """Raised when a required database operation cannot be completed."""

    code = "DATABASE_UNAVAILABLE"
    default_message = "Database is unavailable"
    status_code = 503


class MQTTUnavailableError(ApplicationError):
    """Raised when a command cannot be acknowledged by the MQTT broker."""

    code = "MQTT_UNAVAILABLE"
    default_message = "MQTT broker is unavailable"
    status_code = 503
