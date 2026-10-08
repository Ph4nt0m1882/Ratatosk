from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    provider: str
    display_name: str
    tasks: list[str] = ["text-generation"]
    tier: str = "standard"
    context_window: int | None = None
    is_recommended: bool = False


class ListModelsResponse(BaseModel):
    models: list[ModelInfo]
