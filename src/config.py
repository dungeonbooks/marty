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


PLACEHOLDER_API_KEY = "not-configured"  # noqa: S105


class Config:
    """Application configuration."""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./marty.db")

    # LLM (Neuralwatt, OpenAI-compatible)
    NEURALWATT_API_KEY: str = os.getenv("NEURALWATT_API_KEY", "")
    NEURALWATT_BASE_URL: str = os.getenv(
        "NEURALWATT_BASE_URL", "https://api.neuralwatt.com/v1"
    )
    # Pinned: the `glm-5.2` alias load-balances across backends. Measured over 12
    # identical requests it cost $0.003686 against $0.000644 pinned, ~5.7x.
    MARTY_MODEL: str = os.getenv("MARTY_MODEL", "glm-5.2-short")

    # GLM-5.2 defaults to `max` reasoning effort. Chat replies are 1-5 sentences,
    # so the extra thinking is billed as output for no benefit. The optimizer does
    # structured extraction off the hot path, where depth is worth the latency.
    MARTY_CHAT_REASONING_EFFORT: str = os.getenv(
        "MARTY_CHAT_REASONING_EFFORT", "minimal"
    )
    MARTY_OPTIMIZER_REASONING_EFFORT: str = os.getenv(
        "MARTY_OPTIMIZER_REASONING_EFFORT", "high"
    )
    MARTY_MAX_TOKENS: int = int(os.getenv("MARTY_MAX_TOKENS", "500"))
    MARTY_TEMPERATURE: float = float(os.getenv("MARTY_TEMPERATURE", "0.7"))

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
    def llm_api_key(cls) -> str:
        """The Neuralwatt key, or a placeholder that keeps construction working.

        The OpenAI SDK refuses to build a client without an api_key, and clients
        are constructed at import time, so an unset key would make the package
        unimportable rather than merely unusable. Requests with the placeholder
        are rejected by the API; startup validation catches it first in practice.
        """
        return cls.NEURALWATT_API_KEY or PLACEHOLDER_API_KEY

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
