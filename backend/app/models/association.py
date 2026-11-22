from sqlalchemy import Column, ForeignKey, Integer, PrimaryKeyConstraint, Table

from app.database import Base

contact_tags = Table(
    "contact_tags",
    Base.metadata,
    Column("contact_id", Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
    PrimaryKeyConstraint("contact_id", "tag_id", name="contact_tags_pkey"),
)

conversation_tags = Table(
    "conversation_tags",
    Base.metadata,
    Column("conversation_id", Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False),
    PrimaryKeyConstraint("conversation_id", "tag_id", name="conversation_tags_pkey"),
)
