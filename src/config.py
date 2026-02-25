"""Configuration management for Marty application."""

import os
from datetime import datetime

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

    # Sinch SMS Configuration
    SINCH_SERVICE_PLAN_ID: str | None = os.getenv("SINCH_SERVICE_PLAN_ID")
    SINCH_API_TOKEN: str | None = os.getenv("SINCH_API_TOKEN")
    SINCH_API_URL: str = os.getenv("SINCH_API_URL", "https://us.sms.api.sinch.com")

    # Hardcover API Configuration
    HARDCOVER_API_TOKEN: str | None = os.getenv("HARDCOVER_API_TOKEN")
    HARDCOVER_API_URL: str = os.getenv(
        "HARDCOVER_API_URL", "https://api.hardcover.app/v1/graphql"
    )

    # Hardcover Token Expiry: 7/11/2026, 3:42:27 PM
    HARDCOVER_TOKEN_EXPIRY: str = os.getenv(
        "HARDCOVER_TOKEN_EXPIRY", "2026-07-11T15:42:27"
    )

    # Your Bookstore Integration (to be added)
    BOOKSTORE_API_URL: str | None = os.getenv("BOOKSTORE_API_URL")
    BOOKSTORE_API_KEY: str | None = os.getenv("BOOKSTORE_API_KEY")

    # Bookshop.org Affiliate Integration
    BOOKSHOP_AFFILIATE_ID: str = os.getenv("BOOKSHOP_AFFILIATE_ID", "108216")

    # SMS Configuration
    SMS_MULTI_MESSAGE_ENABLED: bool = (
        os.getenv("SMS_MULTI_MESSAGE_ENABLED", "true").lower() == "true"
    )
    SMS_MESSAGE_DELAY: float = float(
        os.getenv("SMS_MESSAGE_DELAY", "0.5")
    )  # seconds between messages
    DEFAULT_PHONE_REGION: str = os.getenv("DEFAULT_PHONE_REGION", "US")

    # 10DLC Compliance Messages
    STOP_CONFIRMATION_MESSAGE: str = os.getenv(
        "STOP_CONFIRMATION_MESSAGE",
        "Dungeon Books: You have unsubscribed and will no longer receive messages. Reply HELP for help.",
    )
    HELP_RESPONSE_MESSAGE: str = os.getenv(
        "HELP_RESPONSE_MESSAGE",
        "Dungeon Books: For help, contact hello@dungeonbooks.com or reply STOP to unsubscribe. Msg&data rates may apply.",
    )

    @classmethod
    def validate_hardcover_setup(cls) -> bool:
        """Validate that Hardcover API is properly configured."""
        if not cls.HARDCOVER_API_TOKEN:
            return False

        # Check if token is expired
        try:
            expiry = datetime.fromisoformat(
                cls.HARDCOVER_TOKEN_EXPIRY.replace("Z", "+00:00")
            )
            if datetime.now() >= expiry:
                return False
        except ValueError:
            # If we can't parse the expiry date, assume it's valid for now
            pass

        return True

    @classmethod
    def get_hardcover_headers(cls) -> dict[str, str]:
        """Get headers for Hardcover API requests."""
        if not cls.HARDCOVER_API_TOKEN:
            raise ValueError("Hardcover API token not configured")

        return {
            "Authorization": cls.HARDCOVER_API_TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "Marty-SMS-Bot/1.0 (Book recommendation bot)",
        }


# Global config instance
config = Config()
