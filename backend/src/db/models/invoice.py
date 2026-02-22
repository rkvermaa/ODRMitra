"""Invoice model — supports multiple invoices per dispute."""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import String, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.dispute import Dispute
    from src.db.models.document import DisputeDocument


class Invoice(Base):
    """Individual invoice linked to a dispute case."""

    __tablename__ = "invoices"

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

    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    invoice_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    acceptance_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount_received: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    last_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    balance_due: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    # Link to uploaded invoice PDF
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dispute_documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    dispute: Mapped["Dispute"] = relationship(
        "Dispute", back_populates="invoices"
    )
    document: Mapped["DisputeDocument | None"] = relationship(
        "DisputeDocument", foreign_keys=[document_id]
    )

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number} ({self.invoice_amount})>"
