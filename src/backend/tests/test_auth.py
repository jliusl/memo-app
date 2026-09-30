import httpx

from app.security import PASSWORD_MAX_BYTES


async def test_register_signs_the_new_user_in(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/auth/register", json={"email": "New@Example.com", "password": "hunter22"})

    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


async def test_register_lowercases_the_email_so_casing_cannot_create_a_second_account(
    client: httpx.AsyncClient,
) -> None:
    await client.post("/api/auth/register", json={"email": "owner@example.com", "password": "hunter22"})
    client.cookies.clear()

    response = await client.post("/api/auth/register", json={"email": "OWNER@example.com", "password": "hunter22"})

    assert response.status_code == 409


async def test_register_rejects_a_password_shorter_than_eight_characters(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/auth/register", json={"email": "a@example.com", "password": "short"})

    assert response.status_code == 422


async def test_register_rejects_a_password_longer_than_bcrypt_can_read(client: httpx.AsyncClient) -> None:
    """bcrypt ignores everything past 72 bytes. Accepting a longer password would make
    two different passwords interchangeable."""
    too_long = "a" * (PASSWORD_MAX_BYTES + 1)

    response = await client.post("/api/auth/register", json={"email": "a@example.com", "password": too_long})

    assert response.status_code == 422


async def test_the_session_cookie_is_not_readable_by_javascript(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/auth/register", json={"email": "a@example.com", "password": "hunter22"})

    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


async def test_login_rejects_a_wrong_password(client: httpx.AsyncClient) -> None:
    await client.post("/api/auth/register", json={"email": "a@example.com", "password": "hunter22"})
    client.cookies.clear()

    response = await client.post("/api/auth/login", json={"email": "a@example.com", "password": "hunter23"})

    assert response.status_code == 401


async def test_login_gives_the_same_answer_for_an_unknown_account(client: httpx.AsyncClient) -> None:
    """A different message here would turn login into an account-existence oracle."""
    unknown = await client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "hunter22"})
    await client.post("/api/auth/register", json={"email": "a@example.com", "password": "hunter22"})
    client.cookies.clear()
    wrong = await client.post("/api/auth/login", json={"email": "a@example.com", "password": "hunter23"})

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


async def test_login_then_logout_round_trip(client: httpx.AsyncClient) -> None:
    await client.post("/api/auth/register", json={"email": "a@example.com", "password": "hunter22"})
    client.cookies.clear()

    assert (
        await client.post("/api/auth/login", json={"email": "a@example.com", "password": "hunter22"})
    ).status_code == 200
    assert (await client.get("/api/auth/me")).status_code == 200

    assert (await client.post("/api/auth/logout")).status_code == 204
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_me_without_a_cookie_is_unauthorized(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_a_tampered_token_is_rejected(client: httpx.AsyncClient) -> None:
    await client.post("/api/auth/register", json={"email": "a@example.com", "password": "hunter22"})
    client.cookies.set("access_token", "not.a.jwt")

    assert (await client.get("/api/auth/me")).status_code == 401


async def test_a_token_for_a_deleted_account_is_treated_as_signed_out(client: httpx.AsyncClient) -> None:
    """The cookie stays valid but the account is gone; that is a stale session, not a
    crash and not a 404 about a User the caller never named."""
    await client.post("/api/auth/register", json={"email": "a@example.com", "password": "hunter22"})

    await client.post("/api/__test__/reset")

    assert (await client.get("/api/auth/me")).status_code == 401
