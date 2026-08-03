# ORM models

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Computed, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

# Embedding dimensions (assuming BGE-base-en-v1.5 embedding model is used)
EMBEDDING_DIM = 768


class User(Base):
    """User account"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # user's contacts (one-to-many: user -> contacts)
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="owner", cascade="all, delete-orphan"
    )


class Contact(Base):
    """A contact (person) the user is tracking"""

    __tablename__ = "contacts"
    # GIN index on the search_tsv column
    __table_args__ = (
        Index("contacts_search_tsv_gin", "search_tsv", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Structured profile (manual or extracted during create flow)
    display_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    company: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))

    # LLM-generated natural language summary (to be embedded and retrieved by semantic search)
    profile_text: Mapped[str | None] = mapped_column(Text)

    # Full-text search document derived from profile_text
    search_tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', coalesce(profile_text, ''))", persisted=True),
    )

    # Embedding of the profile text (to be used for semantic search)
    profile_embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    # Searchable tags, e.g. ["investor", "tech", "hiking"]
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Owner of the contact (one-to-many: user -> contacts)
    owner: Mapped["User"] = relationship("User", back_populates="contacts")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())