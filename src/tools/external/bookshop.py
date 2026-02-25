"""
Bookshop.org Validation Client - Validates ISBNs and generates affiliate links.

Uses bookshop.org's undocumented /book/{isbn} endpoint to validate ISBNs
(308 = valid, 404 = invalid), enabling direct affiliate links instead of
search-based fallbacks.
"""

from urllib.parse import quote_plus

import httpx
import structlog

from src.config import config

logger = structlog.get_logger(__name__)


class BookshopClient:
    """Async client for validating ISBNs and generating bookshop.org links."""

    BASE_URL = "https://bookshop.org"
    IMAGE_CDN = "https://images-us.bookshop.org"
    REQUEST_TIMEOUT = 3.0  # seconds

    async def validate_isbn(self, isbn: str) -> bool:
        """Validate an ISBN against bookshop.org.

        Sends a HEAD request to /book/{isbn}. A 308 redirect means the ISBN
        is valid; anything else (404, timeout, error) means invalid.
        """
        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                response = await client.head(
                    f"{self.BASE_URL}/book/{isbn}",
                    follow_redirects=False,
                )
                return response.status_code == 308
        except httpx.TimeoutException:
            logger.warning("bookshop_isbn_validation_timeout", isbn=isbn)
            return False
        except httpx.HTTPError as e:
            logger.warning("bookshop_isbn_validation_error", isbn=isbn, error=str(e))
            return False

    async def validate_isbns(self, isbns: list[str]) -> str | None:
        """Try each ISBN sequentially, return the first valid one (or None)."""
        for isbn in isbns:
            if await self.validate_isbn(isbn):
                logger.info("bookshop_isbn_valid", isbn=isbn)
                return isbn
        return None

    @staticmethod
    def get_buy_url(isbn: str, affiliate_id: str | None = None) -> str:
        """Return the direct affiliate buy link for a valid ISBN."""
        aid = affiliate_id or config.BOOKSHOP_AFFILIATE_ID
        return f"https://bookshop.org/a/{aid}/{isbn}"

    @staticmethod
    def get_search_url(title: str, affiliate_id: str | None = None) -> str:
        """Return a search-based fallback link (current behavior)."""
        aid = affiliate_id or config.BOOKSHOP_AFFILIATE_ID
        search_query = quote_plus(title)
        return f"https://bookshop.org/search?keywords={search_query}&affiliate={aid}"

    @staticmethod
    def get_cover_url(isbn: str, height: int = 250) -> str:
        """Return the bookshop.org CDN cover image URL."""
        return f"https://images-us.bookshop.org/ingram/{isbn}.jpg?height={height}"

    async def resolve_link(
        self,
        editions: list[dict],
        title: str,
        affiliate_id: str | None = None,
    ) -> str:
        """Resolve the best bookshop.org link for a book.

        Extracts isbn_13 values from editions, validates each against
        bookshop.org, and returns a direct affiliate link for the first
        valid ISBN. Falls back to a search link if none are valid.
        """
        aid = affiliate_id or config.BOOKSHOP_AFFILIATE_ID

        # Extract ISBN-13s from editions
        isbns: list[str] = []
        for edition in editions:
            isbn = edition.get("isbn_13")
            if isbn:
                isbns.append(str(isbn))

        if isbns:
            try:
                valid_isbn = await self.validate_isbns(isbns)
                if valid_isbn:
                    return self.get_buy_url(valid_isbn, aid)
            except Exception as e:
                logger.warning(
                    "bookshop_resolve_link_error",
                    title=title,
                    error=str(e),
                )

        # Fallback to search URL
        return self.get_search_url(title, aid)
