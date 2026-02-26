"""
Hardcover API Tool - Provides access to Hardcover book data API.

This tool wraps the Hardcover API GraphQL client to provide book search,
book details, user recommendations, and trending books functionality.
"""

import asyncio
import re
import time
from datetime import datetime, timedelta
from typing import Any

import structlog
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportError, TransportQueryError

from src.config import config
from src.tools.base import BaseTool, ToolResult
from src.tools.external.bookshop import BookshopClient

logger = structlog.get_logger(__name__)

# Shared client instance for ISBN validation and link generation
bookshop_client = BookshopClient()


async def _resolve_bookshop_link(book: dict) -> None:
    """Resolve and attach a bookshop.org link to a book dict."""
    title = book.get("title", "")
    if title:
        book["bookshop_link"] = await bookshop_client.resolve_link(
            book.get("editions", []), title
        )


class HardcoverAPIError(Exception):
    """Base exception for Hardcover API errors."""

    pass


class HardcoverAuthError(HardcoverAPIError):
    """Authentication/Authorization errors."""

    pass


class HardcoverRateLimitError(HardcoverAPIError):
    """Rate limit exceeded (60 requests per minute)."""

    pass


class HardcoverTimeoutError(HardcoverAPIError):
    """Query timeout exceeded (30 seconds max)."""

    pass


class RateLimiter:
    """Simple rate limiter for API calls (60 requests per minute)."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait if necessary to respect rate limits."""
        async with self._lock:
            now = time.monotonic()
            # Remove old requests outside the window
            self.requests = [
                req_time
                for req_time in self.requests
                if now - req_time < self.window_seconds
            ]

            if len(self.requests) >= self.max_requests:
                # Calculate wait time
                oldest_request = self.requests[0]
                wait_time = self.window_seconds - (now - oldest_request)
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached, waiting {wait_time:.1f} seconds"
                    )
                    await asyncio.sleep(wait_time + 0.1)  # Add small buffer
                    # Recursive call to re-check
                    return await self.acquire()

            # Add current request
            self.requests.append(now)


class HardcoverTool(BaseTool):
    """
    Hardcover API Tool - Provides access to Hardcover book data API.

    This tool wraps the Hardcover API GraphQL client to provide:
    - Book search functionality
    - Book details retrieval
    - User recommendations
    - Trending books
    - Schema introspection
    """

    def __init__(
        self,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        rate_limit_max_requests: int = 60,
    ):
        super().__init__()
        if not config.HARDCOVER_API_TOKEN:
            raise HardcoverAuthError("Hardcover API token not configured")

        self.api_url = config.HARDCOVER_API_URL
        self.headers = config.get_hardcover_headers()
        self._client: Client | None = None
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit_max_requests, window_seconds=60
        )
        self._retry_count = retry_count
        self._retry_delay = retry_delay

    @property
    def name(self) -> str:
        return "hardcover_api"

    @property
    def description(self) -> str:
        return (
            "Gets book details, ratings, and purchase links via Hardcover API. "
            "Use when user asks about a specific book's rating, where to buy, or for Hardcover links. "
            "Supports book search, book details, purchase link generation, and Hardcover.app link generation."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "action": {
                "type": "string",
                "description": "Action to perform",
                "enum": [
                    "search_books",
                    "search_books_intelligent",
                    "search_books_raw",
                    "get_book_by_id",
                    "get_books_by_ids",
                    "get_user_recommendations",
                    "get_trending_books",
                    "get_recent_releases",
                    "get_current_user",
                    "introspect_schema",
                    "generate_hardcover_link",
                ],
            },
            "query": {
                "type": "string",
                "description": "Search query (required for search_books actions). Include both title and author for better results, e.g. 'The Scar China Miéville'",
            },
            "book_id": {
                "type": "integer",
                "description": "Book ID (required for get_book_by_id action)",
            },
            "book_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "List of book IDs (required for get_books_by_ids action)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5 for search, 10 for others)",
            },
            "offset": {
                "type": "integer",
                "description": "Number of results to skip (for pagination, default: 0)",
            },
            "from_date": {
                "type": "string",
                "description": "Start date in YYYY-MM-DD format (for trending books)",
            },
            "to_date": {
                "type": "string",
                "description": "End date in YYYY-MM-DD format (for trending books)",
            },
        }

    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters."""
        action = kwargs.get("action")

        if not action:
            return False

        if action in ["search_books", "search_books_intelligent", "search_books_raw"]:
            return bool(kwargs.get("query"))
        elif action == "generate_hardcover_link":
            return bool(kwargs.get("query"))
        elif action == "get_book_by_id":
            return bool(kwargs.get("book_id"))
        elif action == "get_books_by_ids":
            book_ids = kwargs.get("book_ids")
            return bool(book_ids and isinstance(book_ids, list) and len(book_ids) > 0)

        # Other actions don't require additional parameters
        return True

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the Hardcover API action."""
        if not self.validate_input(**kwargs):
            return ToolResult(
                success=False,
                data=None,
                error="Invalid parameters. Check action and required fields.",
            )

        try:
            action = kwargs["action"]

            if action == "search_books":
                query = kwargs["query"]
                limit = kwargs.get("limit", 5)
                data = await self._search_books(query, limit)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "query": query, "limit": limit},
                )

            elif action == "search_books_intelligent":
                query = kwargs["query"]
                limit = kwargs.get("limit", 5)
                context = kwargs.get("context", {})
                data = await self._search_books_intelligent(query, limit, context)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "query": query, "limit": limit},
                )

            elif action == "search_books_raw":
                query = kwargs["query"]
                limit = kwargs.get("limit", 5)
                data = await self._search_books_raw(query, limit)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "query": query, "limit": limit},
                )

            elif action == "get_book_by_id":
                book_id = kwargs["book_id"]
                data = await self._get_book_by_id(book_id)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "book_id": book_id},
                )

            elif action == "get_books_by_ids":
                book_ids = kwargs["book_ids"]
                data = await self._get_books_by_ids(book_ids)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "book_count": len(book_ids)},
                )

            elif action == "get_user_recommendations":
                limit = kwargs.get("limit", 10)
                data = await self._get_user_recommendations(limit)
                return ToolResult(
                    success=True, data=data, metadata={"action": action, "limit": limit}
                )

            elif action == "get_trending_books":
                from_date = kwargs.get("from_date")
                to_date = kwargs.get("to_date")
                limit = kwargs.get("limit", 10)
                offset = kwargs.get("offset", 0)
                data = await self._get_trending_books(from_date, to_date, limit, offset)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={
                        "action": action,
                        "from_date": from_date,
                        "to_date": to_date,
                        "limit": limit,
                    },
                )

            elif action == "get_recent_releases":
                limit = kwargs.get("limit", 10)
                data = await self._get_recent_releases(limit)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "limit": limit},
                )

            elif action == "get_current_user":
                data = await self._get_current_user()
                return ToolResult(success=True, data=data, metadata={"action": action})

            elif action == "introspect_schema":
                data = await self._introspect_schema()
                return ToolResult(success=True, data=data, metadata={"action": action})

            elif action == "generate_hardcover_link":
                query = kwargs["query"]
                data = await self._generate_hardcover_link(query)
                return ToolResult(
                    success=True,
                    data=data,
                    metadata={"action": action, "query": query},
                )

            else:
                return ToolResult(
                    success=False, data=None, error=f"Unknown action: {action}"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                metadata={
                    "error_type": type(e).__name__,
                    "action": kwargs.get("action"),
                },
            )

    async def _get_client(self) -> Client:
        """Get or create the GraphQL client."""
        if self._client is None:
            transport = AIOHTTPTransport(
                url=self.api_url,
                headers=self.headers,
                ssl=True,  # Enable SSL certificate verification for security
                timeout=30,  # 30 second timeout as per API docs
            )
            self._client = Client(transport=transport, fetch_schema_from_transport=True)
        return self._client

    async def _execute_with_retry(self, query, variables=None):
        """Execute a GraphQL query with rate limiting and retry logic."""
        # Apply rate limiting
        await self.rate_limiter.acquire()

        last_error = None
        for attempt in range(self._retry_count):
            try:
                client = await self._get_client()
                async with client as session:
                    # Minimal logging to reduce noise
                    result = await session.execute(query, variable_values=variables)
                    return result

            except TransportQueryError as e:
                # GraphQL errors (like field not found)
                logger.error(f"GraphQL query error: {e}")
                raise HardcoverAPIError(f"GraphQL query error: {e}") from e

            except TransportError as e:
                # Transport errors (network, timeout, etc)
                if "401" in str(e) or "403" in str(e):
                    raise HardcoverAuthError(f"Authentication failed: {e}") from e
                elif "429" in str(e):
                    # Rate limit hit despite our limiter - wait longer
                    wait_time = (
                        self._retry_delay * (attempt + 1) * 10
                    )  # Progressive backoff for rate limits
                    logger.warning(f"Rate limit hit, waiting {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                    last_error = HardcoverRateLimitError(f"Rate limit exceeded: {e}")
                elif "timeout" in str(e).lower():
                    raise HardcoverTimeoutError(
                        f"Query timeout (30s limit): {e}"
                    ) from e
                else:
                    last_error = e
                    if attempt < self._retry_count - 1:
                        delay = self._retry_delay * (2**attempt)  # Exponential backoff
                        logger.warning(f"Request failed, retrying in {delay}s: {e}")
                        await asyncio.sleep(delay)

            except Exception as e:
                logger.error(
                    f"Unexpected error in GraphQL execution: {type(e).__name__}: {e}"
                )
                logger.error(f"Exception details: {repr(e)}")
                if hasattr(e, "__cause__") and e.__cause__:
                    logger.error(
                        f"Caused by: {type(e.__cause__).__name__}: {e.__cause__}"
                    )
                last_error = e
                if attempt < self._retry_count - 1:
                    delay = self._retry_delay * (2**attempt)
                    logger.warning(f"Retrying in {delay}s after unexpected error")
                    await asyncio.sleep(delay)

        # All retries failed
        if isinstance(last_error, HardcoverAPIError):
            raise last_error
        else:
            raise HardcoverAPIError(
                f"Failed after {self._retry_count} attempts: {last_error}"
            )

    async def _search_books(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for books using Hardcover's search API (optimized for production)."""
        search_query = gql(
            """
            query SearchBooks($query: String!, $limit: Int!) {
                search(
                    query: $query,
                    query_type: "books",
                    per_page: $limit,
                    page: 1,
                    sort: "activities_count:desc"
                ) {
                    error
                    ids
                    query
                }
            }
        """
        )

        variables = {"query": query, "limit": limit}

        result = await self._execute_with_retry(search_query, variables)
        search_result = result.get("search", {})

        # If we got book IDs, fetch detailed info for them
        book_ids = search_result.get("ids", [])

        if book_ids:
            # Limit to requested number of books
            book_ids = book_ids[:limit]
            books = await self._get_books_by_ids(book_ids)
            return books

        return []

    async def _search_books_raw(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Search for books and return raw search results."""
        search_query = gql(
            """
            query SearchBooksRaw($query: String!, $limit: Int!) {
                search(
                    query: $query,
                    query_type: "books",
                    per_page: $limit,
                    page: 1,
                    sort: "activities_count:desc"
                ) {
                    error
                    ids
                    query
                    results
                }
            }
        """
        )

        variables = {"query": query, "limit": limit}

        result = await self._execute_with_retry(search_query, variables)
        return result.get("search", {})

    async def _search_books_intelligent(
        self, query: str, limit: int = 5, context: dict | None = None
    ) -> list[dict[str, Any]]:
        """Search for books using Claude-powered query optimization."""
        from datetime import datetime

        from src.tools.utils.query_optimizer import QueryOptimizerTool

        # Initialize query optimizer
        optimizer = QueryOptimizerTool()

        # Prepare context for optimization
        if context is None:
            context = {}

        # Add current date if not provided
        if "current_date" not in context:
            context["current_date"] = datetime.now().strftime("%Y-%m-%d")

        try:
            # Get optimization from Claude
            optimization_result = await optimizer.execute(query=query, context=context)

            if not optimization_result.success:
                logger.warning(
                    f"Query optimization failed, falling back to standard search: {optimization_result.error}"
                )
                return await self._search_books(query, limit)

            optimization = optimization_result.data
            logger.info(
                f"Query optimization: {optimization['pattern']} - {optimization['intent']}"
            )

            # Execute multi-strategy search based on optimization
            return await self._execute_intelligent_search_strategy(
                optimization, query, limit
            )

        except Exception as e:
            logger.warning(
                f"Intelligent search failed, falling back to standard search: {e}"
            )
            return await self._search_books(query, limit)

    async def _execute_intelligent_search_strategy(
        self, optimization: dict, original_query: str, limit: int
    ) -> list[dict[str, Any]]:
        """Execute search strategy based on Claude's optimization analysis."""
        pattern = optimization.get("pattern", "AUTHOR_BROWSE")
        author = optimization.get("author")
        temporal_indicators = optimization.get("temporal_indicators", [])

        logger.info(
            f"Executing search strategy: {pattern} for query '{original_query}'"
        )

        # Strategy 1: Series queries - search for books in specific series
        if pattern == "SERIES_QUERY":
            series = optimization.get("series")
            book_number = optimization.get("book_number")

            if series:
                try:
                    results = await self._search_books_in_series(
                        series,
                        book_number,
                        has_temporal=bool(optimization.get("temporal_indicators")),
                        limit=limit,
                    )
                    if results:
                        logger.info(
                            f"Found {len(results)} books using series search for {series}"
                        )
                        return results
                except Exception as e:
                    logger.warning(f"Series search failed: {e}")

            # Fallback to standard search if series search fails
            try:
                results = await self._search_books_optimized(
                    optimization["query_terms"], optimization["sort_by"], limit
                )
                if results:
                    logger.info(f"Found {len(results)} books using fallback search")
                    return results
            except Exception as e:
                logger.warning(f"Fallback search failed: {e}")

        # Strategy 2: Author queries with temporal intent - prioritize recent releases by author
        elif (
            pattern == "AUTHOR_QUERY"
            and author
            and optimization.get("sort_by") == "release_date:desc"
        ):
            # Try recent releases by author first
            try:
                results = await self._search_recent_releases_by_author(author, limit)
                if results:
                    logger.info(
                        f"Found {len(results)} books using recent releases by author"
                    )
                    return results
            except Exception as e:
                logger.warning(f"Recent releases by author strategy failed: {e}")

            # Try author books by recency
            try:
                results = await self._search_author_books_by_recency(author, limit)
                if results:
                    logger.info(
                        f"Found {len(results)} books using author books by recency"
                    )
                    return results
            except Exception as e:
                logger.warning(f"Author books by recency strategy failed: {e}")

            # Try optimized search as fallback
            try:
                results = await self._search_books_optimized(
                    optimization["query_terms"], optimization["sort_by"], limit
                )
                if results:
                    logger.info(f"Found {len(results)} books using optimized search")
                    return results
            except Exception as e:
                logger.warning(f"Optimized search strategy failed: {e}")

        # Strategy 3: Author queries without temporal intent - prioritize popular works by author
        elif (
            pattern == "AUTHOR_QUERY"
            and author
            and optimization.get("sort_by") == "activities_count:desc"
        ):
            try:
                # Use standard search for popular works by author
                results = await self._search_books_optimized(
                    optimization["query_terms"], optimization["sort_by"], limit
                )
                if results:
                    logger.info(f"Found {len(results)} popular books by {author}")
                    return results
            except Exception as e:
                logger.warning(f"Popular author search failed: {e}")

        # Strategy 4: Temporal general queries - recent releases
        elif pattern == "TEMPORAL_GENERAL" and temporal_indicators:
            try:
                # Try recent releases first
                recent_results = await self._get_recent_releases(
                    limit * 2
                )  # Get more to filter
                if recent_results:
                    # Filter by genre if specified
                    genre = optimization.get("genre")
                    if genre:
                        filtered_results = [
                            book
                            for book in recent_results
                            if genre.lower()
                            in (book.get("cached_tags", "") or "").lower()
                        ]
                        if filtered_results:
                            return filtered_results[:limit]
                    return recent_results[:limit]
            except Exception as e:
                logger.warning(f"Recent releases strategy failed: {e}")

        # Strategy 5: Specific title search
        elif pattern == "SPECIFIC_TITLE":
            title = optimization.get("title")
            if title:
                try:
                    results = await self._search_books_optimized(
                        title, "activities_count:desc", limit
                    )
                    if results:
                        return results
                except Exception as e:
                    logger.warning(f"Specific title search failed: {e}")

        # Default: Use optimized standard search
        try:
            return await self._search_books_optimized(
                optimization["query_terms"],
                optimization["sort_by"],
                optimization["limit"],
            )
        except Exception as e:
            logger.warning(f"Optimized search failed, using fallback: {e}")
            return await self._search_books(original_query, limit)

    async def _search_books_optimized(
        self, query_terms: str, sort_by: str, limit: int
    ) -> list[dict[str, Any]]:
        """Search books with optimized GraphQL parameters."""
        search_query = gql(
            """
            query SearchBooksOptimized($query: String!, $limit: Int!, $sort: String!) {
                search(
                    query: $query,
                    query_type: "books",
                    per_page: $limit,
                    page: 1,
                    sort: $sort
                ) {
                    error
                    ids
                    query
                }
            }
        """
        )

        variables = {"query": query_terms, "limit": limit, "sort": sort_by}

        result = await self._execute_with_retry(search_query, variables)
        search_result = result.get("search", {})

        # If we got book IDs, fetch detailed info for them
        book_ids = search_result.get("ids", [])

        if book_ids:
            book_ids = book_ids[:limit]
            books = await self._get_books_by_ids(book_ids)
            return books

        return []

    async def _search_recent_releases_by_author(
        self, author: str, limit: int
    ) -> list[dict[str, Any]]:
        """Search for recent releases by a specific author."""
        try:
            # Use the existing working pattern: get recent releases and filter by author
            # But use a longer timeframe to catch latest books
            logger.info(f"Searching recent books by {author} using extended timeframe")

            # Try last 6 months first (reasonable timeframe)
            recent_books = await self._get_recent_releases_extended(180, 25)

            if not recent_books:
                # If no recent releases in 6 months, try 1 year
                logger.info("No books found in last 6 months, trying last year")
                recent_books = await self._get_recent_releases_extended(365, 25)

            if not recent_books:
                # Fallback: if no recent releases, search all author books and sort by recency
                logger.info(
                    "No recent releases found, falling back to author books search"
                )
                return await self._search_author_books_by_recency(author, limit)

            # Filter by author name (case-insensitive partial match)
            author_books = []
            author_lower = author.lower()

            for book in recent_books:
                book_author = (
                    book.get("author", "") or book.get("cached_contributors", "")
                ).lower()
                if author_lower in book_author or any(
                    name.strip().lower() in book_author for name in author_lower.split()
                ):
                    author_books.append(book)
                    if len(author_books) >= limit:
                        break

            logger.info(f"Found {len(author_books)} recent books by {author}")

            # If we didn't find enough recent books, supplement with author's other recent works
            if len(author_books) < limit:
                logger.info(
                    f"Only found {len(author_books)} recent books, searching author catalog for more recent works"
                )
                additional_books = await self._search_author_books_by_recency(
                    author, limit - len(author_books)
                )
                # Add books that aren't already in our list
                existing_ids = {
                    book.get("id") for book in author_books if book.get("id")
                }
                for book in additional_books:
                    if book.get("id") not in existing_ids:
                        author_books.append(book)
                        if len(author_books) >= limit:
                            break

            return author_books

        except Exception as e:
            logger.warning(f"Recent releases by author search failed: {e}")
            return []

    async def _search_author_books_by_recency(
        self, author: str, limit: int
    ) -> list[dict[str, Any]]:
        """Search all books by author, sorted by recency."""
        try:
            # Search for more books by this author to get better recency sorting
            author_results = await self._search_books(
                author, 15
            )  # Increased from limit * 2

            if not author_results:
                return []

            # Sort by release year/date (most recent first)
            books_with_years = []
            for book in author_results:
                release_year = book.get("release_year", 0) or 0
                books_with_years.append((book, release_year))

            # Sort by year descending (most recent first)
            books_with_years.sort(key=lambda x: x[1], reverse=True)

            # Return just the books, limited to requested count
            sorted_books = [book for book, year in books_with_years[:limit]]

            logger.info(
                f"Found {len(sorted_books)} books by {author}, sorted by recency"
            )
            return sorted_books

        except Exception as e:
            logger.warning(f"Author books by recency search failed: {e}")
            return []

    async def _search_books_in_series(
        self,
        series_name: str,
        book_number: str | int | None = None,
        has_temporal: bool = False,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for books in a specific series."""
        try:
            logger.info(
                f"Searching for books in {series_name} series (book #{book_number if book_number else 'any'})"
            )

            # Search for all books that might be in this series
            # Use a broad search to catch different title formats
            search_results = await self._search_books(
                series_name, limit * 3
            )  # Get more results to filter

            if not search_results:
                logger.info(f"No books found for series search '{series_name}'")
                return []

            # Filter results to find books that are likely part of the series
            series_books = []
            series_lower = series_name.lower()

            for book in search_results:
                title = (book.get("title", "") or "").lower()
                # Check if this book is likely part of the series
                if series_lower in title:
                    series_books.append(book)

            logger.info(f"Found {len(series_books)} potential series books")

            # If we have a specific book number, try to find that book
            if book_number:
                try:
                    target_num = int(book_number)
                    logger.info(f"Looking for book #{target_num} in series")

                    # Look for books with the number in the title
                    for book in series_books:
                        title = book.get("title", "").lower()
                        # Check for various number formats: "book 7", "7:", "#7", etc.

                        number_patterns = [
                            rf"\b{target_num}\b",  # Exact number
                            rf"book\s+{target_num}",  # "book 7"
                            rf"#{target_num}",  # "#7"
                            rf"{target_num}:",  # "7:"
                        ]

                        if any(
                            re.search(pattern, title) for pattern in number_patterns
                        ):
                            logger.info(
                                f"Found book #{target_num}: {book.get('title')}"
                            )
                            return [book]

                except (ValueError, TypeError):
                    logger.warning(f"Could not parse book number: {book_number}")

            # If no specific number or couldn't find it, return series books
            if has_temporal:
                # For "latest" queries, sort by release date (newest first)
                series_books.sort(
                    key=lambda x: x.get("release_year", 0) or 0, reverse=True
                )
                logger.info(f"Returning latest books in {series_name} series")
            else:
                # For general series queries, sort by popularity
                series_books.sort(
                    key=lambda x: x.get("users_count", 0) or 0, reverse=True
                )
                logger.info(f"Returning popular books in {series_name} series")

            return series_books[:limit]

        except Exception as e:
            logger.warning(f"Series search failed for '{series_name}': {e}")
            return []

    async def _get_book_by_id(self, book_id: int) -> dict[str, Any] | None:
        """Get detailed book information by ID."""
        query = gql(
            """
            query GetBook($id: Int!) {
                books_by_pk(id: $id) {
                    id
                    title
                    subtitle
                    description
                    pages
                    release_year
                    rating
                    cached_contributors
                    cached_tags
                    slug
                    compilation
                    links
                    image {
                        url
                    }
                    contributions {
                        author {
                            id
                            name
                        }
                    }
                    ratings_count
                    reviews_count
                    users_count
                    editions {
                        id
                        isbn_10
                        isbn_13
                    }
                }
            }
        """
        )

        variables = {"id": book_id}

        result = await self._execute_with_retry(query, variables)
        book = result.get("books_by_pk")

        # Add purchase link and author information
        if book:
            # Extract author from contributions
            contributions = book.get("contributions", [])
            authors = []
            for contribution in contributions:
                if isinstance(contribution, dict) and "author" in contribution:
                    author = contribution["author"]
                    if isinstance(author, dict) and "name" in author:
                        authors.append(author["name"])

            # Set author field (use first author or cached_contributors as fallback)
            if authors:
                book["author"] = authors[0] if len(authors) == 1 else ", ".join(authors)
            elif book.get("cached_contributors"):
                book["author"] = book["cached_contributors"]

            # Validate ISBNs against bookshop.org for direct affiliate links
            if book.get("title"):
                book["bookshop_link"] = await bookshop_client.resolve_link(
                    book.get("editions", []), book["title"]
                )

        return book

    async def _get_books_by_ids(self, book_ids: list[int]) -> list[dict[str, Any]]:
        """Get detailed book information for multiple books by their IDs."""
        query = gql(
            """
            query GetBooksByIds($ids: [Int!]!) {
                books(where: {id: {_in: $ids}}) {
                    id
                    title
                    subtitle
                    description
                    pages
                    release_year
                    rating
                    cached_contributors
                    cached_tags
                    slug
                    compilation
                    links
                    image {
                        url
                    }
                    contributions {
                        author {
                            id
                            name
                        }
                    }
                    ratings_count
                    reviews_count
                    users_count
                    editions {
                        id
                        isbn_10
                        isbn_13
                    }
                }
            }
        """
        )

        variables = {"ids": book_ids}

        result = await self._execute_with_retry(query, variables)
        books = result.get("books", [])

        # Enhance books with purchase links and author information
        for book in books:
            # Extract author from contributions
            contributions = book.get("contributions", [])
            authors = []
            for contribution in contributions:
                if isinstance(contribution, dict) and "author" in contribution:
                    author = contribution["author"]
                    if isinstance(author, dict) and "name" in author:
                        authors.append(author["name"])

            # Set author field (use first author or cached_contributors as fallback)
            if authors:
                book["author"] = authors[0] if len(authors) == 1 else ", ".join(authors)
            elif book.get("cached_contributors"):
                book["author"] = book["cached_contributors"]

        # Validate ISBNs against bookshop.org concurrently for all books
        await asyncio.gather(*[_resolve_bookshop_link(book) for book in books])

        return books

    async def _get_user_recommendations(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get personalized book recommendations for the authenticated user."""
        query = gql(
            """
            query GetRecommendations($limit: Int!) {
                recommendations(limit: $limit) {
                    id
                    book {
                        id
                        title
                        description
                        cached_contributors
                        cached_tags
                        slug
                        image {
                            url
                        }
                    }
                }
            }
        """
        )

        variables = {"limit": limit}

        logger.info(f"Getting user recommendations: limit={limit}")
        result = await self._execute_with_retry(query, variables)
        return result.get("recommendations", [])

    async def _get_trending_books(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get currently trending/popular books for a date range."""
        # Use relative dates if not provided
        if from_date is None:
            from_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        if to_date is None:
            to_date = datetime.now().strftime("%Y-%m-%d")

        query = gql(
            """
            query GetTrendingBooks($from: date!, $to: date!, $limit: Int!, $offset: Int!) {
                books_trending(from: $from, to: $to, limit: $limit, offset: $offset) {
                    error
                    ids
                }
            }
        """
        )

        variables = {"from": from_date, "to": to_date, "limit": limit, "offset": offset}

        logger.info(
            f"Getting trending books: from={from_date}, to={to_date}, limit={limit}"
        )
        result = await self._execute_with_retry(query, variables)
        trending_result = result.get("books_trending", {})

        logger.info(f"Raw trending books result: {trending_result}")

        # If we got book IDs, also log them and fetch the books
        book_ids = trending_result.get("ids", [])
        if book_ids:
            logger.info(f"Got trending book IDs: {book_ids}")
            # Fetch the actual book data
            books = await self._get_books_by_ids(book_ids[:limit])
            logger.info(f"Fetched {len(books)} trending books with details")
            for i, book in enumerate(books):
                logger.info(
                    f"Book {i + 1}: {book.get('title', 'No title')} by {book.get('author', 'No author')}"
                )
            trending_result["books"] = books
        else:
            logger.warning("No book IDs returned from trending books query")

        return trending_result

    async def _get_recent_releases(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recently released books ordered by number of readers."""
        try:
            # Calculate date range for "recent" (last 1 month)
            one_month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            today = datetime.now().strftime("%Y-%m-%d")

            # Always pull 25 books to get better sorting, then return top 10
            query_limit = 25
            logger.info(
                f"Getting recent releases: from={one_month_ago}, to={today}, fetching={query_limit}, returning={limit}"
            )

            query = gql(
                """
                query GetRecentReleases($from_date: date!, $to_date: date!, $limit: Int!) {
                    books(
                        where: {
                            release_date: {_gte: $from_date, _lte: $to_date}
                        }
                        order_by: {users_count: desc}
                        limit: $limit
                    ) {
                        id
                        title
                        subtitle
                        description
                        pages
                        release_year
                        release_date
                        rating
                        cached_contributors
                        cached_tags
                        slug
                        compilation
                        links
                        image {
                            url
                        }
                        contributions {
                            author {
                                id
                                name
                            }
                        }
                        ratings_count
                        reviews_count
                        users_count
                        editions {
                            id
                            isbn_10
                            isbn_13
                        }
                    }
                }
            """
            )

            variables = {
                "from_date": one_month_ago,
                "to_date": today,
                "limit": query_limit,
            }
            logger.debug(f"GraphQL variables: {variables}")

            result = await self._execute_with_retry(query, variables)
            logger.debug(f"Raw GraphQL result: {result}")

            all_books = result.get("books", [])
            logger.info(
                f"Retrieved {len(all_books)} books from GraphQL query, selecting top {limit}"
            )

            # Take only the top N books (already sorted by users_count desc)
            books = all_books[:limit]

        except Exception as e:
            logger.error(f"Error in _get_recent_releases: {type(e).__name__}: {e}")
            logger.error(f"Exception details: {repr(e)}")
            raise

        # Enhance books with purchase links and author information (same as _get_books_by_ids)
        for book in books:
            # Extract author from contributions
            contributions = book.get("contributions", [])
            authors = []
            for contribution in contributions:
                if isinstance(contribution, dict) and "author" in contribution:
                    author = contribution["author"]
                    if isinstance(author, dict) and "name" in author:
                        authors.append(author["name"])

            # Set author field (use first author or cached_contributors as fallback)
            if authors:
                book["author"] = authors[0] if len(authors) == 1 else ", ".join(authors)
            elif book.get("cached_contributors"):
                book["author"] = book["cached_contributors"]

            # Truncate description for better presentation
            description = book.get("description", "")
            if description and len(description) > 200:
                book["short_description"] = description[:200] + "..."
            else:
                book["short_description"] = description

        # Validate ISBNs against bookshop.org concurrently for all books
        await asyncio.gather(*[_resolve_bookshop_link(book) for book in books])

        logger.info(
            f"Returning top {len(books)} recent releases sorted by reader count"
        )
        for i, book in enumerate(books, 1):
            readers = book.get("users_count", 0)
            logger.debug(f"#{i}: {book.get('title', 'Unknown')} - {readers} readers")

        return books

    async def _get_recent_releases_extended(
        self, days: int, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get recently released books with custom timeframe."""
        try:
            # Calculate date range for specified days
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            today = datetime.now().strftime("%Y-%m-%d")

            logger.info(
                f"Getting recent releases: from={start_date}, to={today}, fetching={limit}, returning={limit}"
            )

            query = gql(
                """
                query GetRecentReleasesExtended($from_date: date!, $to_date: date!, $limit: Int!) {
                    books(
                        where: {
                            release_date: {_gte: $from_date, _lte: $to_date}
                        }
                        order_by: {users_count: desc}
                        limit: $limit
                    ) {
                        id
                        title
                        subtitle
                        description
                        pages
                        release_year
                        release_date
                        rating
                        cached_contributors
                        cached_tags
                        slug
                        compilation
                        links
                        image {
                            url
                        }
                        contributions {
                            author {
                                id
                                name
                            }
                        }
                        ratings_count
                        reviews_count
                        users_count
                        editions {
                            id
                            isbn_10
                            isbn_13
                        }
                    }
                }
            """
            )

            variables = {
                "from_date": start_date,
                "to_date": today,
                "limit": limit,
            }

            result = await self._execute_with_retry(query, variables)
            books = result.get("books", [])

            # Enhance books with author and purchase links (same as _get_recent_releases)
            for book in books:
                contributions = book.get("contributions", [])
                authors = []
                for contribution in contributions:
                    if isinstance(contribution, dict) and "author" in contribution:
                        author = contribution["author"]
                        if isinstance(author, dict) and "name" in author:
                            authors.append(author["name"])

                if authors:
                    book["author"] = (
                        authors[0] if len(authors) == 1 else ", ".join(authors)
                    )
                elif book.get("cached_contributors"):
                    book["author"] = book["cached_contributors"]

                description = book.get("description", "")
                if description and len(description) > 200:
                    book["short_description"] = description[:200] + "..."
                else:
                    book["short_description"] = description

            # Validate ISBNs against bookshop.org concurrently for all books
            await asyncio.gather(*[_resolve_bookshop_link(book) for book in books])

            logger.info(f"Found {len(books)} books released in last {days} days")
            return books

        except Exception as e:
            logger.error(
                f"Error in _get_recent_releases_extended: {type(e).__name__}: {e}"
            )
            raise

    async def _get_current_user(self) -> dict[str, Any]:
        """Get current user information (test query)."""
        query = gql(
            """
            query {
                me {
                    id
                    username
                    email
                }
            }
        """
        )

        logger.info("Getting current user information")
        return await self._execute_with_retry(query)

    async def _introspect_schema(self) -> dict[str, Any]:
        """Get the GraphQL schema for exploration."""
        introspection_query = gql(
            """
            query IntrospectionQuery {
                __schema {
                    queryType { name }
                    mutationType { name }
                    subscriptionType { name }
                    types {
                        ...FullType
                    }
                }
            }

            fragment FullType on __Type {
                kind
                name
                description
                fields(includeDeprecated: true) {
                    name
                    description
                    args {
                        ...InputValue
                    }
                    type {
                        ...TypeRef
                    }
                    isDeprecated
                    deprecationReason
                }
                inputFields {
                    ...InputValue
                }
                interfaces {
                    ...TypeRef
                }
                enumValues(includeDeprecated: true) {
                    name
                    description
                    isDeprecated
                    deprecationReason
                }
                possibleTypes {
                    ...TypeRef
                }
            }

            fragment InputValue on __InputValue {
                name
                description
                type { ...TypeRef }
                defaultValue
            }

            fragment TypeRef on __Type {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                    ofType {
                                        kind
                                        name
                                        ofType {
                                            kind
                                            name
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """
        )

        logger.info("Introspecting GraphQL schema")
        return await self._execute_with_retry(introspection_query)

    async def _generate_hardcover_link(self, query: str) -> dict[str, Any] | None:
        """Generate a Hardcover.app link for a book by searching for it."""
        try:
            # Search for the book to get its slug
            books = await self._search_books(query, limit=1)

            if not books:
                return {
                    "error": f"No books found for query: {query}",
                    "hardcover_link": None,
                    "title": None,
                    "author": None,
                }

            book = books[0]
            slug = book.get("slug")

            if not slug:
                return {
                    "error": f"No slug found for book: {book.get('title', 'Unknown')}",
                    "hardcover_link": None,
                    "title": book.get("title"),
                    "author": book.get("author"),
                }

            hardcover_link = f"https://hardcover.app/books/{slug}?referrer_id=148"

            return {
                "hardcover_link": hardcover_link,
                "title": book.get("title"),
                "author": book.get("author"),
                "slug": slug,
            }

        except Exception as e:
            logger.error(f"Error generating Hardcover link for query '{query}': {e}")
            return {
                "error": f"Failed to generate link: {str(e)}",
                "hardcover_link": None,
                "title": None,
                "author": None,
            }

    async def close(self) -> None:
        """Close the client connection."""
        if self._client:
            await self._client.close_async()
            self._client = None
