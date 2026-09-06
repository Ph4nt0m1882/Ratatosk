from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
from ratatosk.api.routes import system
from ratatosk.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🐿️ Ratatosk Engine starting up...")
    yield
    print("🐿️ Ratatosk Engine shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None
    )
    # CORS config for the flutter app, to be refined according to the profiles
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/docs", include_in_schema=False)
    async def scalar_docs():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=app.title,
        )

    app.include_router(system.router, tags=["System"])
    return app
