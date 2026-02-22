"""User model"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.dispute import Dispute
    from src.db.models.session import Session
    from src.db.models.document import DisputeDocument


class UserRole(str, enum.Enum):
    """User role in the ODR platform."""
    CLAIMANT = "claimant"
    RESPONDENT = "respondent"
    CONCILIATOR = "conciliator"
    ADMIN = "admin"


class User(Base):
    """User of the ODR platform (claimant/respondent/conciliator)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    mobile_number: Mapped[str] = mapped_column(
        String(15), unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.CLAIMANT.value)

    # MSME details
    organization_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    udyam_registration: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(10), nullable=True)  # micro/small/medium
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    district: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pin_code: Mapped[str | None] = mapped_column(String(6), nullable=True)

    # Channel connections
    whatsapp_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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
    filed_disputes: Mapped[list["Dispute"]] = relationship(
        "Dispute",
        back_populates="claimant",
        foreign_keys="Dispute.claimant_id",
        cascade="all, delete-orphan",
    )
    responded_disputes: Mapped[list["Dispute"]] = relationship(
        "Dispute",
        back_populates="respondent",
        foreign_keys="Dispute.respondent_id",
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    uploaded_documents: Mapped[list["DisputeDocument"]] = relationship(
        "DisputeDocument",
        back_populates="uploaded_by_user",
    )

    def __repr__(self) -> str:
        return f"<User {self.mobile_number} ({self.name})>"
