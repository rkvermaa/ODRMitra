"""WhatsApp authentication storage — Database-backed Baileys credentials for ODRMitra"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, JSON, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class WhatsAppAuth(Base):
    """
    Database-backed storage for Baileys WhatsApp credentials.

    ODRMitra uses user_id as the session identifier (single-tenant).
    """

    __tablename__ = "whatsapp_auth"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Link to the user who connected WhatsApp
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Friendly label for the bot (e.g., "Bot 1", "Support Line")
    label: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Connected WhatsApp phone number
    phone_number: Mapped[str | None] = mapped_column(String(15), nullable=True)

    # Baileys auth credentials (rarely changes after initial auth)
    creds: Mapped[dict] = mapped_column(JSON, default=dict)

    # Signal protocol keys (grows over time)
    keys: Mapped[dict] = mapped_column(JSON, default=dict)

    # Connection status: disconnected, connecting, connected
    status: Mapped[str] = mapped_column(String(20), default="disconnected")

    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    def __repr__(self) -> str:
        return f"<WhatsAppAuth user={self.user_id} phone={self.phone_number}>"

    @property
    def has_credentials(self) -> bool:
        """Check if this auth has valid credentials."""
        return bool(self.creds and self.creds.get("me"))
