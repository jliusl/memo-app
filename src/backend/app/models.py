from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, MetaData, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .clock import utcnow

# Without a naming convention, constraint names are database-assigned and Alembic
# autogenerate reports phantom differences every time it runs. The names produced here
# are the ones spelled out in alembic/versions/0001_initial_schema.py.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def normalize_title(title: str | None) -> str | None:
    """A title made only of whitespace is no title at all."""
    if title is None:
        return None
    return title.strip() or None


def has_content(title: str | None, body: str) -> bool:
    """A Memo needs a title or a body; it is never empty. This mirrors the
    ck_memos_title_or_body constraint, and lives next to it so the two cannot drift."""
    return title is not None or body.strip() != ""


class User(Base):
    """An account that signs in with an email and a password, and owns Memos."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Stored lowercased; email comparison is case-insensitive in practice, and a
    # case-sensitive unique index would let Alice@x.com and alice@x.com coexist.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    # 60 bytes for bcrypt today, with room to switch algorithms without a migration.
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memos: Mapped[list["Memo"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class Memo(Base):
    """A single note owned by exactly one User, made of an optional title and a Markdown body."""

    __tablename__ = "memos"
    __table_args__ = (
        # A Memo with neither a title nor a body is not a concept in this context
        # (see CONTEXT.md). Enforced here as well as in the request schemas so that
        # a bad write from any path - including the test reset route - cannot land.
        CheckConstraint(
            "title IS NOT NULL OR btrim(body) <> ''",
            # Expands to ck_memos_title_or_body via NAMING_CONVENTION.
            name="title_or_body",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")

    # NULL means not pinned. A timestamp rather than a boolean, so that when several
    # Memos are pinned the most recently pinned one sorts first.
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Deliberately no `onupdate`: this is "when the content was last written", and the
    # router sets it only when the title or body actually changed. With `onupdate`, any
    # UPDATE of the row would move the Memo in the recency order - so pinning a Memo and
    # then unpinning it would teleport it to the top of the list without an edit.
    # See docs/adr/0002-an-edit-is-a-content-change.md.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped[User] = relationship(back_populates="memos")

    @hybrid_property
    def pinned(self) -> bool:
        return self.pinned_at is not None
