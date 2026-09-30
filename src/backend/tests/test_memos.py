from datetime import UTC, datetime

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Memo

# Well before anything the API will produce, so ordering assertions do not depend on
# the resolution of the system clock.
BACKDATED = datetime(2020, 1, 1, tzinfo=UTC)

OTHER_ACCOUNT = {"email": "other@example.com", "password": "hunter22"}


async def _ids(client: httpx.AsyncClient, query: str = "") -> list[int]:
    response = await client.get(f"/api/memos{query}")
    assert response.status_code == 200, response.text
    return [memo["id"] for memo in response.json()]


async def test_the_api_requires_authentication(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/memos")).status_code == 401
    assert (await client.post("/api/memos", json={"title": "a", "body": ""})).status_code == 401


async def test_create_trims_the_title(client: httpx.AsyncClient, signed_in: dict) -> None:
    response = await client.post("/api/memos", json={"title": "  Groceries  ", "body": "milk"})

    assert response.status_code == 201
    assert response.json()["title"] == "Groceries"
    assert response.json()["pinned"] is False


async def test_create_accepts_a_body_without_a_title(client: httpx.AsyncClient, signed_in: dict) -> None:
    """Reaching for a pen means writing the body first; forcing a title would block that."""
    response = await client.post("/api/memos", json={"body": "call the dentist"})

    assert response.status_code == 201
    assert response.json()["title"] is None


async def test_create_rejects_a_memo_with_neither_title_nor_body(client: httpx.AsyncClient, signed_in: dict) -> None:
    assert (await client.post("/api/memos", json={})).status_code == 422
    assert (await client.post("/api/memos", json={"title": "   ", "body": ""})).status_code == 422


async def test_a_pinned_memo_outranks_a_more_recently_edited_one(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
) -> None:
    """The whole point of pinning: it beats recency."""
    pinned = await create_memo(title="Pinned", body="")
    edited = await create_memo(title="Edited later", body="")
    await client.patch(f"/api/memos/{pinned['id']}", json={"pinned": True})
    await client.patch(f"/api/memos/{edited['id']}", json={"body": "edited much later"})

    assert await _ids(client) == [pinned["id"], edited["id"]]


async def test_pinned_memos_are_ordered_by_most_recently_pinned(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
    session: AsyncSession,
) -> None:
    first = await create_memo(title="First pinned", body="")
    second = await create_memo(title="Second pinned", body="")
    await create_memo(title="Never pinned", body="")

    await client.patch(f"/api/memos/{first['id']}", json={"pinned": True})
    await client.patch(f"/api/memos/{second['id']}", json={"pinned": True})

    # The two pins above may land in the same clock tick, so the order between them is
    # fixed explicitly rather than left to the machine's timer resolution.
    await session.execute(
        update(Memo).where(Memo.id == second["id"]).values(pinned_at=datetime(2020, 6, 1, tzinfo=UTC))
    )
    await session.commit()

    listed = (await client.get("/api/memos")).json()
    assert [memo["id"] for memo in listed[:2]] == [second["id"], first["id"]]


async def test_repinning_an_already_pinned_memo_does_not_reorder_it(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
    session: AsyncSession,
) -> None:
    """Otherwise a repeated PATCH would silently reshuffle the pinned list."""
    older = await create_memo(title="Older pin", body="")
    newer = await create_memo(title="Newer pin", body="")

    await client.patch(f"/api/memos/{older['id']}", json={"pinned": True})
    await client.patch(f"/api/memos/{newer['id']}", json={"pinned": True})
    await session.execute(update(Memo).where(Memo.id == older["id"]).values(pinned_at=datetime(2020, 6, 1, tzinfo=UTC)))
    await session.commit()

    await client.patch(f"/api/memos/{older['id']}", json={"pinned": True})

    listed = (await client.get("/api/memos")).json()
    assert [memo["id"] for memo in listed[:2]] == [newer["id"], older["id"]]


async def test_unpinning_returns_a_memo_to_the_ordinary_ordering(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
) -> None:
    pinned = await create_memo(title="Pinned", body="")
    ordinary = await create_memo(title="Ordinary", body="")
    await client.patch(f"/api/memos/{pinned['id']}", json={"pinned": True})
    assert await _ids(client) == [pinned["id"], ordinary["id"]]

    await client.patch(f"/api/memos/{pinned['id']}", json={"pinned": False})

    # `ordinary` was written after `pinned`, so it now leads on recency.
    assert await _ids(client) == [ordinary["id"], pinned["id"]]


async def test_identical_timestamps_fall_back_to_the_id_descending(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
    session: AsyncSession,
) -> None:
    """Without this tie-break Postgres may return equal-timestamped rows in any order,
    which is exactly how a list-order assertion becomes intermittently flaky."""
    first = await create_memo(title="One", body="")
    second = await create_memo(title="Two", body="")
    third = await create_memo(title="Three", body="")

    await session.execute(update(Memo).values(updated_at=BACKDATED))
    await session.commit()

    assert await _ids(client) == [third["id"], second["id"], first["id"]]


async def test_editing_a_memo_moves_it_to_the_top(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
    session: AsyncSession,
) -> None:
    first = await create_memo(title="One", body="")
    second = await create_memo(title="Two", body="")
    await session.execute(update(Memo).values(updated_at=BACKDATED))
    await session.commit()

    await client.patch(f"/api/memos/{first['id']}", json={"body": "now with more text"})

    assert await _ids(client) == [first["id"], second["id"]]


async def test_search_matches_title_and_body(client: httpx.AsyncClient, signed_in: dict, create_memo) -> None:
    by_title = await create_memo(title="Buy milk", body="")
    by_body = await create_memo(title="Errands", body="also buy milk")
    await create_memo(title="Unrelated", body="nothing to see")

    assert sorted(await _ids(client, "?q=milk")) == sorted([by_title["id"], by_body["id"]])


async def test_search_is_case_insensitive(client: httpx.AsyncClient, signed_in: dict, create_memo) -> None:
    memo = await create_memo(title="Buy Milk", body="")

    assert await _ids(client, "?q=milk") == [memo["id"]]


async def test_search_treats_a_percent_sign_as_a_literal(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
) -> None:
    """Unescaped, '%' is a LIKE wildcard and would match every memo the caller owns."""
    literal = await create_memo(title="100% done", body="")
    await create_memo(title="plain", body="")

    assert await _ids(client, "?q=%25") == [literal["id"]]


async def test_search_only_sees_the_callers_own_memos(client: httpx.AsyncClient, signed_in: dict, create_memo) -> None:
    await create_memo(title="secret plans", body="")
    client.cookies.clear()
    await client.post("/api/auth/register", json=OTHER_ACCOUNT)

    assert await _ids(client, "?q=secret") == []


async def test_another_users_memo_is_not_found(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
) -> None:
    """404 rather than 403: a 403 would confirm that the Memo exists."""
    memo = await create_memo(title="private", body="")
    client.cookies.clear()
    await client.post("/api/auth/register", json=OTHER_ACCOUNT)

    assert (await client.get(f"/api/memos/{memo['id']}")).status_code == 404
    assert (await client.patch(f"/api/memos/{memo['id']}", json={"title": "mine now"})).status_code == 404
    assert (await client.delete(f"/api/memos/{memo['id']}")).status_code == 404


async def test_another_user_cannot_see_the_memo_in_a_list(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
) -> None:
    await create_memo(title="private", body="")
    client.cookies.clear()
    await client.post("/api/auth/register", json=OTHER_ACCOUNT)

    assert await _ids(client) == []


async def test_patch_can_clear_a_title_when_a_body_remains(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
) -> None:
    memo = await create_memo(title="Title", body="body text")

    response = await client.patch(f"/api/memos/{memo['id']}", json={"title": None})

    assert response.status_code == 200
    assert response.json()["title"] is None
    assert response.json()["body"] == "body text"


async def test_patch_rejects_emptying_the_last_remaining_content(
    client: httpx.AsyncClient,
    signed_in: dict,
    create_memo,
) -> None:
    memo = await create_memo(title="Only a title", body="")

    response = await client.patch(f"/api/memos/{memo['id']}", json={"title": None})

    assert response.status_code == 422


async def test_patch_rejects_a_null_body(client: httpx.AsyncClient, signed_in: dict, create_memo) -> None:
    memo = await create_memo(title="Title", body="body")

    response = await client.patch(f"/api/memos/{memo['id']}", json={"body": None})

    assert response.status_code == 422


async def test_patch_leaves_untouched_fields_alone(client: httpx.AsyncClient, signed_in: dict, create_memo) -> None:
    memo = await create_memo(title="Title", body="body")

    response = await client.patch(f"/api/memos/{memo['id']}", json={"pinned": True})

    assert response.status_code == 200
    assert response.json()["title"] == "Title"
    assert response.json()["body"] == "body"
    assert response.json()["pinned"] is True


async def test_delete_removes_the_memo_permanently(client: httpx.AsyncClient, signed_in: dict, create_memo) -> None:
    memo = await create_memo(title="Temporary", body="")

    assert (await client.delete(f"/api/memos/{memo['id']}")).status_code == 204

    assert (await client.get(f"/api/memos/{memo['id']}")).status_code == 404
    assert await _ids(client) == []


async def test_list_paginates(client: httpx.AsyncClient, signed_in: dict, create_memo) -> None:
    created = [await create_memo(title=f"Memo {n}", body="") for n in range(5)]

    page = (await client.get("/api/memos?limit=2&offset=1")).json()

    assert [memo["id"] for memo in page] == [created[3]["id"], created[2]["id"]]


async def test_list_rejects_an_absurd_page_size(client: httpx.AsyncClient, signed_in: dict) -> None:
    assert (await client.get("/api/memos?limit=1000")).status_code == 422
