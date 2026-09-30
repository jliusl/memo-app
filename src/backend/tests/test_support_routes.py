import httpx

from app.config import Settings
from app.main import create_app


async def test_reset_wipes_everything_and_seeds_what_it_was_given(client: httpx.AsyncClient, reset) -> None:
    # Leave an account behind first, so that the wipe is observable rather than assumed.
    await client.post("/api/auth/register", json={"email": "doomed@example.com", "password": "hunter22"})

    seeded = await reset(
        users=[{"email": "seeded@example.com", "password": "hunter22"}],
        memos=[{"owner": "seeded@example.com", "title": "Seeded", "body": "", "pinned": True}],
    )

    assert [user["email"] for user in seeded["users"]] == ["seeded@example.com"]
    assert [(memo["title"], memo["pinned"]) for memo in seeded["memos"]] == [("Seeded", True)]
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_a_seeded_account_can_sign_in(client: httpx.AsyncClient, reset) -> None:
    await reset(users=[{"email": "seeded@example.com", "password": "hunter22"}])

    login = await client.post("/api/auth/login", json={"email": "seeded@example.com", "password": "hunter22"})

    assert login.status_code == 200
    assert (await client.get("/api/auth/me")).status_code == 200


async def test_reset_rejects_a_memo_whose_owner_was_not_seeded(
    client: httpx.AsyncClient,
    signed_in: dict,
) -> None:
    """Rejected before the wipe runs, so a typo in a fixture cannot leave the database
    empty and every subsequent test failing for the wrong reason."""
    response = await client.post(
        "/api/__test__/reset",
        json={
            "users": [{"email": signed_in["email"], "password": "hunter22"}],
            "memos": [{"owner": "typo@example.com", "title": "Orphan", "body": ""}],
        },
    )

    assert response.status_code == 422
    # The rejected reset left the existing session, and its account, alone.
    assert (await client.get("/api/auth/me")).status_code == 200


async def test_reset_rejects_duplicate_emails(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/__test__/reset",
        json={
            "users": [
                {"email": "a@example.com", "password": "hunter22"},
                {"email": "A@example.com", "password": "hunter22"},
            ]
        },
    )

    assert response.status_code == 422


async def test_reset_route_does_not_exist_outside_the_test_environment(settings: Settings) -> None:
    """The guard from docs/adr/0001. Verified by building an app in another environment
    rather than taken on trust: this route can wipe tables and needs no credentials."""
    app = create_app(settings.model_copy(update={"env": "dev"}))
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/__test__/reset")
    finally:
        await app.state.engine.dispose()

    assert response.status_code == 404
