from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field


class ConversationMetadata(BaseModel):
    id: str
    title: str
    archived: bool
    last_message: AwareDatetime | None
    nb_message: int
    owner_id: str
    owner_name: str


class ConversationManager(BaseModel):
    id: str
    title: str
    title_auto: bool
    archived: bool
    anchor_message: str | None  # id of a reference message for manage the scroll
    anchor_message_index: int | None
    nb_message: int


class RefMessage(StrEnum):
    AFTER = "after"  # want the x next message
    AROUND = "around"  # want the x/2 previous message and the x/2 next message
    BEFORE = "before"  # want the x previous message


class MessagesRequest(BaseModel):
    conversation_id: str
    nb_requested: int = Field(default=30, gt=0, le=200)
    ref_message: RefMessage = RefMessage.AROUND
    ref_message_id: str | None = None


class MessageData(BaseModel):
    id: str
    role: str
    model: str
    content: str
    parts: list[dict] | None = None
    token_count: int | None = None
    cost: float | None = None
    is_first: bool = False  # when it's the first message of the conversation
    is_last: bool = False  # when it's the last message of the conversation
    created_at: AwareDatetime


class ConversationUpdate(BaseModel):
    title: str | None = None
    title_auto: bool | None = None
    archived: bool | None = None
