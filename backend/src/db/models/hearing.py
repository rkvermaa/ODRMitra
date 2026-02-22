"""Hearing model"""

from datetime import date, datetime, time, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import String, Text, DateTime, Date, Time, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.dispute import Dispute
    from src.db.models.user import User
    from src.db.models.session import Session


class HearingType(str, enum.Enum):
    """Hearing type."""
    CONCILIATION = "conciliation"
    ARBITRATION = "arbitration"


class HearingStatus(str, enum.Enum):
    """Hearing status."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class Hearing(Base):
    """Scheduled hearing for a dispute."""

    __tablename__ = "hearings"

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

    hearing_type: Mapped[str] = mapped_column(
        String(20), default=HearingType.CONCILIATION.value
    )
    scheduled_date: Mapped[date] = mapped_column(Date)
    scheduled_time: Mapped[time] = mapped_column(Time)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)

    status: Mapped[str] = mapped_column(
        String(20), default=HearingStatus.SCHEDULED.value
    )

    # Chat-based hearing room session
    room_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    dispute: Mapped["Dispute"] = relationship(
        "Dispute", back_populates="hearings"
    )
    creator: Mapped["User"] = relationship("User")
    room_session: Mapped["Session | None"] = relationship("Session")

    def __repr__(self) -> str:
        return f"<Hearing {self.dispute_id} ({self.hearing_type} {self.scheduled_date})>"
