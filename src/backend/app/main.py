from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import Settings
from .db import create_engine, create_sessionmaker
from .routers import auth, memos, test_support


def create_app(settings: Settings | None = None) -> FastAPI:
    """An app factory rather than a module-level singleton, so that tests can build an
    app in a different environment. That is how the absence of the test-only reset
    route outside ENV=test is verified, rather than assumed."""
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await app.state.engine.dispose()

    app = FastAPI(title="Memo API", version="0.1.0", lifespan=lifespan)

    app.state.settings = settings
    app.state.engine = create_engine(settings, test=settings.is_test)
    app.state.sessionmaker = create_sessionmaker(app.state.engine)

    @app.get("/api/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Used as the readiness probe by the Playwright webServer and by CI."""
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/api")
    app.include_router(memos.router, prefix="/api")

    if settings.is_test:
        app.include_router(test_support.router, prefix="/api")

    return app


app = create_app()
