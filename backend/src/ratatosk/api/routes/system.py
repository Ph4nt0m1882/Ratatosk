from fastapi import APIRouter
from pydantic import BaseModel
from ratatosk.core.config import settings, FeaturesConfig, RunMode

router = APIRouter(tags=["System"])

class BootstrapResponse(BaseModel):
    """Data sent to the client at the start for the UI configuration."""
    app_name: str
    app_version: str
    mode: RunMode
    features: FeaturesConfig

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }

@router.get("/bootstrap", response_model=BootstrapResponse)
async def bootstrap():
    return BootstrapResponse(
        app_name=settings.app_name,
        app_version=settings.app_version,
        mode=settings.mode,
        features=settings.features
    )
