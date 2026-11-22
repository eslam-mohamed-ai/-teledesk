from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .company import Company
    from .conversation import Conversation
    from .email_verification_token import EmailVerificationToken
    from .internal_note import InternalNote
    from .audit_log import AuditLog
    from .message import Message
    from .password_reset_token import PasswordResetToken
    from .refresh_token import RefreshToken


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(32), nullable=False, server_default="agent")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
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
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", passive_deletes="all")
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(back_populates="user", passive_deletes="all")
    email_verification_tokens: Mapped[list["EmailVerificationToken"]] = relationship(
        back_populates="user", passive_deletes="all",
    )
