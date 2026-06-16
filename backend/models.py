# ORM models

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

import enum

from backend.db import Base

# Embedding dimensions (assuming BGE-base-en-v1.5 embedding model is used)
EMBEDDING_DIM = 768

# ---- ENUMS ----
class Modality(str, enum.Enum):
    voice = "voice"
    image = "image"
    text = "text"

class CaptureStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    error = "error"

# ---- MODELS ----
class User(Base):
    """User account"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # user's contacts (one-to-many: user -> contacts)
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="owner", cascade="all, delete-orphan"
    )


class Contact(Base):
    """A contact (person) the user is tracking"""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Structured profile (manual or extracted from captures)
    display_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    company: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))

    # LLM-generated natural language summary (to be embedded and retrieved by semantic search)
    profile_text: Mapped[str | None] = mapped_column(Text)
    
    # Embedding of the profile text (to be used for semantic search)
    profile_embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    # Structured JSON ground truth tags (to be used for filtering and searching)
    profile_tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


    # Relationships (one-to-many: user -> contacts, contact -> captures)
    owner: Mapped["User"] = relationship("User", back_populates="contacts")
    captures: Mapped[list["Capture"]] = relationship(
        "Capture", back_populates="contact", cascade="all, delete-orphan"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Capture(Base):
    """Output from capture (voice note, image scan, free-form text) after processing"""
    __tablename__ = "captures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Contact associated with the capture (one-to-many: contact -> captures)
    contact_id: Mapped[int] = mapped_column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Modality of the capture (voice, image, text)
    modality: Mapped[Modality] = mapped_column(SAEnum(Modality), nullable=False)

    # Raw text of the capture (transcript or OCR output)
    raw_text: Mapped[str | None] = mapped_column(Text)

    # Status of the capture (pending, processing, done, error)
    status: Mapped[CaptureStatus] = mapped_column(SAEnum(CaptureStatus), default=CaptureStatus.pending, nullable=False)
    
    # Relationships (one-to-many: contact -> captures)
    contact: Mapped["Contact"] = relationship("Contact", back_populates="captures")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
