import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.scryfall.cards import (
    Card,
    RateLimiter,
    get_scryfall_data,
)


class TestCard:
    """Test cases for the Card class."""

    def test_card_initialization(self):
        """Test creating a Card object with all parameters."""
        card = Card(
            name="Black Lotus",
            price="1000.00",
            url="https://scryfall.com/card/1e/232/black-lotus",
            mana_cost="{0}",
            image="https://cards.scryfall.io/large/front/1/2/123.jpg",
            type_line="Artifact",
            oracle_text="Tap, Sacrifice Black Lotus: Add three mana of any one color.",
        )

        assert card.name == "Black Lotus"
        assert card.price == "1000.00"
        assert card.url == "https://scryfall.com/card/1e/232/black-lotus"
        assert card.mana_cost == "{0}"
        assert card.image == "https://cards.scryfall.io/large/front/1/2/123.jpg"
        assert card.type_line == "Artifact"
        assert "Sacrifice Black Lotus" in card.oracle_text

    def test_card_from_scryfall_with_complete_data(self):
        """Test creating a Card from Scryfall API response data."""
        scryfall_data = {
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "type_line": "Instant",
            "oracle_text": "Lightning Bolt deals 3 damage to any target.",
            "scryfall_uri": "https://scryfall.com/card/a25/141/lightning-bolt",
            "prices": {"usd": "15.00"},
            "image_uris": {
                "normal": "https://cards.scryfall.io/normal/front/1/2/123.jpg"
            },
        }

        card = Card.from_scryfall(scryfall_data)

        assert card.name == "Lightning Bolt"
        assert card.mana_cost == "{R}"
        assert card.type_line == "Instant"
        assert (
            card.oracle_text == "Lightning Bolt deals 3 damage to any target."
        )
        assert card.url == "https://scryfall.com/card/a25/141/lightning-bolt"
        assert card.price == "15.00"
        assert (
            card.image == "https://cards.scryfall.io/normal/front/1/2/123.jpg"
        )

    def test_card_from_scryfall_with_missing_optional_fields(self):
        """Test creating a Card when optional fields are missing."""
        scryfall_data = {
            "name": "Test Card",
            "mana_cost": "{1}{W}",
            "type_line": "Creature — Human",
            "oracle_text": "Test card text",
            "scryfall_uri": "https://scryfall.com/test",
            "prices": {"usd": None},
            "image_uris": {"normal": None},
        }

        card = Card.from_scryfall(scryfall_data)

        assert card.name == "Test Card"
        assert card.price is None
        assert card.image is None

    def test_card_from_scryfall_with_no_mana_cost(self):
        """Test creating a Card for a card with no mana cost."""
        scryfall_data = {
            "name": "Swamp",
            "mana_cost": "",
            "type_line": "Basic Land — Swamp",
            "oracle_text": "{T}: Add {B}.",
            "scryfall_uri": "https://scryfall.com/card/test",
            "prices": {"usd": "0.50"},
            "image_uris": {"normal": "https://example.com/image.jpg"},
        }

        card = Card.from_scryfall(scryfall_data)

        assert card.name == "Swamp"
        assert card.mana_cost == ""
        assert card.type_line == "Basic Land — Swamp"


class TestRateLimiter:
    """Test cases for the RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test RateLimiter is initialized correctly."""
        limiter = RateLimiter(min_interval=0.1)
        assert limiter.min_interval == 0.1
        assert limiter.last_call == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_single_acquire(self):
        """Test acquiring from rate limiter once."""
        limiter = RateLimiter(min_interval=0.05)
        await limiter.acquire()
        # Should not raise any exceptions
        assert limiter.last_call > 0

    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_minimum_interval(self):
        """Test that rate limiter enforces minimum interval between calls."""
        limiter = RateLimiter(min_interval=0.1)

        import time

        start_time = time.time()
        await limiter.acquire()
        first_call_time = time.time()

        await limiter.acquire()
        second_call_time = time.time()

        elapsed = second_call_time - first_call_time
        # Should have waited approximately 0.1 seconds
        assert elapsed >= 0.09

    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_calls(self):
        """Test rate limiter with concurrent calls."""
        limiter = RateLimiter(min_interval=0.05)

        # Create multiple concurrent acquire calls
        tasks = [limiter.acquire() for _ in range(3)]

        # All should complete without errors
        await asyncio.gather(*tasks)
        assert limiter.last_call > 0


class TestGetScryfallData:
    """Test cases for the get_scryfall_data function."""

    @pytest.mark.asyncio
    async def test_get_scryfall_data_successful_search(self):
        """Test successful API response."""
        mock_response_data = {
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "type_line": "Instant",
        }

        with (
            patch(
                "src.tools.scryfall.cards.fetch_scryfall",
                new_callable=AsyncMock,
                return_value=mock_response_data,
            ),
            patch(
                "src.tools.scryfall.cards.api_limiter.acquire",
                new_callable=AsyncMock,
            ),
        ):
            result = await get_scryfall_data("lightning bolt")

            assert result is not None
            assert result["name"] == "Lightning Bolt"

    @pytest.mark.asyncio
    async def test_get_scryfall_data_timeout_returns_none(self):
        """Test that timeout returns None and logs warning."""
        with (
            patch(
                "src.tools.scryfall.cards.fetch_scryfall",
                new_callable=AsyncMock,
                side_effect=TimeoutError,
            ),
            patch(
                "src.tools.scryfall.cards.api_limiter.acquire",
                new_callable=AsyncMock,
            ),
            patch("src.tools.scryfall.cards.logger") as mock_logger,
        ):
            result = await get_scryfall_data("some card")

            assert result is None
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_get_scryfall_data_network_error_returns_none(self):
        """Test that network errors return None and log warning."""
        import aiohttp

        with (
            patch(
                "src.tools.scryfall.cards.fetch_scryfall",
                new_callable=AsyncMock,
                side_effect=aiohttp.ClientError("Network error"),
            ),
            patch(
                "src.tools.scryfall.cards.api_limiter.acquire",
                new_callable=AsyncMock,
            ),
            patch("src.tools.scryfall.cards.logger") as mock_logger,
        ):
            result = await get_scryfall_data("some card")

            assert result is None
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_get_scryfall_data_api_error_returns_none(self):
        """Test API error handling."""
        import aiohttp

        error = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=500,
            message="Internal Server Error",
        )

        with (
            patch(
                "src.tools.scryfall.cards.fetch_scryfall",
                new_callable=AsyncMock,
                side_effect=error,
            ),
            patch(
                "src.tools.scryfall.cards.api_limiter.acquire",
                new_callable=AsyncMock,
            ),
            patch("src.tools.scryfall.cards.logger") as mock_logger,
        ):
            result = await get_scryfall_data("test")

            assert result is None
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_get_scryfall_data_respects_rate_limit(self):
        """Test that rate limiter is used."""
        with (
            patch(
                "src.tools.scryfall.cards.api_limiter.acquire",
                new_callable=AsyncMock,
            ) as mock_acquire,
            patch(
                "src.tools.scryfall.cards.fetch_scryfall",
                new_callable=AsyncMock,
                return_value={"name": "Test"},
            ),
        ):
            await get_scryfall_data("test card")

            mock_acquire.assert_called_once()
