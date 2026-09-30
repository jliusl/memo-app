from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import httpx
import pytest
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from app.config import Settings
from app.db import create_engine, create_sessionmaker
from app.main import create_app

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# One account, reused by tests that only need to be signed in. Registering through the
# real endpoint is deliberate: the cookie that comes back is the same one the browser
# gets, so every Memo test exercises the real authentication path.
CREDENTIALS = {"email": "owner@example.com", "password": "correct-horse"}


@pytest.fixture(scope="session")
def settings() -> Settings:
    # Explicit arguments beat .env, so the suite always targets memo_test with cheap
    # password hashing no matter what the developer has configured.
    return Settings(env="test", bcrypt_rounds=4)


@pytest.fixture(scope="session", autouse=True)
def migrated_database(settings: Settings) -> None:
    """Run the real migrations instead of metadata.create_all, so a broken or drifted
    migration fails the suite rather than hiding behind the models."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", settings.database_url(test=True))
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
async def client(settings: Settings) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    await app.state.engine.dispose()


@pytest.fixture(autouse=True)
async def clean_database(client: httpx.AsyncClient) -> AsyncIterator[None]:
    """Every test starts from an empty database and a clean cookie jar.

    Going through the reset route rather than truncating directly keeps the suite honest
    about that route working, since E2E setup depends on it too."""
    client.cookies.clear()
    response = await client.post("/api/__test__/reset")
    assert response.status_code == 200, response.text
    yield


@pytest.fixture
def reset(client: httpx.AsyncClient) -> Callable[..., Awaitable[dict]]:
    async def _reset(*, users: list[dict] = (), memos: list[dict] = ()) -> dict:
        response = await client.post("/api/__test__/reset", json={"users": list(users), "memos": list(memos)})
        assert response.status_code == 200, response.text
        return response.json()

    return _reset


@pytest.fixture
async def signed_in(client: httpx.AsyncClient) -> dict[str, str]:
    response = await client.post("/api/auth/register", json=CREDENTIALS)
    assert response.status_code == 201, response.text
    return CREDENTIALS


@pytest.fixture
def create_memo(client: httpx.AsyncClient) -> Callable[..., Awaitable[dict]]:
    async def _create(**payload: object) -> dict:
        response = await client.post("/api/memos", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
async def session(settings: Settings) -> AsyncIterator[AsyncSession]:
    """Direct database access, for the few tests that need to place rows in a state the
    API deliberately cannot produce - such as an explicitly backdated `updated_at`."""
    engine = create_engine(settings, test=True)
    async with create_sessionmaker(engine)() as session:
        yield session
    await engine.dispose()
