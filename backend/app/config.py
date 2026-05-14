"""Settings loaded from env. Pydantic v2 settings.

DB connection is built from individual fields (host/port/user/password/db)
rather than accepting a pre-formed DATABASE_URL. This avoids a class of bugs
where special characters in the password (e.g. '@', ':', '/', '#', '$') would
be silently mis-parsed when embedded in a URL by docker-compose interpolation.

The password is URL-quoted exactly once, here, before being assembled into
the SQLAlchemy URL. Postgres receives the same raw password value via its
own POSTGRES_PASSWORD env var, so the two sides are guaranteed to match.

DATABASE_URL is still accepted as an override for advanced/local scenarios.
"""
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- DB (individual fields — preferred) ---------------------------------
    POSTGRES_HOST:     str = "postgres"
    POSTGRES_PORT:     int = 5432
    POSTGRES_USER:     str = "rbi_user"
    POSTGRES_PASSWORD: str = "rbi_pass_demo_only"
    POSTGRES_DB:       str = "rbi_cms"

    # ---- DB URL (optional override) -----------------------------------------
    # If set, takes precedence over the individual fields above. Useful for
    # local dev pointing at an external DB, or for tests.
    DATABASE_URL_OVERRIDE: str | None = None

    # ---- API auth -----------------------------------------------------------
    RBI_API_KEY: str = "rbi_demo_token_change_me"

    # ---- Bank-side Crest endpoint -------------------------------------------
    CREST_BANK_BASE_URL: str = "http://host.docker.internal:8000"
    CREST_BANK_API_KEY:  str = "crest_test_sk_demo"
    CREST_BANK_AGENT_ID: str = "grievance-io-agent"

    # ---- Logging ------------------------------------------------------------
    LOG_LEVEL: str = "INFO"

    # -------------------------------------------------------------------------
    @property
    def DATABASE_URL(self) -> str:
        """Async SQLAlchemy URL with the password URL-quoted exactly once.

        Uses quote() with an empty safe set (every reserved char gets %-encoded,
        including '/', '@', ':', '+', etc.) — NOT quote_plus, which would
        encode spaces as '+' and create a + / space ambiguity that some URL
        parsers handle inconsistently.
        """
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        pw   = quote(self.POSTGRES_PASSWORD, safe="")
        user = quote(self.POSTGRES_USER,     safe="")
        return (
            f"postgresql+asyncpg://{user}:{pw}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
