from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/backend/app/config.py -> app -> backend -> src -> repository root.
# The single .env at the repository root serves both docker-compose and this app,
# so credentials are declared exactly once.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["dev", "test", "prod"] = "dev"
    secret_key: str = "dev-only-not-a-real-secret"
    access_token_expire_minutes: int = 60
    # Lowered by the test suite: at 12 rounds every seeded account costs ~300ms.
    bcrypt_rounds: int = 12

    postgres_user: str = "memo"
    postgres_password: str = "memo"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "memo_dev"
    postgres_test_db: str = "memo_test"

    def database_url(self, *, test: bool = False) -> str:
        """Build the SQLAlchemy URL. Credentials are percent-encoded: a password
        containing '@' or '/' would otherwise silently corrupt the URL."""
        database = self.postgres_test_db if test else self.postgres_db
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        return f"postgresql+psycopg://{user}:{password}@{self.postgres_host}:{self.postgres_port}/{database}"

    @property
    def is_test(self) -> bool:
        """True only in the test environment, which is the single condition that
        registers the test-only reset route. See docs/adr/0001."""
        return self.env == "test"

    @property
    def cookie_secure(self) -> bool:
        # Must stay False for the plain-http localhost used by dev and CI.
        return self.env == "prod"
