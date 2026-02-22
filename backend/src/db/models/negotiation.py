"""Negotiation round model"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.dispute import Dispute


class NegotiationStatus(str, enum.Enum):
    """Negotiation round status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COUNTER = "counter"


class NegotiationRound(Base):
    """A single round of negotiation for a dispute."""

    __tablename__ = "negotiation_rounds"

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
    round_number: Mapped[int] = mapped_column(Integer)

    # Offers
    claimant_offer: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    respondent_offer: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    ai_suggested_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), default=NegotiationStatus.PENDING.value
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    dispute: Mapped["Dispute"] = relationship(
        "Dispute", back_populates="negotiation_rounds"
    )

    def __repr__(self) -> str:
        return f"<NegotiationRound {self.dispute_id} round={self.round_number}>"
