from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .bot import Bot
    from .channel import Channel
    from .contact import Contact
    from .chunk import Chunk
    from .conversation import Conversation
    from .document import Document
    from .invitation import Invitation
    from .tag import Tag
    from .user import User
    from .message import Message
    from .audit_log import AuditLog
    from .canned_reply import CannedReply
    from .contact_field_definition import ContactFieldDefinition


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    welcome: Mapped[str] = mapped_column(Text, default="أهلا بيك! تحب أساعدك في إيه؟")
    tone: Mapped[str] = mapped_column(String(20), default="friendly")  # friendly | professional | formal
    reply_language: Mapped[str] = mapped_column(String(10), default="auto")  # auto | ar | en
    handoff_on_request: Mapped[bool] = mapped_column(Boolean, default=True)
    handoff_out_of_scope: Mapped[bool] = mapped_column(Boolean, default=True)
    handoff_keywords: Mapped[str] = mapped_column(Text, default="شكوى,استرداد,مكسور")
    handoff_after_two: Mapped[bool] = mapped_column(Boolean, default=False)
    work_hours: Mapped[str] = mapped_column(String(200), default="")
    plan: Mapped[str] = mapped_column(String(20), default="free")
    onboarding_step: Mapped[str | None] = mapped_column(String(40), nullable=True)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    profile: Mapped[dict | None] = mapped_column(postgresql.JSONB(astext_type=Text()), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="company")
    bots: Mapped[list["Bot"]] = relationship(back_populates="company")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="company")
    messages: Mapped[list["Message"]] = relationship(back_populates="company")
    documents: Mapped[list["Document"]] = relationship(back_populates="company")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="company")
    channels: Mapped[list["Channel"]] = relationship(back_populates="company", passive_deletes="all")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="company", passive_deletes="all")
    tags: Mapped[list["Tag"]] = relationship(back_populates="company", passive_deletes="all")
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="company", passive_deletes="all")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="company", passive_deletes="all")
    canned_replies: Mapped[list["CannedReply"]] = relationship(back_populates="company", passive_deletes="all")
    contact_field_definitions: Mapped[list["ContactFieldDefinition"]] = relationship(
        back_populates="company", passive_deletes="all",
    )
