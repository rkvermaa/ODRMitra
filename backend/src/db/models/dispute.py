"""Dispute model"""

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Date,
    JSON,
    ForeignKey,
    Numeric,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.user import User
    from src.db.models.document import DisputeDocument
    from src.db.models.session import Session
    from src.db.models.negotiation import NegotiationRound
    from src.db.models.settlement import SettlementAgreement
    from src.db.models.hearing import Hearing
    from src.db.models.invoice import Invoice


class DisputeStatus(str, enum.Enum):
    """Maps to the 16-step ODR workflow."""
    FILED = "filed"
    INTIMATION_SENT = "intimation_sent"
    SOD_FILED = "sod_filed"
    PRE_MSEFC = "pre_msefc"
    DGP = "dgp"
    NEGOTIATION = "negotiation"
    MSEFC = "msefc"
    SCRUTINY_SOC = "scrutiny_soc"
    NOTICE = "notice"
    SCRUTINY_SOD = "scrutiny_sod"
    CONCILIATION_ASSIGNED = "conciliation_assigned"
    CONCILIATION_PROCEEDINGS = "conciliation_proceedings"
    CONCILIATION = "conciliation"
    ARBITRATION = "arbitration"
    RESOLUTION = "resolution"
    CLOSED = "closed"


class DisputeCategory(str, enum.Enum):
    """Dispute categories under MSMED Act."""
    DELAYED_PAYMENT = "delayed_payment"
    NON_PAYMENT = "non_payment"
    PARTIAL_PAYMENT = "partial_payment"
    DISPUTED_QUALITY = "disputed_quality"
    CONTRACTUAL_DISPUTE = "contractual_dispute"
    OTHER = "other"


class Dispute(Base):
    """MSME delayed payment dispute case."""

    __tablename__ = "disputes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    case_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True
    )

    # Parties
    claimant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    respondent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    respondent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    respondent_mobile: Mapped[str | None] = mapped_column(String(15), nullable=True)
    respondent_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    respondent_category: Mapped[str | None] = mapped_column(String(30), nullable=True)  # individual/company/organization/govt
    respondent_pan: Mapped[str | None] = mapped_column(String(10), nullable=True)
    respondent_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    respondent_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    respondent_district: Mapped[str | None] = mapped_column(String(50), nullable=True)
    respondent_pin_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    respondent_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Case details
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(30), default=DisputeCategory.DELAYED_PAYMENT.value
    )
    sub_category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Transaction / PO (Tab 4)
    po_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    po_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_terms: Mapped[str | None] = mapped_column(String(500), nullable=True)
    goods_services_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Financial — claimed_amount is the formal claim total (= total_amount_due at filing)
    claimed_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    invoice_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    amount_received: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    principal_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    interest_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    interest_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    interest_amount: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    total_amount_due: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    # SOC narrative (Tab 4)
    cause_of_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    relief_sought: Mapped[str | None] = mapped_column(Text, nullable=True)
    correspondence_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    buyer_objections: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # [{date, nature, resolved}]
    msefc_council: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status (16-step workflow)
    status: Mapped[str] = mapped_column(
        String(30), default=DisputeStatus.FILED.value, index=True
    )

    # AI analysis results (stored as JSON for flexibility)
    ai_classification: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_missing_docs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_outcome_prediction: Mapped[dict | None] = mapped_column(JSON, nullable=True)

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
    claimant: Mapped["User"] = relationship(
        "User", back_populates="filed_disputes", foreign_keys=[claimant_id]
    )
    respondent: Mapped["User | None"] = relationship(
        "User", back_populates="responded_disputes", foreign_keys=[respondent_id]
    )
    documents: Mapped[list["DisputeDocument"]] = relationship(
        "DisputeDocument",
        back_populates="dispute",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="dispute",
    )
    negotiation_rounds: Mapped[list["NegotiationRound"]] = relationship(
        "NegotiationRound",
        back_populates="dispute",
        cascade="all, delete-orphan",
        order_by="NegotiationRound.round_number",
    )
    settlement: Mapped["SettlementAgreement | None"] = relationship(
        "SettlementAgreement",
        back_populates="dispute",
        uselist=False,
    )
    hearings: Mapped[list["Hearing"]] = relationship(
        "Hearing",
        back_populates="dispute",
        cascade="all, delete-orphan",
        order_by="Hearing.scheduled_date",
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="dispute",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Dispute {self.case_number} ({self.status})>"
