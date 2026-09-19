"""SQLAlchemy engine, session factory, and health check helpers."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Create one connection-pooled engine for the application process."""
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": settings.database_connect_timeout_seconds,
        },
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Create one session factory bound to the application engine."""
    return sessionmaker(
        bind=get_engine(),
        class_=Session,
        expire_on_commit=False,
    )


def get_db_session() -> Generator[Session, None, None]:
    """Provide a transaction-capable session to a FastAPI request."""
    with get_session_factory()() as session:
        yield session


def check_database_connection() -> None:
    """Raise an SQLAlchemy error unless PostgreSQL answers a trivial query."""
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
