import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ratatosk.db.base import Base


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (Index("ix_attachments_dedup", "user_id", "source", "file_hash"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source: Mapped[str] = mapped_column(
        String(100), default="upload", nullable=False, index=True
    )
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    message_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    attachment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("attachments.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
