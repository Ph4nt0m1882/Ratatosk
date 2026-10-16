import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ratatosk.db.base import Base


class SystemPrompt(Base):
    __tablename__ = "system_prompts"

    # organization by modular prompting, a document is a short text that define for exemple, the personality, the tone, the style, the context, the knowledge, the memory, the behavior of the AI assistant.

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hierarchy: Mapped[int] = mapped_column(  # Order of the prompt in the list
        nullable=False, default=0, unique=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(  # content of the prompt sent to the LLM
        Text, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
