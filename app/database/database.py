import os
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./secure_rag.db")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create all database tables if they do not exist and ensure schema is updated."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR;"))
            conn.commit()
        except Exception:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR;"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR;"))
                conn.commit()
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR;"))
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
