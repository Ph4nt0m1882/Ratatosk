from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from ratatosk.core.config import settings
from ratatosk.endpoints.health.router import router as health_router

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    docs_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)


@app.get("/", include_in_schema=False)
def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}! Visit /docs for the API reference.",
        "version": settings.app_version,
        "description": settings.app_description,
    }


@app.get("/docs", include_in_schema=False)
def docs():
    """Redirect to the Scalar API reference."""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=settings.app_name,
    )
