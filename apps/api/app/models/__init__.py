"""SQLAlchemy models."""

from app.models.abandoned_checkout import AbandonedCheckout, CheckoutStatus
from app.models.base import Base
from app.models.conversation import Channel, Conversation, ConversationStatus
from app.models.email_unsubscribe import EmailUnsubscribe
from app.models.integration import IntegrationStatus, PlatformType, StoreIntegration
from app.models.knowledge import ContentType, KnowledgeArticle, KnowledgeChunk
from app.models.message import Message, MessageRole
from app.models.order_inquiry import InquiryResolution, InquiryType, OrderInquiry
from app.models.product import Product
from app.models.recovery_event import RecoveryEvent
from app.models.recovery_sequence import RecoverySequence, SequenceStatus
from app.models.store import Store

__all__ = [
    # Base
    "Base",
    # Store & Integration
    "Store",
    "StoreIntegration",
    "PlatformType",
    "IntegrationStatus",
    # Products
    "Product",
    # Knowledge
    "KnowledgeArticle",
    "KnowledgeChunk",
    "ContentType",
    # Conversations
    "Conversation",
    "ConversationStatus",
    "Channel",
    "Message",
    "MessageRole",
    # Order Inquiries
    "OrderInquiry",
    "InquiryType",
    "InquiryResolution",
    # Cart Recovery
    "AbandonedCheckout",
    "CheckoutStatus",
    "RecoverySequence",
    "SequenceStatus",
    "RecoveryEvent",
    "EmailUnsubscribe",
]
