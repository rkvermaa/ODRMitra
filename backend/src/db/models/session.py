"""Session model - Chat sessions linked to users and disputes"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.user import User
    from src.db.models.dispute import Dispute
    from src.db.models.message import Message


class SessionStatus(str, enum.Enum):
    """Session status."""
    ACTIVE = "active"
    ESCALATED = "escalated"
    CLOSED = "closed"


class SessionType(str, enum.Enum):
    """Session type based on ODR workflow."""
    FILING = "filing"
    NEGOTIATION = "negotiation"
    HEARING = "hearing"
    GENERAL = "general"


class Session(Base):
    """Chat session between user and ODR agent."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    dispute_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("disputes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Channel and type
    channel: Mapped[str] = mapped_column(String(20), default="web")
    channel_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_type: Mapped[str] = mapped_column(
        String(20), default=SessionType.GENERAL.value
    )

    # State
    status: Mapped[str] = mapped_column(
        String(20), default=SessionStatus.ACTIVE.value
    )
    context_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    compaction_count: Mapped[int] = mapped_column(Integer, default=0)

    session_data: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    dispute: Mapped["Dispute | None"] = relationship("Dispute", back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Session {self.id} channel={self.channel} type={self.session_type}>"
