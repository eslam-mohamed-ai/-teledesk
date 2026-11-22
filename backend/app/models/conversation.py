from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.association import conversation_tags

if TYPE_CHECKING:
    from .bot import Bot
    from .channel import Channel
    from .company import Company
    from .contact import Contact
    from .internal_note import InternalNote
    from .message import Message
    from .tag import Tag
    from .user import User


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index(
            "ix_conversations_company_id_last_message_at",
            "company_id",
            "last_message_at",
        ),
        Index(
            "ix_conversations_company_status_last_message",
            "company_id",
            "status",
            "last_message_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    bot_id: Mapped[int | None] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), index=True, nullable=True)
    tg_chat_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    channel_id: Mapped[int | None] = mapped_column(ForeignKey("channels.id", ondelete="SET NULL"), index=True, nullable=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"), index=True, nullable=True)
    assignee_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    customer_name: Mapped[str] = mapped_column(String(200), default="عميل")
    username: Mapped[str] = mapped_column(String(100), default="")
    lang: Mapped[str] = mapped_column(String(5), default="ar")
    status: Mapped[str] = mapped_column(String(20), default="bot")  # bot | needs_human | human | closed
    priority: Mapped[str | None] = mapped_column(String(16), default="normal")
    handoff_reason: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    last_preview: Mapped[str] = mapped_column(String(200), default="")
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="conversations")
    bot: Mapped["Bot"] = relationship(back_populates="conversations")
    channel: Mapped["Channel | None"] = relationship(back_populates="conversations")
    contact: Mapped["Contact | None"] = relationship(back_populates="conversations")
    assignee: Mapped["User | None"] = relationship(
        back_populates="assigned_conversations", foreign_keys=[assignee_user_id],
    )
    closed_by_user: Mapped["User | None"] = relationship(
        back_populates="closed_conversations", foreign_keys=[closed_by],
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        passive_deletes="all",
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary=conversation_tags,
        back_populates="conversations",
    )
    internal_notes: Mapped[list["InternalNote"]] = relationship(
        back_populates="conversation", passive_deletes="all",
    )
