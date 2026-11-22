from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.dialects import postgresql
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.association import contact_tags

if TYPE_CHECKING:
    from .company import Company
    from .contact_identity import ContactIdentity
    from .conversation import Conversation
    from .tag import Tag


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    custom_fields: Mapped[dict | None] = mapped_column(postgresql.JSONB(astext_type=Text()), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    merged_into_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="contacts")
    identities: Mapped[list["ContactIdentity"]] = relationship(
        back_populates="contact", passive_deletes="all",
    )
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="contact")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=contact_tags,
        back_populates="contacts",
    )
