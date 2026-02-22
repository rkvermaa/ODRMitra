"""Knowledge document model — admin-uploaded legal docs for RAG."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid
import enum

from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class DocCategory(str, enum.Enum):
    """Categories for admin-uploaded legal documents."""
    ACT = "act"
    RULES = "rules"
    JUDGMENT = "judgment"
    CIRCULAR = "circular"
    OTHER = "other"


class IndexStatus(str, enum.Enum):
    """RAG indexing status."""
    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class KnowledgeDocument(Base):
    """Admin-uploaded legal document for the shared RAG knowledge base."""

    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # File info
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_url: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer, default=0)

    # Classification
    doc_category: Mapped[str] = mapped_column(
        String(30), default=DocCategory.OTHER.value
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Indexing status
    index_status: Mapped[str] = mapped_column(
        String(20), default=IndexStatus.PENDING.value
    )
    index_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # Upload info
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    uploaded_by_user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<KnowledgeDocument {self.original_filename} ({self.doc_category})>"
