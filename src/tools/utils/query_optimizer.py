"""
Query Optimizer Tool - Uses Claude to optimize GraphQL queries based on user intent.

This tool analyzes natural language book search queries and provides optimized
GraphQL parameters including search terms, sort orders, and filters.
"""

import json
import os
import re
from typing import Any

import structlog
from anthropic import AsyncAnthropic

from src.tools.base import BaseTool, ToolResult

logger = structlog.get_logger(__name__)

# Word-to-number mapping for ordinal book numbers
WORD_TO_NUMBER_MAP = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}


class QueryOptimizerTool(BaseTool):
    """
    Uses Claude to analyze user search queries and optimize GraphQL parameters.

    This tool processes natural language queries like "Cassandra Khaw's new book"
    and returns optimized search parameters including temporal context awareness.
    """

    def __init__(self):
        super().__init__()
        self.claude_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    @property
    def name(self) -> str:
        return "query_optimizer"

    @property
    def description(self) -> str:
        return (
            "Analyzes natural language book search queries and provides optimized "
            "GraphQL parameters including search terms, sort orders, and temporal context."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "The natural language search query to optimize",
            },
            "context": {
                "type": "object",
                "description": "Optional context including platform, current date, etc.",
                "properties": {
                    "platform": {"type": "string"},
                    "current_date": {"type": "string"},
                    "user_preferences": {"type": "object"},
                },
            },
        }

    def validate_input(self, **kwargs) -> bool:
        """Validate input parameters."""
        return bool(kwargs.get("query"))

    async def execute(self, **kwargs) -> ToolResult:
        """Execute query optimization."""
        if not self.validate_input(**kwargs):
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: query",
            )

        try:
            query = kwargs["query"]
            context = kwargs.get("context", {})

            optimization = await self._optimize_query(query, context)

            return ToolResult(
                success=True,
                data=optimization,
                metadata={
                    "original_query": query,
                    "optimization_confidence": optimization.get("confidence", 0.0),
                },
            )

        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                metadata={"error_type": type(e).__name__},
            )

    async def _optimize_query(self, query: str, context: dict) -> dict[str, Any]:
        """Use Claude to analyze and optimize the search query."""

        optimization_prompt = f"""
Analyze this book search query and optimize the GraphQL parameters for a book database search:

User Query: "{query}"
Context: {json.dumps(context, indent=2)}

Available GraphQL sort options:
- activities_count:desc (popularity/trending - good for general searches)
- release_date:desc (newest first - good for "new", "latest", "recent" queries)
- title:asc (alphabetical - good for browsing)
- rating:desc (highest rated - good for quality searches)

Query Pattern Classification:
1. AUTHOR_QUERY: Author name queries → Popular works first UNLESS temporal keywords present
   - "Brandon Sanderson" → Popular works first (Mistborn, Stormlight Archive)
   - "Cassandra Khaw's new book" → Recent works first (has temporal keyword "new")
   - "Stephen King books" → Popular works first (browse catalog)
   - "latest Brandon Sanderson" → Recent works first (has temporal keyword "latest")
2. SERIES_QUERY: Series-specific queries → Search all books in series, then filter
   - "7th book in Dungeon Crawler Carl series" → Find all DCC books, return book 7
   - "latest Dungeon Crawler Carl book" → Find all DCC books, return most recent
   - "next Stormlight Archive book" → Find series books, return upcoming
3. TEMPORAL_GENERAL: "new fantasy books" → Search recent releases in genre
4. SPECIFIC_TITLE: "The Library at Hellebore" → Exact title search
5. GENRE_MOOD: "dark fantasy recommendations" → Genre search with mood
6. GENERAL_SEARCH: General queries → Standard search

Important: For AUTHOR_QUERY, most users want popular/acclaimed books when asking about an author. Only prioritize recent releases when temporal keywords ("new", "latest", "recent") are explicitly present.

Temporal Keywords: new, latest, recent, newest, just came out, just released, current

Return ONLY a JSON object with this exact structure:
{{
    "pattern": "AUTHOR_QUERY|SERIES_QUERY|TEMPORAL_GENERAL|SPECIFIC_TITLE|GENRE_MOOD|GENERAL_SEARCH",
    "query_terms": "optimized search terms for GraphQL",
    "sort_by": "best sort option from above list",
    "author": "extracted author name or null",
    "title": "extracted specific title or null",
    "series": "extracted series name or null",
    "book_number": "extracted book number/position or null",
    "genre": "extracted genre or null",
    "temporal_indicators": ["list of temporal keywords found"],
    "confidence": 0.8,
    "intent": "brief description of user intent",
    "search_strategy": "recommended search approach",
    "limit": 5
}}
"""

        try:
            response = await self.claude_client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                temperature=0.1,  # Low temperature for consistent structured output
                messages=[{"role": "user", "content": optimization_prompt}],
            )

            response_text = response.content[0].text.strip()

            # Extract JSON from response (handle potential markdown formatting)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif response_text.startswith("```") and response_text.endswith("```"):
                response_text = response_text[3:-3].strip()

            optimization = json.loads(response_text)

            # Validate and set defaults
            optimization = self._validate_optimization(optimization, query)

            logger.info(f"Query optimized: '{query}' → {optimization}")
            return optimization

        except json.JSONDecodeError as e:
            logger.warning(f"Claude returned invalid JSON, using fallback: {e}")
            return self._fallback_optimization(query)
        except Exception as e:
            logger.warning(f"Claude optimization failed, using fallback: {e}")
            return self._fallback_optimization(query)

    def _validate_optimization(self, optimization: dict, original_query: str) -> dict:
        """Validate and normalize the optimization response."""
        valid_patterns = [
            "AUTHOR_QUERY",
            "SERIES_QUERY",
            "TEMPORAL_GENERAL",
            "SPECIFIC_TITLE",
            "GENRE_MOOD",
            "GENERAL_SEARCH",
        ]
        valid_sorts = [
            "activities_count:desc",
            "release_date:desc",
            "title:asc",
            "rating:desc",
        ]

        # Ensure required fields exist with defaults
        optimization.setdefault("pattern", "GENERAL_SEARCH")
        optimization.setdefault("query_terms", original_query)
        optimization.setdefault("sort_by", "activities_count:desc")
        optimization.setdefault("author", None)
        optimization.setdefault("title", None)
        optimization.setdefault("series", None)
        optimization.setdefault("book_number", None)
        optimization.setdefault("genre", None)
        optimization.setdefault("temporal_indicators", [])
        optimization.setdefault("confidence", 0.5)
        optimization.setdefault("intent", "general book search")
        optimization.setdefault("search_strategy", "standard search")
        optimization.setdefault("limit", 5)

        # Validate pattern
        if optimization["pattern"] not in valid_patterns:
            optimization["pattern"] = "GENERAL_SEARCH"

        # Validate sort
        if optimization["sort_by"] not in valid_sorts:
            optimization["sort_by"] = "activities_count:desc"

        # Ensure limit is reasonable
        if not isinstance(optimization["limit"], int) or optimization["limit"] < 1:
            optimization["limit"] = 5
        elif optimization["limit"] > 20:
            optimization["limit"] = 20

        return optimization

    def _fallback_optimization(self, query: str) -> dict:
        """Provide fallback optimization when Claude analysis fails."""
        # Simple pattern detection as fallback
        query_lower = query.lower()
        temporal_keywords = [
            "new",
            "latest",
            "recent",
            "newest",
            "just came out",
            "just released",
        ]

        has_temporal = any(keyword in query_lower for keyword in temporal_keywords)

        # Check for series patterns - be more specific to avoid false positives
        series_indicators = [
            "series",
            "volume",
            "installment",
            "sequel",
            "prequel",
        ]

        # More specific patterns that indicate series queries
        ordinal_patterns = [
            r"\b(\d+)(?:st|nd|rd|th)\s+book\b",  # "7th book"
            r"\bbook\s+(\d+)\b",  # "book 7"
            r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+book\b",  # "seventh book"
        ]

        series_specific_patterns = [
            r"\bin\s+(?:the\s+)?\w+.*?\s+series\b",  # "in the [name] series"
            r"\w+.*?\s+series\s+book\b",  # "[name] series book"
            r"\blatest\s+\w+.*?\s+series\b",  # "latest [name] series"
        ]

        # Check for explicit series indicators or numbered book patterns
        is_series_query = (
            any(indicator in query_lower for indicator in series_indicators)
            or any(re.search(pattern, query_lower) for pattern in ordinal_patterns)
            or any(
                re.search(pattern, query_lower) for pattern in series_specific_patterns
            )
        )
        book_number = None
        series_name = None

        # Extract book number if present
        for pattern in ordinal_patterns:
            match = re.search(pattern, query_lower)
            if match:
                number_text = match.group(1)
                # Convert word numbers to digits
                book_number = WORD_TO_NUMBER_MAP.get(number_text, number_text)
                is_series_query = True
                break

        # Extract series name (simple heuristics) - only for confirmed series queries
        if is_series_query:
            # Look for patterns like "dungeon crawler carl series" or "stormlight archive"
            series_patterns = [
                r"(\w+(?:\s+\w+)*?)\s+series",  # "[series name] series"
                r"in\s+(?:the\s+)?(\w+(?:\s+\w+)*?)\s+series",  # "in [the] [series name] series"
                r"(\w+(?:\s+\w+){1,3})\s+book\s+\d+",  # "[series name] book 7"
                r"(\d+)(?:st|nd|rd|th)\s+book\s+in\s+(?:the\s+)?(\w+(?:\s+\w+)*)",  # "7th book in [series]"
            ]
            for pattern in series_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    # Handle different capture groups
                    if len(match.groups()) > 1:
                        series_name = match.group(
                            2
                        ).strip()  # For "7th book in [series]"
                    else:
                        series_name = match.group(1).strip()
                    break

            # If we can't extract a clear series name, this might be a false positive
            if not series_name:
                is_series_query = False

        has_temporal = any(keyword in query_lower for keyword in temporal_keywords)

        # Try to extract author using multiple patterns
        author_patterns = [
            r"([A-Z][a-z]+ [A-Z][a-z]+)'s (?:new|latest|recent)",  # "Author's new book"
            r"(?:new|latest|recent) book by ([A-Z][a-z]+ [A-Z][a-z]+)",  # "new book by Author"
            r"^([A-Z][a-z]+ [A-Z][a-z]+)$",  # Just "Author Name" alone
            r"^([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+)$",  # "First Middle Last" for 3-part names
            r"^([A-Z][a-z]+ [A-Z][a-z]+) (?:books|novels|series|bibliography)$",  # "Author books"
            r"^([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+) (?:books|novels|series|bibliography)$",  # "First Middle Last books"
            r"(?:latest|recent|new) ([A-Z][a-z]+ [A-Z][a-z]+)",  # "latest Author"
        ]

        author = None
        for pattern in author_patterns:
            match = re.search(pattern, query.strip())
            if match:
                author = match.group(1)
                break

        # Determine pattern and strategy
        if is_series_query and series_name:
            # Series query - search for all books in series
            pattern = "SERIES_QUERY"
            if has_temporal:
                sort_by = "release_date:desc"
                search_strategy = f"find latest book in {series_name} series"
            else:
                sort_by = "release_date:asc"  # Chronological order for numbered books
                search_strategy = (
                    f"find book {book_number} in {series_name} series"
                    if book_number
                    else f"search {series_name} series"
                )
        elif author:
            # Author query - default to popular unless temporal keywords present
            if has_temporal:
                pattern = "AUTHOR_QUERY"
                sort_by = (
                    "release_date:desc"  # Recent mode when temporal keywords present
                )
                search_strategy = "prioritize recent works by author"
            else:
                pattern = "AUTHOR_QUERY"
                sort_by = "activities_count:desc"  # Popular mode for bare author names
                search_strategy = "prioritize popular works by author"
        elif has_temporal:
            pattern = "TEMPORAL_GENERAL"
            sort_by = "release_date:desc"
            search_strategy = "prioritize recent releases"
        else:
            pattern = "GENERAL_SEARCH"
            sort_by = "activities_count:desc"
            search_strategy = "standard popularity search"

        return {
            "pattern": pattern,
            "query_terms": query,
            "sort_by": sort_by,
            "author": author,
            "title": None,
            "series": series_name,
            "book_number": book_number,
            "genre": None,
            "temporal_indicators": [
                kw for kw in temporal_keywords if kw in query_lower
            ],
            "confidence": 0.6,
            "intent": f"fallback analysis: {search_strategy}",
            "search_strategy": search_strategy,
            "limit": 5,
        }
