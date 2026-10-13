from fastapi import Query
from pydantic import AwareDatetime, BaseModel, ConfigDict


class SystemPromptMetadata(BaseModel):
    id: str
    name: str
    hierarchy: int
    description: str | None = None
    is_active: bool
    is_default: bool
    last_modification: AwareDatetime


class SystemPromptRequest(BaseModel):
    id: str | None = Query(default=None, description="Filter by id")
    name: str | None = Query(default=None, description="Filter by name")
    hierarchy: int | None = Query(default=None, description="Filster by hierarchy")


class SystemPromptBase(BaseModel):
    name: str
    hierarchy: int = 0
    description: str | None = None
    content: str
    is_active: bool = True


class SystemPromptCreate(SystemPromptBase):
    pass


class SystemPromptContent(SystemPromptBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_default: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


class SystemPromptUpdate(BaseModel):
    name: str | None = None
    hierarchy: int | None = None
    description: str | None = None
    content: str | None = None
    is_active: bool | None = None
