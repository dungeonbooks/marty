"""
Tests for QueryOptimizerTool - LLM-powered query optimization.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.tools.utils.query_optimizer import QueryOptimizerTool


class TestQueryOptimizerTool:
    """Test suite for QueryOptimizerTool."""

    @pytest.fixture
    def query_optimizer(self):
        """Create QueryOptimizerTool instance for testing."""
        return QueryOptimizerTool()

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM (OpenAI-shape) response for query optimization."""
        payload = json.dumps(
            {
                "pattern": "AUTHOR_QUERY",
                "query_terms": "Cassandra Khaw",
                "sort_by": "release_date:desc",
                "author": "Cassandra Khaw",
                "title": None,
                "genre": None,
                "temporal_indicators": ["new"],
                "confidence": 0.9,
                "intent": "Find recent books by Cassandra Khaw",
                "search_strategy": "prioritize recent releases by author",
                "limit": 5,
            }
        )
        return type(
            "MockResponse",
            (),
            {
                "choices": [
                    type(
                        "MockChoice",
                        (),
                        {"message": type("MockMessage", (), {"content": payload})()},
                    )()
                ]
            },
        )()

    def test_tool_properties(self, query_optimizer):
        """Test tool basic properties."""
        assert query_optimizer.name == "query_optimizer"
        assert "optimize" in query_optimizer.description.lower()
        assert "query" in query_optimizer.parameters
        assert query_optimizer.parameters["query"]["type"] == "string"

    def test_validate_input(self, query_optimizer):
        """Test input validation."""
        # Valid input
        assert query_optimizer.validate_input(query="test query")

        # Invalid input
        assert not query_optimizer.validate_input()
        assert not query_optimizer.validate_input(query="")
        assert not query_optimizer.validate_input(query=None)

    @pytest.mark.asyncio
    async def test_execute_success(self, query_optimizer, mock_llm_response):
        """Test successful query optimization."""
        with patch.object(
            query_optimizer.llm_client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_llm_response

            result = await query_optimizer.execute(query="Cassandra Khaw's new book")

            assert result.success
            assert result.data is not None
            assert result.data["pattern"] == "AUTHOR_QUERY"
            assert result.data["author"] == "Cassandra Khaw"
            assert result.data["sort_by"] == "release_date:desc"
            assert "new" in result.data["temporal_indicators"]

    @pytest.mark.asyncio
    async def test_execute_with_context(self, query_optimizer, mock_llm_response):
        """Test query optimization with context."""
        with patch.object(
            query_optimizer.llm_client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_llm_response

            context = {
                "platform": "discord",
                "current_date": "2024-07-26",
                "user_preferences": {"genres": ["fantasy", "horror"]},
            }

            result = await query_optimizer.execute(
                query="latest horror books", context=context
            )

            assert result.success
            assert result.metadata["original_query"] == "latest horror books"

    @pytest.mark.asyncio
    async def test_execute_missing_query(self, query_optimizer):
        """Test execution with missing query parameter."""
        result = await query_optimizer.execute()

        assert not result.success
        assert result.error == "Missing required parameter: query"

    @pytest.mark.asyncio
    async def test_llm_api_failure(self, query_optimizer):
        """Test fallback when the LLM API fails."""
        with patch.object(
            query_optimizer.llm_client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.side_effect = Exception("LLM API error")

            result = await query_optimizer.execute(query="Cassandra Khaw's new book")

            assert result.success  # Should use fallback
            assert result.data["pattern"] == "AUTHOR_QUERY"
            assert result.data["author"] == "Cassandra Khaw"
            assert result.data["confidence"] == 0.6  # Fallback confidence

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, query_optimizer):
        """Test handling of invalid JSON from the LLM."""
        invalid_response = type(
            "MockResponse",
            (),
            {
                "choices": [
                    type(
                        "MockChoice",
                        (),
                        {
                            "message": type(
                                "MockMessage",
                                (),
                                {"content": "This is not valid JSON content"},
                            )()
                        },
                    )()
                ]
            },
        )()

        with patch.object(
            query_optimizer.llm_client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = invalid_response

            result = await query_optimizer.execute(query="Stephen King books")

            assert result.success  # Should use fallback
            assert result.data["pattern"] in [
                "AUTHOR_QUERY",
                "SERIES_QUERY",
                "TEMPORAL_GENERAL",
                "SPECIFIC_TITLE",
                "GENRE_MOOD",
                "GENERAL_SEARCH",
            ]

    def test_fallback_optimization_author_temporal_query(self, query_optimizer):
        """Test fallback optimization for author queries with temporal keywords."""
        result = query_optimizer._fallback_optimization("Cassandra Khaw's new book")

        assert result["pattern"] == "AUTHOR_QUERY"
        assert result["author"] == "Cassandra Khaw"
        assert (
            result["sort_by"] == "release_date:desc"
        )  # Recent mode due to "new" keyword
        assert "new" in result["temporal_indicators"]

    def test_fallback_optimization_temporal_general(self, query_optimizer):
        """Test fallback optimization for general temporal queries."""
        result = query_optimizer._fallback_optimization("latest fantasy books")

        assert result["pattern"] == "TEMPORAL_GENERAL"
        assert result["author"] is None
        assert result["sort_by"] == "release_date:desc"
        assert "latest" in result["temporal_indicators"]

    def test_fallback_optimization_author_popular_mode(self, query_optimizer):
        """Test fallback optimization for author-only queries (should prioritize popular)."""
        result = query_optimizer._fallback_optimization("Brandon Sanderson")

        assert result["pattern"] == "AUTHOR_QUERY"
        assert result["author"] == "Brandon Sanderson"
        assert (
            result["sort_by"] == "activities_count:desc"
        )  # Popular mode (new default)
        assert result["temporal_indicators"] == []

    def test_fallback_optimization_author_browse_mode(self, query_optimizer):
        """Test fallback optimization for author browse queries."""
        result = query_optimizer._fallback_optimization("Stephen King books")

        assert result["pattern"] == "AUTHOR_QUERY"
        assert result["sort_by"] == "activities_count:desc"  # Browse mode
        assert result["temporal_indicators"] == []

    def test_fallback_optimization_recent_vs_popular_author_queries(
        self, query_optimizer
    ):
        """Test that author queries properly distinguish between recent and popular intent."""
        # Author with temporal keyword should prioritize recent
        recent_result = query_optimizer._fallback_optimization(
            "latest Brandon Sanderson"
        )
        assert recent_result["pattern"] == "AUTHOR_QUERY"
        assert recent_result["author"] == "Brandon Sanderson"
        assert recent_result["sort_by"] == "release_date:desc"
        assert "latest" in recent_result["temporal_indicators"]

        # Author without temporal keyword should prioritize popular
        popular_result = query_optimizer._fallback_optimization("Brandon Sanderson")
        assert popular_result["pattern"] == "AUTHOR_QUERY"
        assert popular_result["author"] == "Brandon Sanderson"
        assert popular_result["sort_by"] == "activities_count:desc"
        assert popular_result["temporal_indicators"] == []

    def test_validate_optimization(self, query_optimizer):
        """Test optimization validation and normalization."""
        # Test with incomplete optimization
        incomplete = {
            "pattern": "INVALID_PATTERN",
            "sort_by": "invalid_sort",
            "limit": "not_a_number",
        }

        validated = query_optimizer._validate_optimization(incomplete, "test query")

        assert validated["pattern"] == "GENERAL_SEARCH"  # Default fallback
        assert validated["sort_by"] == "activities_count:desc"  # Default fallback
        assert validated["limit"] == 5  # Default limit
        assert validated["query_terms"] == "test query"  # Uses original query

    def test_validate_optimization_limit_bounds(self, query_optimizer):
        """Test optimization limit boundary validation."""
        # Test with excessive limit
        high_limit = {
            "pattern": "AUTHOR_QUERY",
            "sort_by": "activities_count:desc",
            "limit": 100,  # Too high
        }

        validated = query_optimizer._validate_optimization(high_limit, "test")
        assert validated["limit"] == 20  # Capped at maximum

        # Test with negative limit
        negative_limit = {
            "pattern": "AUTHOR_QUERY",
            "sort_by": "activities_count:desc",
            "limit": -5,  # Invalid
        }

        validated = query_optimizer._validate_optimization(negative_limit, "test")
        assert validated["limit"] == 5  # Default fallback


class TestQueryOptimizerPatterns:
    """Test query pattern recognition and optimization strategies."""

    @pytest.fixture
    def query_optimizer(self):
        return QueryOptimizerTool()

    def test_temporal_author_patterns(self, query_optimizer):
        """Test various temporal author query patterns."""
        test_cases = [
            "Cassandra Khaw's new book",
            "Stephen King's latest novel",
            "Brandon Sanderson's recent release",
            "new book by Neil Gaiman",
            "latest book by Ursula K. Le Guin",
        ]

        for query in test_cases:
            result = query_optimizer._fallback_optimization(query)
            assert result["pattern"] in [
                "AUTHOR_QUERY",
                "SERIES_QUERY",
                "TEMPORAL_GENERAL",
            ]
            assert result["sort_by"] == "release_date:desc"

    def test_author_extraction(self, query_optimizer):
        """Test author name extraction from queries."""
        test_cases = [
            ("Cassandra Khaw's new book", "Cassandra Khaw"),
            ("Stephen King's latest", "Stephen King"),
            ("new book by Neil Gaiman", "Neil Gaiman"),
            ("recent release from Ursula K. Le Guin", None),  # Pattern not matched
        ]

        for query, expected_author in test_cases:
            result = query_optimizer._fallback_optimization(query)
            assert result["author"] == expected_author

    def test_temporal_indicators(self, query_optimizer):
        """Test temporal keyword detection."""
        test_cases = [
            ("new fantasy books", ["new"]),
            ("latest sci-fi novels", ["latest"]),
            ("recent horror releases", ["recent"]),
            ("books that just came out", ["just came out"]),
            ("newest mystery novels", ["newest"]),
        ]

        for query, expected_indicators in test_cases:
            result = query_optimizer._fallback_optimization(query)
            for indicator in expected_indicators:
                assert indicator in result["temporal_indicators"]
