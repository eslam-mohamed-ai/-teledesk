from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.dialects import postgresql
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .channel import Channel
    from .contact import Contact


class ContactIdentity(Base):
    __tablename__ = "contact_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_snapshot: Mapped[dict | None] = mapped_column(postgresql.JSONB(astext_type=Text()), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    contact: Mapped["Contact"] = relationship(back_populates="identities")
    channel: Mapped["Channel"] = relationship(back_populates="contact_identities")
