from pydantic import AwareDatetime, BaseModel


class ConversationMetadata(BaseModel):
    id: str
    title: str
    archived: bool
    last_message: AwareDatetime | None
    nb_message: int
    owner_id: str
    owner_name: str
