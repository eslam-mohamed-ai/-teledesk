from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .company import Company
    from .conversation import Conversation
    from .internal_note import InternalNote
    from .audit_log import AuditLog
    from .message import Message


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(32), nullable=False, server_default="agent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="users")
    assigned_conversations: Mapped[list["Conversation"]] = relationship(
        primaryjoin="Conversation.assignee_user_id == User.id",
        back_populates="assignee",
    )
    closed_conversations: Mapped[list["Conversation"]] = relationship(
        primaryjoin="Conversation.closed_by == User.id",
        back_populates="closed_by_user",
    )
    sent_messages: Mapped[list["Message"]] = relationship(
        back_populates="sender",
    )
    internal_notes: Mapped[list["InternalNote"]] = relationship(back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
