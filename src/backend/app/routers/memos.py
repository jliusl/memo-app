from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import utcnow
from ..deps import CurrentUser, SessionDep
from ..models import Memo, has_content, normalize_title
from ..schemas import MemoCreate, MemoRead, MemoUpdate

router = APIRouter(prefix="/memos", tags=["memos"])


async def _get_owned_memo(session: AsyncSession, memo_id: int, owner_id: int) -> Memo:
    memo = await session.scalar(select(Memo).where(Memo.id == memo_id, Memo.owner_id == owner_id))
    if memo is None:
        # 404 rather than 403 for someone else's Memo: a 403 would confirm that the
        # Memo exists, which is information the caller has not earned.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Memo not found")
    return memo


@router.get("", response_model=list[MemoRead])
async def list_memos(
    user: CurrentUser,
    session: SessionDep,
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Memo]:
    statement = select(Memo).where(Memo.owner_id == user.id)

    if q is not None and q.strip():
        needle = q.strip()
        # autoescape so that searching for '%' looks for a literal '%' instead of
        # matching every Memo the caller owns.
        statement = statement.where(
            or_(
                Memo.title.icontains(needle, autoescape=True),
                Memo.body.icontains(needle, autoescape=True),
            )
        )

    statement = (
        statement.order_by(
            # Pinned Memos first: `pinned_at IS NULL` is False for a pinned row, and False
            # sorts before True. Within each group, most recently pinned, then most
            # recently edited.
            Memo.pinned_at.is_(None),
            Memo.pinned_at.desc(),
            Memo.updated_at.desc(),
            # This tie-break is load-bearing, not decoration: two Memos written within the
            # same clock tick would otherwise come back in an unspecified order, and E2E
            # assertions about list order would fail intermittently.
            Memo.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    return list(await session.scalars(statement))


@router.post("", response_model=MemoRead, status_code=status.HTTP_201_CREATED)
async def create_memo(payload: MemoCreate, user: CurrentUser, session: SessionDep) -> Memo:
    memo = Memo(
        owner_id=user.id,
        title=payload.title,
        body=payload.body,
        pinned_at=utcnow() if payload.pinned else None,
    )
    session.add(memo)
    await session.commit()
    return memo


@router.get("/{memo_id}", response_model=MemoRead)
async def get_memo(memo_id: int, user: CurrentUser, session: SessionDep) -> Memo:
    return await _get_owned_memo(session, memo_id, user.id)


@router.patch("/{memo_id}", response_model=MemoRead)
async def update_memo(memo_id: int, payload: MemoUpdate, user: CurrentUser, session: SessionDep) -> Memo:
    memo = await _get_owned_memo(session, memo_id, user.id)
    data = payload.model_dump(exclude_unset=True)

    if "body" in data and data["body"] is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "body cannot be null")

    # `exclude_unset` left out the fields the caller did not send, so a plain default
    # means "keep what is stored"; an explicit null arrives as None and was handled above.
    title = data.get("title", memo.title)
    body = data.get("body", memo.body)

    # Validated against the values that are about to be written, and before anything is
    # assigned, so that a rejected PATCH leaves the session untouched.
    if not has_content(title, body):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "a memo needs a title or a body")

    memo.title = normalize_title(title)
    memo.body = body

    if data.get("pinned") is not None:
        if data["pinned"]:
            # Re-pinning an already pinned Memo is deliberately a no-op, so a repeated
            # PATCH cannot silently reshuffle the pinned order.
            if memo.pinned_at is None:
                memo.pinned_at = utcnow()
        else:
            memo.pinned_at = None

    await session.commit()
    return memo


@router.delete("/{memo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memo(memo_id: int, user: CurrentUser, session: SessionDep) -> None:
    # Permanent: this context has no recycle bin and no archive. See CONTEXT.md.
    memo = await _get_owned_memo(session, memo_id, user.id)
    await session.delete(memo)
    await session.commit()
