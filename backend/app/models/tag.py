from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.association import contact_tags, conversation_tags

if TYPE_CHECKING:
    from .company import Company
    from .contact import Contact
    from .conversation import Conversation


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    company: Mapped["Company"] = relationship(back_populates="tags")
    contacts: Mapped[list["Contact"]] = relationship(
        secondary=contact_tags,
        back_populates="tags",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        secondary=conversation_tags,
        back_populates="tags",
    )
