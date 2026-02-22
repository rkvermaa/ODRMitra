"""Settlement agreement model"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.dispute import Dispute


class SettlementStatus(str, enum.Enum):
    """Settlement agreement status."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    ACCEPTED_CLAIMANT = "accepted_claimant"
    ACCEPTED_RESPONDENT = "accepted_respondent"
    EXECUTED = "executed"
    REJECTED = "rejected"


class SettlementAgreement(Base):
    """AI-drafted settlement agreement for a dispute."""

    __tablename__ = "settlement_agreements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disputes.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Agreement content
    content_markdown: Mapped[str] = mapped_column(Text)
    settlement_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    payment_schedule: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    terms: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[str] = mapped_column(
        String(30), default=SettlementStatus.DRAFT.value
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    signed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    dispute: Mapped["Dispute"] = relationship(
        "Dispute", back_populates="settlement"
    )

    def __repr__(self) -> str:
        return f"<SettlementAgreement {self.dispute_id} ({self.status})>"
