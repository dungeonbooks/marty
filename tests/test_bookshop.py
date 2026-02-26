"""
Tests for BookshopClient - bookshop.org ISBN validation and link generation.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.tools.external.bookshop import BookshopClient


@pytest.fixture
def client():
    return BookshopClient()


# --- validate_isbn ---


async def test_validate_isbn_valid(client):
    """A 308 response means the ISBN is valid."""
    mock_response = httpx.Response(status_code=308, request=httpx.Request("HEAD", "https://bookshop.org/book/9780316769488"))
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, return_value=mock_response):
        assert await client.validate_isbn("9780316769488") is True


async def test_validate_isbn_invalid(client):
    """A 404 response means the ISBN is invalid."""
    mock_response = httpx.Response(status_code=404, request=httpx.Request("HEAD", "https://bookshop.org/book/0000000000000"))
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, return_value=mock_response):
        assert await client.validate_isbn("0000000000000") is False


async def test_validate_isbn_timeout(client):
    """Timeout should return False (graceful degradation)."""
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timed out")):
        assert await client.validate_isbn("9780316769488") is False


async def test_validate_isbn_http_error(client):
    """HTTP errors should return False (graceful degradation)."""
    with patch("httpx.AsyncClient.head", new_callable=AsyncMock, side_effect=httpx.ConnectError("connection refused")):
        assert await client.validate_isbn("9780316769488") is False


# --- validate_isbns ---


async def test_validate_isbns_finds_first_valid(client):
    """Should return the first valid ISBN from the list."""
    async def mock_validate(isbn):
        return isbn == "9780316769488"

    client.validate_isbn = mock_validate
    result = await client.validate_isbns(["0000000000001", "9780316769488", "0000000000002"])
    assert result == "9780316769488"


async def test_validate_isbns_none_valid(client):
    """Should return None when no ISBNs are valid."""
    async def mock_validate(isbn):
        return False

    client.validate_isbn = mock_validate
    result = await client.validate_isbns(["0000000000001", "0000000000002"])
    assert result is None


async def test_validate_isbns_empty_list(client):
    """Should return None for an empty list."""
    result = await client.validate_isbns([])
    assert result is None


# --- get_buy_url ---


def test_get_buy_url(client):
    url = client.get_buy_url("9780316769488", "108216")
    assert url == "https://bookshop.org/a/108216/9780316769488"


def test_get_buy_url_default_affiliate(client):
    """Should use the configured affiliate ID when none is provided."""
    with patch("src.tools.external.bookshop.config") as mock_config:
        mock_config.BOOKSHOP_AFFILIATE_ID = "108216"
        url = client.get_buy_url("9780316769488")
        assert url == "https://bookshop.org/a/108216/9780316769488"


# --- get_search_url ---


def test_get_search_url(client):
    url = client.get_search_url("The Catcher in the Rye", "108216")
    assert url == "https://bookshop.org/search?keywords=The+Catcher+in+the+Rye&affiliate=108216"


def test_get_search_url_special_characters(client):
    url = client.get_search_url("Harry Potter & the Sorcerer's Stone", "108216")
    assert "keywords=Harry+Potter" in url
    assert "&affiliate=108216" in url


# --- resolve_link ---


async def test_resolve_link_with_valid_isbn(client):
    """Should return a direct /a/ URL when a valid ISBN is found."""
    editions = [
        {"isbn_13": "0000000000001"},
        {"isbn_13": "9780316769488"},
    ]

    async def mock_validate_isbns(isbns):
        return "9780316769488"

    client.validate_isbns = mock_validate_isbns

    with patch("src.tools.external.bookshop.config") as mock_config:
        mock_config.BOOKSHOP_AFFILIATE_ID = "108216"
        url = await client.resolve_link(editions, "The Catcher in the Rye")
        assert url == "https://bookshop.org/a/108216/9780316769488"


async def test_resolve_link_fallback_to_search(client):
    """Should fall back to search URL when no valid ISBN is found."""
    editions = [
        {"isbn_13": "0000000000001"},
        {"isbn_13": "0000000000002"},
    ]

    async def mock_validate_isbns(isbns):
        return None

    client.validate_isbns = mock_validate_isbns

    with patch("src.tools.external.bookshop.config") as mock_config:
        mock_config.BOOKSHOP_AFFILIATE_ID = "108216"
        url = await client.resolve_link(editions, "The Catcher in the Rye")
        assert "search?keywords=" in url
        assert "affiliate=108216" in url


async def test_resolve_link_no_editions(client):
    """Should return search URL when there are no editions."""
    with patch("src.tools.external.bookshop.config") as mock_config:
        mock_config.BOOKSHOP_AFFILIATE_ID = "108216"
        url = await client.resolve_link([], "The Catcher in the Rye")
        assert "search?keywords=" in url
        assert "affiliate=108216" in url


async def test_resolve_link_editions_without_isbn(client):
    """Should return search URL when editions have no isbn_13 field."""
    editions = [{"id": 1}, {"id": 2}]

    with patch("src.tools.external.bookshop.config") as mock_config:
        mock_config.BOOKSHOP_AFFILIATE_ID = "108216"
        url = await client.resolve_link(editions, "Some Book")
        assert "search?keywords=" in url


async def test_timeout_falls_back_to_search(client):
    """Timeout during validation should fall back to search URL."""
    editions = [{"isbn_13": "9780316769488"}]

    async def mock_validate_isbns(isbns):
        raise httpx.TimeoutException("timed out")

    client.validate_isbns = mock_validate_isbns

    with patch("src.tools.external.bookshop.config") as mock_config:
        mock_config.BOOKSHOP_AFFILIATE_ID = "108216"
        url = await client.resolve_link(editions, "The Catcher in the Rye")
        assert "search?keywords=" in url
        assert "affiliate=108216" in url
