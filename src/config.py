"""Configuration management for Marty application."""

import base64
import binascii
import json
import os
from datetime import UTC, datetime

# Load .env file for local development (if it exists)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv not installed, continue without .env loading
    pass


class Config:
    """Application configuration."""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./marty.db")

    # Hardcover API Configuration
    HARDCOVER_API_TOKEN: str | None = os.getenv("HARDCOVER_API_TOKEN")
    HARDCOVER_API_URL: str = os.getenv(
        "HARDCOVER_API_URL", "https://api.hardcover.app/v1/graphql"
    )

    # Deprecated: expiry now comes from the token's own `exp` claim. Kept only so
    # existing deployments that still set it do not break on import.
    HARDCOVER_TOKEN_EXPIRY: str | None = os.getenv("HARDCOVER_TOKEN_EXPIRY")

    # Your Bookstore Integration (to be added)
    BOOKSTORE_API_URL: str | None = os.getenv("BOOKSTORE_API_URL")
    BOOKSTORE_API_KEY: str | None = os.getenv("BOOKSTORE_API_KEY")

    # Bookshop.org Affiliate Integration
    BOOKSHOP_AFFILIATE_ID: str = os.getenv("BOOKSHOP_AFFILIATE_ID", "108216")

    # Redis
    REDIS_URL: str | None = os.getenv("REDIS_URL")

    # RSS Feeds
    RPG_NEWS_CHANNEL_ID: str | None = os.getenv("RPG_NEWS_CHANNEL_ID")

    # Conversation
    CONVERSATION_HISTORY_LIMIT: int = int(os.getenv("CONVERSATION_HISTORY_LIMIT", "10"))

    @classmethod
    def hardcover_token_expiry(cls) -> datetime | None:
        """Read the expiry from the token's own `exp` claim.

        Hardcover issues a JWT, so it already carries its expiry. Reading it
        beats HARDCOVER_TOKEN_EXPIRY, which is a hand-maintained copy that goes
        stale on every rotation and then reports a working token as expired.
        """
        if not cls.HARDCOVER_API_TOKEN:
            return None

        token = cls.HARDCOVER_API_TOKEN.removeprefix("Bearer ").strip()
        try:
            payload = token.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))
            if not isinstance(claims, dict):
                return None
            exp = claims.get("exp")
            if exp is None:
                return None
            return datetime.fromtimestamp(int(exp), tz=UTC)
        except (
            IndexError,
            TypeError,
            ValueError,
            OverflowError,
            OSError,
            binascii.Error,
        ):
            return None

    @classmethod
    def validate_hardcover_setup(cls) -> bool:
        """Check a Hardcover token is present, and unexpired when we can tell.

        An opaque or unparseable token passes: we have no expiry to enforce, so
        the API is the only real judge. Only a token whose own `exp` claim has
        passed is reported invalid.
        """
        if not cls.HARDCOVER_API_TOKEN:
            return False

        expiry = cls.hardcover_token_expiry()
        if expiry is None:
            # Opaque or unparseable token - let the API be the judge.
            return True

        return datetime.now(UTC) < expiry

    @classmethod
    def get_hardcover_headers(cls) -> dict[str, str]:
        """Get headers for Hardcover API requests."""
        if not cls.HARDCOVER_API_TOKEN:
            raise ValueError("Hardcover API token not configured")

        return {
            "Authorization": cls.HARDCOVER_API_TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "Marty-Bot/1.0 (Book recommendation bot)",
        }


# Global config instance
config = Config()
