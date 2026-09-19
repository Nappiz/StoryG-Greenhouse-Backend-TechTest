"""Verify PostgreSQL independently from the HTTP API."""

from sqlalchemy.exc import SQLAlchemyError

from database.connection import check_database_connection


def main() -> int:
    try:
        check_database_connection()
    except SQLAlchemyError as exc:
        print(f"Database connection failed: {exc.__class__.__name__}")
        return 1

    print("Database connection successful")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
