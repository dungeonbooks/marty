"""
BookEnricher Tool - Enriches AI responses with validated book data.

This tool processes AI responses to extract book mentions, validates them
against the Hardcover API, and stores verified books in the database.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from src.database import (
    Book,
    BookCreate,
    get_db_session,
)
from src.tools.base import BaseTool, ToolResult
from src.tools.external.bookshop import BookshopClient
from src.tools.external.hardcover import HardcoverAPIError, HardcoverTool

logger = structlog.get_logger(__name__)


@dataclass
class BookMention:
    """Represents a book mentioned in AI response."""

    title: str
    author: str | None = None
    isbn: str | None = None
    confidence: float = 0.0
    context: str = ""
    message_id: str = ""
    validated: bool = False
    hardcover_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnrichedResponse:
    """AI response enriched with validated book data."""

    original_response: str
    book_mentions: list[BookMention]
    validated_books: list[dict[str, Any]]
    enrichment_metadata: dict[str, Any] = field(default_factory=dict)


class BookEnricherTool(BaseTool):
    """
    Enriches AI responses with validated book data.

    This tool processes AI responses to:
    1. Extract book mentions using Claude AI
    2. Validate books against Hardcover API
    3. Store validated books in database
    4. Prepare data for SMS cards and recommendations
    """

    def __init__(self, hardcover_tool: HardcoverTool | None = None):
        super().__init__()
        self.hardcover_tool = hardcover_tool or HardcoverTool()
        self.bookshop_client = BookshopClient()
        # Simple but effective ISBN pattern for ISBN-10 and ISBN-13
        self.isbn_pattern = re.compile(
            r"(?:ISBN[-:\s]*)?((?:97[89][-\s]?)?(?:\d[-\s]?){9,12}\d)", re.IGNORECASE
        )

    @property
    def name(self) -> str:
        return "book_enricher"

    @property
    def description(self) -> str:
        return (
            "Enriches AI responses with validated book data. "
            "Extracts book mentions from AI responses, validates them against "
            "the Hardcover API, and stores verified books in the database."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "ai_response": {
                "type": "string",
                "description": "The AI-generated response text to enrich",
            },
            "conversation_id": {
                "type": "string",
                "description": "ID of the conversation",
            },
            "message_id": {"type": "string", "description": "ID of the message"},
        }

    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters."""
        required_fields = ["ai_response", "conversation_id", "message_id"]
        return all(field in kwargs and kwargs[field] for field in required_fields)

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the book enrichment tool."""
        if not self.validate_input(**kwargs):
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameters: ai_response, conversation_id, message_id",
            )

        try:
            ai_response = kwargs["ai_response"]
            conversation_id = kwargs["conversation_id"]
            message_id = kwargs["message_id"]

            enriched_response = await self._enrich_response(
                ai_response, conversation_id, message_id
            )

            return ToolResult(
                success=True,
                data=enriched_response,
                metadata={
                    "books_found": len(enriched_response.book_mentions),
                    "books_validated": len(enriched_response.validated_books),
                    "processed_at": datetime.now(UTC).isoformat(),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                metadata={"error_type": type(e).__name__},
            )

    async def _enrich_response(
        self, ai_response: str, conversation_id: str, message_id: str
    ) -> EnrichedResponse:
        """
        Enrich an AI response with validated book data.

        Args:
            ai_response: The AI-generated response text
            conversation_id: ID of the conversation
            message_id: ID of the message

        Returns:
            EnrichedResponse with validated book data
        """
        logger.info(f"Enriching response for conversation {conversation_id}")

        # Extract book mentions from AI response
        book_mentions = await self._extract_book_mentions(ai_response, message_id)

        # Validate books against Hardcover API
        validated_books = []
        for mention in book_mentions:
            try:
                validated_book = await self._validate_book(mention)
                if validated_book:
                    mention.validated = True
                    mention.hardcover_id = str(validated_book.get("id"))
                    mention.metadata = validated_book
                    validated_books.append(validated_book)

                    # Store in database
                    await self._store_book(validated_book)

            except Exception as e:
                logger.warning(f"Failed to validate book '{mention.title}': {e}")
                # Keep unvalidated mention for context

        return EnrichedResponse(
            original_response=ai_response,
            book_mentions=book_mentions,
            validated_books=validated_books,
            enrichment_metadata={
                "conversation_id": conversation_id,
                "message_id": message_id,
                "processed_at": datetime.now(UTC).isoformat(),
                "mentions_found": len(book_mentions),
                "books_validated": len(validated_books),
            },
        )

    async def _extract_book_mentions(
        self, text: str, message_id: str
    ) -> list[BookMention]:
        """Extract book mentions from AI response text."""
        mentions = []

        # Quick ISBN detection
        isbn_matches = self.isbn_pattern.findall(text)
        for isbn in isbn_matches:
            mentions.append(
                BookMention(
                    title=isbn.strip(),
                    isbn=isbn.strip(),
                    confidence=0.9,
                    context=text,
                    message_id=message_id,
                )
            )

        # Use simple regex patterns for book extraction (avoid recursive AI calls)
        # Look for patterns like "Book Title" by Author or **Book Title** by Author
        import re

        # Pattern for "Book Title" by Author
        book_pattern = r'["""]([^"""]+)["""]\s+by\s+([^,.\n]+)'
        matches = re.findall(book_pattern, text, re.IGNORECASE)
        for title, author in matches:
            mentions.append(
                BookMention(
                    title=title.strip(),
                    author=author.strip(),
                    confidence=0.8,
                    context=text,
                    message_id=message_id,
                )
            )

        # Pattern for **Book Title** by Author (Discord formatting)
        bold_pattern = r"\*\*([^*]+)\*\*\s+by\s+([^,.\n]+)"
        matches = re.findall(bold_pattern, text, re.IGNORECASE)
        for title, author in matches:
            mentions.append(
                BookMention(
                    title=title.strip(),
                    author=author.strip(),
                    confidence=0.8,
                    context=text,
                    message_id=message_id,
                )
            )

        # Pattern for just "Book Title" (without author)
        title_pattern = r'["""]([^"""]+)["""]'
        matches = re.findall(title_pattern, text, re.IGNORECASE)
        for title in matches:
            # Skip if we already found this title with an author
            if not any(m.title == title.strip() for m in mentions):
                mentions.append(
                    BookMention(
                        title=title.strip(),
                        author=None,
                        confidence=0.6,
                        context=text,
                        message_id=message_id,
                    )
                )

        # Pattern for **Book Title** (Discord formatting without author)
        bold_title_pattern = r"\*\*([^*]+)\*\*"
        matches = re.findall(bold_title_pattern, text, re.IGNORECASE)
        for title in matches:
            # Skip if we already found this title with an author
            if not any(m.title == title.strip() for m in mentions):
                mentions.append(
                    BookMention(
                        title=title.strip(),
                        author=None,
                        confidence=0.6,
                        context=text,
                        message_id=message_id,
                    )
                )

        return mentions

    async def _validate_book(self, mention: BookMention) -> dict[str, Any] | None:
        """Validate a book mention against Hardcover API."""
        try:
            # Search for the book
            search_query = f"{mention.title}"
            if mention.author:
                search_query += f" {mention.author}"

            # Use the HardcoverTool to search for books
            result = await self.hardcover_tool.execute(
                action="search_books", query=search_query, limit=3
            )

            if not result.success:
                logger.error(f"Failed to search books: {result.error}")
                return None

            books = result.data

            if not books:
                logger.debug(f"No books found for: {search_query}")
                return None

            # Find the best match
            best_match = self._find_best_match(mention, books)
            if best_match:
                logger.info(f"Validated book: {best_match.get('title')}")
                return best_match

            return None

        except HardcoverAPIError as e:
            logger.error(f"Hardcover API error for '{mention.title}': {e}")
            return None

    def _find_best_match(
        self, mention: BookMention, books: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Find the best matching book from search results."""
        if not books:
            return None

        # Simple matching logic - can be enhanced
        for book in books:
            book_title = book.get("title", "").lower()
            mention_title = mention.title.lower()

            # Exact match
            if book_title == mention_title:
                return book

            # Partial match (title contains mention or vice versa)
            if mention_title in book_title or book_title in mention_title:
                # Check author if available
                if mention.author:
                    authors = book.get("authors", [])
                    if authors:
                        book_author = authors[0].get("name", "").lower()
                        if mention.author.lower() in book_author:
                            return book
                else:
                    return book

        # If no good match found, return the first book as fallback
        return books[0]

    async def _store_book(self, book_data: dict[str, Any]) -> None:
        """Store validated book in database."""
        try:
            async with get_db_session() as session:
                # Check if book already exists
                from sqlalchemy import select

                hardcover_id = str(book_data.get("id"))
                result = await session.execute(
                    select(Book).where(Book.hardcover_id == hardcover_id)
                )
                existing_book = result.scalars().first()

                if existing_book:
                    logger.debug(f"Book already exists: {existing_book.title}")
                    return

                # Resolve bookshop.org URL via ISBN validation
                bookshop_url = await self.bookshop_client.resolve_link(
                    book_data.get("editions", []),
                    book_data.get("title", ""),
                )

                # Create new book
                book_create = BookCreate(
                    title=book_data.get("title", ""),
                    author=book_data.get("authors", [{}])[0].get("name")
                    if book_data.get("authors")
                    else None,
                    description=book_data.get("description"),
                    hardcover_id=hardcover_id,
                    isbn=book_data.get("isbn"),
                    publisher=book_data.get("publisher"),
                    page_count=book_data.get("pages"),
                    bookshop_url=bookshop_url,
                    price=None,  # Not available from Hardcover API
                    genre=None,  # Not available from Hardcover API
                    format=None,  # Not available from Hardcover API
                )

                db_book = Book(**book_create.model_dump())
                session.add(db_book)
                await session.commit()

                logger.info(f"Stored book: {db_book.title}")

        except Exception as e:
            logger.error(f"Failed to store book: {e}")
            raise

    async def close(self) -> None:
        """Close any resources."""
        if self.hardcover_tool:
            await self.hardcover_tool.close()
