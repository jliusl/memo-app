from datetime import timedelta

import anyio.to_thread
import bcrypt
import jwt

from .clock import utcnow
from .config import Settings

ALGORITHM = "HS256"
ACCESS_TOKEN_COOKIE = "access_token"

# bcrypt reads at most 72 bytes and silently ignores the rest, which would make two
# different long passwords compare equal. We reject them at the schema layer and
# truncate here as a second line of defence.
PASSWORD_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:PASSWORD_MAX_BYTES]


def _hash_sync(password: str, rounds: int) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt(rounds=rounds)).decode()


def _verify_sync(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(password), password_hash.encode())
    except ValueError:
        # A malformed hash in the database is a failed login, not a 500.
        return False


async def hash_password(password: str, *, rounds: int) -> str:
    # bcrypt is deliberately CPU-expensive; keep it off the event loop.
    return await anyio.to_thread.run_sync(_hash_sync, password, rounds)


async def verify_password(password: str, password_hash: str) -> bool:
    return await anyio.to_thread.run_sync(_verify_sync, password, password_hash)


def create_access_token(user_id: int, settings: Settings) -> str:
    now = utcnow()
    return jwt.encode(
        {
            # The JWT spec requires `sub` to be a string.
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str, settings: Settings) -> int | None:
    """Return the User id, or None for any token we should treat as absent."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None
