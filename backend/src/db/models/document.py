"""Dispute document model"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.dispute import Dispute
    from src.db.models.user import User


class DocType(str, enum.Enum):
    """Document types for MSME disputes."""
    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"
    CONTRACT = "contract"
    DELIVERY_CHALLAN = "delivery_challan"
    CORRESPONDENCE = "correspondence"
    BANK_STATEMENT = "bank_statement"
    UDYAM_CERTIFICATE = "udyam_certificate"
    AFFIDAVIT = "affidavit"
    LEGAL_NOTICE = "legal_notice"
    SOC = "soc"
    SOD = "sod"
    OTHER = "other"


class AnalysisStatus(str, enum.Enum):
    """Document AI analysis status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DisputeDocument(Base):
    """Document uploaded for a dispute case."""

    __tablename__ = "dispute_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disputes.id", ondelete="CASCADE"),
        index=True,
    )

    # File info
    filename: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    doc_type: Mapped[str] = mapped_column(String(30), default=DocType.OTHER.value)
    file_url: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(Integer, default=0)

    # AI analysis
    analysis_status: Mapped[str] = mapped_column(
        String(20), default=AnalysisStatus.PENDING.value
    )
    analysis_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extracted_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    # RAG indexing status
    index_status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )

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

    # Relationships
    dispute: Mapped["Dispute"] = relationship(
        "Dispute", back_populates="documents"
    )
    uploaded_by_user: Mapped["User"] = relationship(
        "User", back_populates="uploaded_documents"
    )

    def __repr__(self) -> str:
        return f"<DisputeDocument {self.original_filename} ({self.doc_type})>"
