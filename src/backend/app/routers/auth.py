from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from ..config import Settings
from ..deps import CurrentUser, SessionDep
from ..models import User
from ..schemas import LoginRequest, RegisterRequest, UserRead
from ..security import ACCESS_TOKEN_COOKIE, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookie(response: Response, token: str, settings: Settings) -> None:
    """The token goes in an httpOnly cookie rather than somewhere JavaScript can read,
    which keeps it out of reach of an XSS payload. `SameSite=Lax` is enough here
    because the SPA and the API are same-origin (the dev server proxies /api)."""
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
        max_age=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: SessionDep,
) -> User:
    settings: Settings = request.app.state.settings

    if await session.scalar(select(User.id).where(User.email == payload.email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=payload.email,
        password_hash=await hash_password(payload.password, rounds=settings.bcrypt_rounds),
    )
    session.add(user)
    await session.commit()

    _set_auth_cookie(response, create_access_token(user.id, settings), settings)
    return user


@router.post("/login", response_model=UserRead)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
) -> User:
    settings: Settings = request.app.state.settings

    user = await session.scalar(select(User).where(User.email == payload.email))
    # One message for both "no such account" and "wrong password": telling them apart
    # would turn this endpoint into an account-existence oracle.
    if user is None or not await verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    _set_auth_cookie(response, create_access_token(user.id, settings), settings)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user
