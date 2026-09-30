from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .config import Settings


def create_engine(settings: Settings, *, test: bool = False) -> AsyncEngine:
    """Engines are lazy: constructing one does not open a connection, which is why
    tests can build an app for the routing-only checks without a database running."""
    return create_async_engine(settings.database_url(test=test), pool_pre_ping=True)


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False so a router can return a model after committing
    # without triggering a lazy refresh that would need a second round trip.
    return async_sessionmaker(engine, expire_on_commit=False)
