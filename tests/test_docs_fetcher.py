"""Tests for src.tools.docs.fetcher.

Unit tests only — no live network. The aiohttp boundary is mocked via
monkeypatching `_fetch_remote`. Frontmatter parsing and HTML extraction
are tested through the pure `_parse` function.
"""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest
import yaml

from src.tools.docs import fetcher
from src.tools.docs.fetcher import (
    CACHE_TTL_SECONDS,
    DocNotFoundError,
    DocNotPublishedError,
    DocPayload,
    _cache,
    _parse,
    clear_cache,
    fetch_doc,
    format_index_for_prompt,
)


@pytest.fixture(autouse=True)
def reset_cache():
    clear_cache()
    yield
    clear_cache()


class TestParse:
    def test_parses_lf_frontmatter(self):
        raw = "---\ntitle: hello\npublish: true\n---\nbody text"
        p = _parse("x", raw)
        assert p.frontmatter == {"title": "hello", "publish": True}
        assert p.body == "body text"

    def test_parses_crlf_frontmatter(self):
        raw = "---\r\ntitle: hello\r\npublish: true\r\n---\r\nbody text"
        p = _parse("x", raw)
        assert p.frontmatter == {"title": "hello", "publish": True}
        assert p.body == "body text"

    def test_frontmatter_only_no_body(self):
        raw = "---\ntitle: hello\npublish: true\n---"
        p = _parse("x", raw)
        assert p.frontmatter == {"publish": True, "title": "hello"}
        assert p.body == ""

    def test_no_frontmatter_treats_whole_file_as_body(self):
        raw = "just markdown text, no frontmatter"
        p = _parse("x", raw)
        assert p.frontmatter == {}
        assert "just markdown text" in p.body

    def test_extracts_html_comments_as_agent_guidance(self):
        raw = (
            "---\npublish: true\n---\n"
            "visible body\n\n"
            "<!-- agent: do thing 1 -->\n\n"
            "more body\n\n"
            "<!-- agent: do thing 2 -->\n"
        )
        p = _parse("x", raw)
        assert "visible body" in p.body
        assert "more body" in p.body
        assert "<!--" not in p.body
        assert any("do thing 1" in g for g in p.agent_guidance)
        assert any("do thing 2" in g for g in p.agent_guidance)

    def test_empty_frontmatter_yields_empty_dict(self):
        raw = "---\n\n---\nbody"
        p = _parse("x", raw)
        assert p.frontmatter == {}
        assert p.body == "body"


class TestCachePolicy:
    @pytest.mark.asyncio
    async def test_returns_fresh_without_calling_remote(self, monkeypatch):
        called = []

        async def fake(slug):
            called.append(slug)
            return DocPayload(
                slug=slug,
                frontmatter={"publish": True},
                body="b",
                agent_guidance=[],
                fetched_at=time.time(),
            )

        monkeypatch.setattr(fetcher, "_fetch_remote", fake)
        first = await fetch_doc("x")
        second = await fetch_doc("x")
        assert first is second
        assert called == ["x"]

    @pytest.mark.asyncio
    async def test_expired_entry_triggers_refetch(self, monkeypatch):
        # Pre-populate with an expired entry
        _cache.set(
            "x",
            DocPayload(
                slug="x",
                frontmatter={"publish": True, "title": "old"},
                body="old body",
                agent_guidance=[],
                fetched_at=time.time() - CACHE_TTL_SECONDS - 1,
            ),
        )
        new_payload = DocPayload(
            slug="x",
            frontmatter={"publish": True, "title": "new"},
            body="new body",
            agent_guidance=[],
            fetched_at=time.time(),
        )

        monkeypatch.setattr(
            fetcher, "_fetch_remote", AsyncMock(return_value=new_payload)
        )
        result = await fetch_doc("x")
        assert result.body == "new body"

    @pytest.mark.asyncio
    async def test_force_bypasses_fresh_cache(self, monkeypatch):
        _cache.set(
            "x",
            DocPayload(
                slug="x",
                frontmatter={"publish": True},
                body="cached",
                agent_guidance=[],
                fetched_at=time.time(),
            ),
        )
        new_payload = DocPayload(
            slug="x",
            frontmatter={"publish": True},
            body="forced",
            agent_guidance=[],
            fetched_at=time.time(),
        )
        monkeypatch.setattr(
            fetcher, "_fetch_remote", AsyncMock(return_value=new_payload)
        )
        result = await fetch_doc("x", force=True)
        assert result.body == "forced"


class TestPublishGate:
    @pytest.mark.asyncio
    async def test_unpublished_doc_raises(self, monkeypatch):
        monkeypatch.setattr(
            fetcher,
            "_fetch_remote",
            AsyncMock(
                return_value=DocPayload(
                    slug="x",
                    frontmatter={"publish": False},
                    body="b",
                    agent_guidance=[],
                    fetched_at=time.time(),
                )
            ),
        )
        with pytest.raises(DocNotPublishedError):
            await fetch_doc("x")

    @pytest.mark.asyncio
    async def test_missing_publish_field_raises(self, monkeypatch):
        monkeypatch.setattr(
            fetcher,
            "_fetch_remote",
            AsyncMock(
                return_value=DocPayload(
                    slug="x",
                    frontmatter={"title": "no publish field"},
                    body="b",
                    agent_guidance=[],
                    fetched_at=time.time(),
                )
            ),
        )
        with pytest.raises(DocNotPublishedError):
            await fetch_doc("x")

    @pytest.mark.asyncio
    async def test_unpublished_doc_does_not_pollute_cache(self, monkeypatch):
        monkeypatch.setattr(
            fetcher,
            "_fetch_remote",
            AsyncMock(
                return_value=DocPayload(
                    slug="x",
                    frontmatter={"publish": False},
                    body="b",
                    agent_guidance=[],
                    fetched_at=time.time(),
                )
            ),
        )
        with pytest.raises(DocNotPublishedError):
            await fetch_doc("x")
        assert _cache.get_stale("x") is None


class TestErrorPaths:
    @pytest.mark.asyncio
    async def test_404_raises_doc_not_found(self, monkeypatch):
        monkeypatch.setattr(
            fetcher, "_fetch_remote", AsyncMock(side_effect=DocNotFoundError("x"))
        )
        with pytest.raises(DocNotFoundError):
            await fetch_doc("x")

    @pytest.mark.asyncio
    async def test_network_error_serves_stale(self, monkeypatch):
        # Pre-populate with stale entry
        _cache.set(
            "x",
            DocPayload(
                slug="x",
                frontmatter={"publish": True, "title": "stale"},
                body="stale body",
                agent_guidance=[],
                fetched_at=time.time() - CACHE_TTL_SECONDS - 1,
            ),
        )
        monkeypatch.setattr(
            fetcher,
            "_fetch_remote",
            AsyncMock(side_effect=ConnectionError("boom")),
        )
        result = await fetch_doc("x")
        assert result.body == "stale body"

    @pytest.mark.asyncio
    async def test_network_error_with_no_stale_raises(self, monkeypatch):
        monkeypatch.setattr(
            fetcher,
            "_fetch_remote",
            AsyncMock(side_effect=ConnectionError("boom")),
        )
        with pytest.raises(ConnectionError):
            await fetch_doc("x")

    @pytest.mark.asyncio
    async def test_404_does_not_serve_stale(self, monkeypatch):
        # 404 means the file is gone; stale would be misleading
        _cache.set(
            "x",
            DocPayload(
                slug="x",
                frontmatter={"publish": True},
                body="stale body",
                agent_guidance=[],
                fetched_at=time.time() - CACHE_TTL_SECONDS - 1,
            ),
        )
        monkeypatch.setattr(
            fetcher, "_fetch_remote", AsyncMock(side_effect=DocNotFoundError("x"))
        )
        with pytest.raises(DocNotFoundError):
            await fetch_doc("x")

    @pytest.mark.asyncio
    async def test_parse_error_propagates_instead_of_serving_stale(self, monkeypatch):
        # A bad doc commit (malformed YAML, etc.) should surface, not be masked.
        _cache.set(
            "x",
            DocPayload(
                slug="x",
                frontmatter={"publish": True},
                body="stale body",
                agent_guidance=[],
                fetched_at=time.time() - CACHE_TTL_SECONDS - 1,
            ),
        )
        monkeypatch.setattr(
            fetcher,
            "_fetch_remote",
            AsyncMock(side_effect=yaml.YAMLError("bad yaml")),
        )
        with pytest.raises(yaml.YAMLError):
            await fetch_doc("x")

    @pytest.mark.asyncio
    async def test_stale_served_entry_grants_grace_window(self, monkeypatch):
        # After serving stale once, the next call within the grace window
        # should hit the fast path and not re-attempt the failing fetch.
        _cache.set(
            "x",
            DocPayload(
                slug="x",
                frontmatter={"publish": True},
                body="stale body",
                agent_guidance=[],
                fetched_at=time.time() - CACHE_TTL_SECONDS - 1,
            ),
        )
        fetch_calls = 0

        async def failing_fetch(slug):
            nonlocal fetch_calls
            fetch_calls += 1
            raise ConnectionError("boom")

        monkeypatch.setattr(fetcher, "_fetch_remote", failing_fetch)

        first = await fetch_doc("x")
        second = await fetch_doc("x")
        third = await fetch_doc("x")

        assert first.body == second.body == third.body == "stale body"
        # Only the first call exercised _fetch_remote; the next two short-
        # circuited via the freshness window granted by touch().
        assert fetch_calls == 1


class TestStampedePrevention:
    @pytest.mark.asyncio
    async def test_concurrent_fetches_collapse_to_one_remote_call(self, monkeypatch):
        call_count = 0

        async def slow_fetch(slug):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return DocPayload(
                slug=slug,
                frontmatter={"publish": True},
                body=f"body-{call_count}",
                agent_guidance=[],
                fetched_at=time.time(),
            )

        monkeypatch.setattr(fetcher, "_fetch_remote", slow_fetch)
        results = await asyncio.gather(*[fetch_doc("x") for _ in range(5)])
        assert call_count == 1
        # All callers see the same payload
        assert {r.body for r in results} == {"body-1"}


class TestFormatIndexForPrompt:
    def test_combines_body_and_guidance(self):
        payload = DocPayload(
            slug="index",
            frontmatter={"publish": True},
            body="body content",
            agent_guidance=["agent_index: foo: bar"],
            fetched_at=time.time(),
        )
        out = format_index_for_prompt(payload)
        assert "body content" in out
        assert "agent_index" in out

    def test_skips_empty_parts(self):
        payload = DocPayload(
            slug="index",
            frontmatter={"publish": True},
            body="",
            agent_guidance=["only guidance"],
            fetched_at=time.time(),
        )
        out = format_index_for_prompt(payload)
        assert out == "only guidance"
