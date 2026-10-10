import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

load_dotenv()

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


class Base(DeclarativeBase):
    pass

# Import models so SQLAlchemy metadata is populated before create_all() is called.
from app.database import models  # noqa: F401


def init_db() -> None:
    """Development/test initialization only. Production uses Alembic migrations."""
    if settings.is_production():
        return

    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        try:
            def ensure_columns(table_name: str, column_defs: list[tuple[str, str]]) -> None:
                existing = {
                    row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name});")).fetchall()
                }
                for column_name, ddl in column_defs:
                    if column_name not in existing:
                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl};"))

            ensure_columns("users", [
                ("name", "VARCHAR"),
                ("email", "VARCHAR"),
                ("password_hash", "VARCHAR"),
                ("full_name", "VARCHAR"),
                ("employee_id", "VARCHAR"),
                ("is_active", "BOOLEAN DEFAULT TRUE"),
                ("created_at", "TIMESTAMP"),
                ("updated_at", "TIMESTAMP"),
            ])
            ensure_columns("roles", [
                ("description", "VARCHAR"),
                ("created_at", "TIMESTAMP"),
            ])
            ensure_columns("documents", [
                ("name", "VARCHAR"),
                ("original_filename", "VARCHAR"),
                ("storage_path", "VARCHAR"),
                ("file_path", "VARCHAR"),
                ("status", "VARCHAR"),
                ("file_size", "INTEGER"),
                ("chunk_count", "INTEGER"),
                ("uploaded_by_id", "VARCHAR"),
                ("created_at", "TIMESTAMP"),
                ("updated_at", "TIMESTAMP"),
                ("uploaded_at", "TIMESTAMP"),
                ("error_message", "VARCHAR"),
            ])
            conn.commit()
        except Exception:
            pass


def get_db() -> Generator[Session, None, None]:
    """Dependency generator for database sessions in FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
