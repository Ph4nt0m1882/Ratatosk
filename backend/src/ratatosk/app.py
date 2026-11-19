from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
from sqlalchemy import select

import ratatosk.db.models  # noqa: F401 - Save the models to ensure they are registered with SQLAlchemy
from ratatosk.core.config import settings
from ratatosk.core.idle_worker import IdleTrackingMiddleware, idle_worker
from ratatosk.db.base import Base
from ratatosk.db.models import SystemPrompt, User
from ratatosk.db.seeds import create_admin_user, get_default_prompts
from ratatosk.db.session import async_session_maker, engine
from ratatosk.endpoints.auth.router import router as auth_router
from ratatosk.endpoints.chat.router import router as chat_router
from ratatosk.endpoints.db_manipulation.router import router as db_router
from ratatosk.endpoints.health.router import router as health_router
from ratatosk.endpoints.settings.router import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed missing default system prompts without overwriting admin customizations
    async with async_session_maker() as session:
        existing_names = set(
            (await session.execute(select(SystemPrompt.name))).scalars().all()
        )
        missing_defaults = [
            p for p in get_default_prompts() if p.name not in existing_names
        ]
        if missing_defaults:
            session.add_all(missing_defaults)
            await session.commit()

        result = await session.execute(
            select(User.id).where(User.is_admin == True).limit(1)
        )
        if result.scalar_one_or_none() is None:
            session.add(
                create_admin_user(settings.admin_username, settings.admin_password)
            )
            await session.commit()

    idle_worker.start()
    yield
    await idle_worker.stop()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url=None,
)

app.add_middleware(IdleTrackingMiddleware, worker=idle_worker)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Attachment-Complete",
        "X-Original-Mime-Type",
        "X-Preview-Kind",
        "Content-Disposition",
    ],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(db_router)
app.include_router(settings_router)


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
