import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Table, Column, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base
from app.config import settings

EMBEDDING_DIMENSION = settings.EMBEDDING_DIMENSION

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    extend_existing=True,
)

document_roles = Table(
    "document_roles",
    Base.metadata,
    Column(
        "document_id",
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    Column(
        "role_id",
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    extend_existing=True,
)

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    username: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    name: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    full_name: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    employee_id: Mapped[Optional[str]] = mapped_column(
        String,
        unique=True,
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles,
        back_populates="users",
    )

    documents_uploaded: Mapped[list["Document"]] = relationship(
        back_populates="uploaded_by",
        foreign_keys="Document.uploaded_by_id",
    )

    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user",
        foreign_keys="AuditLog.actor_user_id",
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
        index=True,
    )

    description: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
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

    filename: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    name: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    original_filename: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    storage_path: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    file_path: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    status: Mapped[str] = mapped_column(
        String,
        default="PROCESSING",
        index=True,
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    uploaded_by_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    uploaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    uploaded_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[uploaded_by_id],
        back_populates="documents_uploaded",
    )

    roles: Mapped[list["Role"]] = relationship(
        secondary=document_roles,
        back_populates="documents",
        cascade="save-update, merge",
    )

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    # Adjust the dimension (e.g. 768, 1024, or 1536) to match your embedding model
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSION),
        nullable=False,
    )

    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    actor_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    resource_type: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    resource_id: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String,
        default="SUCCESS",
        nullable=False,
        index=True,
    )

    audit_metadata: Mapped[Optional[str]] = mapped_column("metadata", Text, nullable=True)

    ip_address: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[actor_user_id],
        back_populates="audit_logs",
    )