"""The test-only reset route.

Registered only when ENV=test (see main.create_app and docs/adr/0001), and deliberately
unauthenticated so a suite can reset the database before it has a session. It exists so
that every test starts from a known state without replaying the whole registration flow
over HTTP, which would make setup time grow with the size of the suite.
"""

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import text

from ..clock import utcnow
from ..deps import SessionDep
from ..models import Memo, User
from ..schemas import MemoRead, ResetRequest, ResetResult, UserRead
from ..security import hash_password

router = APIRouter(prefix="/__test__", tags=["test-support"])


@router.post("/reset", response_model=ResetResult)
async def reset(request: Request, session: SessionDep, payload: ResetRequest | None = None) -> ResetResult:
    payload = payload or ResetRequest()
    settings = request.app.state.settings

    emails = [spec.email for spec in payload.users]
    if len(set(emails)) != len(emails):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "duplicate email in users")

    unknown_owners = {spec.owner for spec in payload.memos} - set(emails)
    if unknown_owners:
        # Rejected up front, before the wipe, so a typo cannot leave the database empty.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"memo owner(s) not among the seeded users: {', '.join(sorted(unknown_owners))}",
        )

    # No `RESTART IDENTITY` on purpose, even though it would make ids start from 1 again on
    # every reset. A JWT identifies its subject by id, so recycling ids hands a caller's
    # still-valid cookie to whichever account is created next: a suite that asserts "the
    # deleted account is signed out" would see a 200 instead of a 401 and pass a genuinely
    # broken logout. Sequences are never reset outside this route, so letting them climb is
    # also the more faithful impression of production.
    await session.execute(text("TRUNCATE TABLE memos, users CASCADE"))

    users: dict[str, User] = {}
    for spec in payload.users:
        user = User(
            email=spec.email,
            password_hash=await hash_password(spec.password, rounds=settings.bcrypt_rounds),
        )
        session.add(user)
        users[spec.email] = user
    # Flush so the new Users have ids before the Memos reference them.
    await session.flush()

    memos: list[Memo] = []
    for spec in payload.memos:
        memo = Memo(
            owner_id=users[spec.owner].id,
            title=spec.title,
            body=spec.body,
            pinned_at=utcnow() if spec.pinned else None,
        )
        session.add(memo)
        memos.append(memo)

    await session.commit()

    return ResetResult(
        users=[UserRead.model_validate(user) for user in users.values()],
        memos=[MemoRead.model_validate(memo) for memo in memos],
    )
