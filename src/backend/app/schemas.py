from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .models import has_content, normalize_title
from .security import PASSWORD_MAX_BYTES

TITLE_MAX = 200
BODY_MAX = 100_000
PASSWORD_MIN = 8


class _EmailRequest(BaseModel):
    """Emails are stored and compared lowercased, so the unique index behaves the way
    people expect: Alice@example.com and alice@example.com are one account."""

    email: EmailStr

    @field_validator("email")
    @classmethod
    def _lowercase(cls, value: str) -> str:
        return value.lower()


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class RegisterRequest(_EmailRequest):
    password: str = Field(min_length=PASSWORD_MIN)

    @field_validator("password")
    @classmethod
    def _within_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode()) > PASSWORD_MAX_BYTES:
            raise ValueError(f"password must be at most {PASSWORD_MAX_BYTES} bytes")
        return value


class LoginRequest(_EmailRequest):
    # No length rules here: a password that cannot possibly be right is a 401, not a
    # validation error that would spell out the real constraints.
    password: str


class MemoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    body: str
    pinned: bool
    created_at: datetime
    updated_at: datetime


class MemoCreate(BaseModel):
    title: str | None = Field(default=None, max_length=TITLE_MAX)
    body: str = Field(default="", max_length=BODY_MAX)
    pinned: bool = False

    @field_validator("title")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return normalize_title(value)

    @model_validator(mode="after")
    def _require_content(self) -> "MemoCreate":
        if not has_content(self.title, self.body):
            raise ValueError("a memo needs a title or a body")
        return self


class MemoUpdate(BaseModel):
    """Every field is optional. Callers use `exclude_unset` to tell "not sent" apart
    from "explicitly set to null"."""

    title: str | None = Field(default=None, max_length=TITLE_MAX)
    body: str | None = Field(default=None, max_length=BODY_MAX)
    pinned: bool | None = None

    @field_validator("title")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return normalize_title(value)


class ResetUser(_EmailRequest):
    password: str = Field(min_length=PASSWORD_MIN)


class ResetMemo(BaseModel):
    owner: EmailStr
    title: str | None = Field(default=None, max_length=TITLE_MAX)
    body: str = Field(default="", max_length=BODY_MAX)
    pinned: bool = False

    @field_validator("owner")
    @classmethod
    def _lowercase(cls, value: str) -> str:
        return value.lower()

    @field_validator("title")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return normalize_title(value)


class ResetRequest(BaseModel):
    """Absent or empty means "wipe everything and seed nothing"."""

    users: list[ResetUser] = Field(default_factory=list)
    memos: list[ResetMemo] = Field(default_factory=list)


class ResetResult(BaseModel):
    users: list[UserRead]
    memos: list[MemoRead]
