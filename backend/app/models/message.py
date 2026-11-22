from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .attachment import Attachment
    from .channel import Channel
    from .company import Company
    from .conversation import Conversation
    from .user import User


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index(
            "ix_messages_conversation_id_created_at",
            "conversation_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), index=True, nullable=True)
    role: Mapped[str] = mapped_column(String(10))  # customer | bot | agent | system
    direction: Mapped[str | None] = mapped_column(String(16), nullable=True)  # inbound | outbound
    sender_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # contact | ai | agent | system
    sender_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str | None] = mapped_column(String(250), nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    flag: Mapped[str | None] = mapped_column(String(20), nullable=True)  # auto | handoff | out_of_scope
    unanswered: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_to_message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    company: Mapped["Company"] = relationship(back_populates="messages")
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    channel: Mapped["Channel | None"] = relationship(back_populates="messages")
    sender: Mapped["User | None"] = relationship(back_populates="sent_messages", foreign_keys=[sender_user_id])
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="message", passive_deletes="all",
    )
