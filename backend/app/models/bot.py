from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from .company import Company
    from .conversation import Conversation


class Bot(Base):
    __tablename__ = "bots"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    token_encrypted: Mapped[str] = mapped_column(String(500))
    username: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    secret: Mapped[str] = mapped_column(String(100))  # secret_token بتاع الـ Webhook
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="bots")
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="bot",
        passive_deletes="all",
    )
