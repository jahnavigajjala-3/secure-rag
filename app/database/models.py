import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import ForeignKey, String, Table, Column, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

document_roles = Table(
    "document_roles",
    Base.metadata,
    Column(
        "document_id",
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    username: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    email: Mapped[Optional[str]] = mapped_column(
        String,
        unique=True,
        nullable=True,
    )

    password_hash: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles,
        back_populates="users",
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    users: Mapped[list["User"]] = relationship(
        secondary=user_roles,
        back_populates="roles",
    )

    documents: Mapped[list["Document"]] = relationship(
        secondary=document_roles,
        back_populates="roles",
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    filename: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String,
        default="UPLOADED",
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    uploaded_by_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    uploaded_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[uploaded_by_id],
    )

    roles: Mapped[list["Role"]] = relationship(
        secondary=document_roles,
        back_populates="documents",
    )