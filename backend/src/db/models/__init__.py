"""Database models"""

from src.db.models.user import User, UserRole
from src.db.models.skill import Skill
from src.db.models.dispute import Dispute, DisputeStatus, DisputeCategory
from src.db.models.document import DisputeDocument, DocType, AnalysisStatus
from src.db.models.knowledge_document import KnowledgeDocument, DocCategory, IndexStatus
from src.db.models.invoice import Invoice
from src.db.models.session import Session, SessionStatus, SessionType
from src.db.models.message import Message, MessageRole
from src.db.models.negotiation import NegotiationRound, NegotiationStatus
from src.db.models.settlement import SettlementAgreement, SettlementStatus
from src.db.models.hearing import Hearing, HearingType, HearingStatus
from src.db.models.whatsapp_auth import WhatsAppAuth

__all__ = [
    "User",
    "UserRole",
    "Skill",
    "Dispute",
    "DisputeStatus",
    "DisputeCategory",
    "DisputeDocument",
    "DocType",
    "AnalysisStatus",
    "KnowledgeDocument",
    "DocCategory",
    "IndexStatus",
    "Invoice",
    "Session",
    "SessionStatus",
    "SessionType",
    "Message",
    "MessageRole",
    "NegotiationRound",
    "NegotiationStatus",
    "SettlementAgreement",
    "SettlementStatus",
    "Hearing",
    "HearingType",
    "HearingStatus",
    "WhatsAppAuth",
]
