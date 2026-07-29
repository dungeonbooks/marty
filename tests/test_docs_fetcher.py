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
    INDEX_FILE,
    DocNotFoundError,
    DocNotPublishedError,
    DocPayload,
    _cache,
    _parse,
    clear_cache,
    fetch_doc,
    fetch_page_index,
    format_index_for_prompt,
    format_page_index,
    parse_page_index,
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

    def test_extracts_agent_guidance_from_comments(self):
        raw = (
            "---\npublish: true\n---\n"
            "visible body\n\n"
            "<!--\nagent_guidance:\n  - do thing 1\n  - do thing 2\n-->\n\n"
            "more body\n"
        )
        p = _parse("x", raw)
        assert "visible body" in p.body
        assert "more body" in p.body
        assert "<!--" not in p.body
        assert p.agent_guidance == ["do thing 1", "do thing 2"]

    def test_human_only_keys_never_reach_the_agent(self):
        """`todo` and `status` are author notes. They are hidden from customers
        by living in a comment, but they are not directives and must not be fed
        to the model as if they were."""
        raw = (
            "---\npublish: true\n---\n"
            "body\n\n"
            "<!--\n"
            "agent_guidance:\n  - quote hours directly\n"
            "todo:\n  - confirm payment methods\n"
            "status:\n  - draft\n"
            "-->\n"
        )
        p = _parse("x", raw)

        assert p.agent_guidance == ["quote hours directly"]
        assert set(p.agent_directives) == {"agent_guidance"}
        assert "confirm payment methods" not in str(p.agent_directives)
        assert "draft" not in str(p.agent_directives)

    def test_unknown_agent_prefixed_key_is_kept(self):
        """The prefix is the contract, so a new directive needs no code change."""
        raw = "---\npublish: true\n---\nbody\n<!--\nagent_escalation:\n  - ping staff\n-->\n"
        p = _parse("x", raw)
        assert p.agent_directives["agent_escalation"] == ["ping staff"]

    def test_malformed_comment_drops_directives_rather_than_leaking(self):
        raw = "---\npublish: true\n---\nbody\n<!--\nagent_guidance: [unclosed\n-->\n"
        p = _parse("x", raw)
        assert p.agent_directives == {}
        assert p.agent_guidance == []

    def test_repeated_key_across_comments_accumulates(self):
        """A page may split guidance across blocks. Overwriting would drop the
        earlier one silently, which is how a directive goes missing unnoticed."""
        raw = (
            "---\npublish: true\n---\n"
            "body\n"
            "<!--\nagent_guidance:\n  - first rule\n-->\n"
            "more body\n"
            "<!--\nagent_guidance:\n  - second rule\n-->\n"
        )
        p = _parse("x", raw)
        assert p.agent_guidance == ["first rule", "second rule"]

    def test_repeated_mapping_key_merges(self):
        raw = (
            "---\npublish: true\n---\nbody\n"
            "<!--\nagent_index:\n  store: hours\n-->\n"
            "<!--\nagent_index:\n  events: formats\n-->\n"
        )
        p = _parse("x", raw)
        assert p.agent_directives["agent_index"] == {
            "store": "hours",
            "events": "formats",
        }

    def test_directive_ending_in_colon_keeps_the_authors_words(self):
        raw = "---\npublish: true\n---\nbody\n<!--\nagent_guidance:\n  - note to staff:\n-->\n"
        p = _parse("x", raw)
        assert p.agent_guidance == ["note to staff"]

    def test_prose_comment_is_not_treated_as_directives(self):
        raw = "---\npublish: true\n---\nbody\n<!-- just a note to self -->\n"
        p = _parse("x", raw)
        assert p.agent_directives == {}

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
                agent_directives={},
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
                agent_directives={},
                fetched_at=time.time() - CACHE_TTL_SECONDS - 1,
            ),
        )
        new_payload = DocPayload(
            slug="x",
            frontmatter={"publish": True, "title": "new"},
            body="new body",
            agent_directives={},
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
                agent_directives={},
                fetched_at=time.time(),
            ),
        )
        new_payload = DocPayload(
            slug="x",
            frontmatter={"publish": True},
            body="forced",
            agent_directives={},
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
                    agent_directives={},
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
                    agent_directives={},
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
                    agent_directives={},
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
                agent_directives={},
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
                agent_directives={},
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
                agent_directives={},
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
                agent_directives={},
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
                agent_directives={},
                fetched_at=time.time(),
            )

        monkeypatch.setattr(fetcher, "_fetch_remote", slow_fetch)
        results = await asyncio.gather(*[fetch_doc("x") for _ in range(5)])
        assert call_count == 1
        # All callers see the same payload
        assert {r.body for r in results} == {"body-1"}


LLMS_TXT = """# Dungeon Books Docs

> Operational documentation for Dungeon Books.

## Pages

- [Store](https://docs.dungeonbooks.com/store.md): Hours, location, and contact.
- [Events](https://docs.dungeonbooks.com/events.md)
- [Return policy](https://docs.dungeonbooks.com/policies/return-policy.md): Returns and exchanges.
"""


def _page_index(body: str) -> DocPayload:
    return DocPayload(
        slug=INDEX_FILE,
        frontmatter={},
        body=body,
        agent_directives={},
        fetched_at=time.time(),
    )


class TestParsePageIndex:
    def test_reads_slug_title_and_description(self):
        entries = parse_page_index(LLMS_TXT)
        assert [e.slug for e in entries] == [
            "store",
            "events",
            "policies/return-policy",
        ]
        assert entries[0].title == "Store"
        assert entries[0].description == "Hours, location, and contact."

    def test_description_is_none_when_absent(self):
        assert parse_page_index(LLMS_TXT)[1].description is None

    def test_ignores_the_heading_and_blurb(self):
        # The blurb starts with "> " and the heading with "# ", so neither can
        # match; this pins that they stay out rather than arriving as entries.
        assert len(parse_page_index(LLMS_TXT)) == 3

    def test_nested_slug_survives(self):
        entries = parse_page_index(LLMS_TXT)
        assert entries[2].slug == "policies/return-policy"

    # A slug is what fetch_doc builds its own URL from, so a link off-site would
    # become a request to the wrong page under our own host.
    def test_drops_links_to_another_host(self):
        raw = "- [Elsewhere](https://example.com/store.md): nope."
        assert parse_page_index(raw) == []

    def test_drops_links_that_are_not_markdown(self):
        raw = "- [Rendered](https://docs.dungeonbooks.com/store): nope."
        assert parse_page_index(raw) == []

    # Scheme-relative links are off-site but carry no scheme, so without an
    # explicit check they arrive as the in-site slug "example.com/store".
    def test_drops_scheme_relative_links(self):
        raw = "- [Elsewhere](//example.com/store.md): nope."
        assert parse_page_index(raw) == []

    # A traversal segment would be interpolated into the fetch URL as-is.
    @pytest.mark.parametrize(
        "target",
        ["../store.md", "policies/../../store.md", "./store.md", "policies//store.md"],
    )
    def test_drops_traversal_and_empty_segments(self, target):
        assert parse_page_index(f"- [Store]({target}): nope.") == []

    def test_keeps_a_plain_relative_link(self):
        # The emitter falls back to relative links when baseUrl is unset, so
        # these stay valid.
        entries = parse_page_index("- [Store](store.md): Hours.")
        assert [e.slug for e in entries] == ["store"]

    def test_skips_unparseable_lines(self):
        raw = "- not a link at all\n- [Store](https://docs.dungeonbooks.com/store.md)"
        entries = parse_page_index(raw)
        assert [e.slug for e in entries] == ["store"]

    def test_empty_file_yields_nothing(self):
        assert parse_page_index("") == []


class TestFormatPageIndex:
    def test_renders_slug_to_summary(self):
        out = format_page_index(_page_index(LLMS_TXT))
        assert out.startswith("page_index:\n")
        assert "  store: Hours, location, and contact." in out
        assert "  policies/return-policy: Returns and exchanges." in out

    def test_undescribed_page_is_listed_bare(self):
        assert "  events\n" in format_page_index(_page_index(LLMS_TXT)) + "\n"

    def test_empty_index_renders_nothing(self):
        assert format_page_index(_page_index("")) == ""


class TestFetchPageIndex:
    @pytest.mark.asyncio
    async def test_caches_and_skips_the_publish_gate(self, monkeypatch):
        calls = 0

        async def fake_remote():
            nonlocal calls
            calls += 1
            return _page_index(LLMS_TXT)

        monkeypatch.setattr(fetcher, "_fetch_page_index_remote", fake_remote)

        first = await fetch_page_index()
        second = await fetch_page_index()

        # llms.txt has no frontmatter, so a publish gate would reject it outright.
        assert first.frontmatter == {}
        assert calls == 1
        assert second is first

    @pytest.mark.asyncio
    async def test_force_refetches(self, monkeypatch):
        calls = 0

        async def fake_remote():
            nonlocal calls
            calls += 1
            return _page_index(LLMS_TXT)

        monkeypatch.setattr(fetcher, "_fetch_page_index_remote", fake_remote)
        await fetch_page_index()
        await fetch_page_index(force=True)
        assert calls == 2


class TestFormatIndexForPrompt:
    def test_combines_body_and_page_index(self):
        payload = DocPayload(
            slug="index",
            frontmatter={"publish": True},
            body="body content",
            agent_directives={},
            fetched_at=time.time(),
        )
        out = format_index_for_prompt(payload, _page_index(LLMS_TXT))
        assert "body content" in out
        assert "page_index" in out
        assert "store: Hours, location, and contact." in out

    def test_body_alone_when_the_page_index_is_missing(self):
        payload = DocPayload(
            slug="index",
            frontmatter={"publish": True},
            body="body content",
            agent_directives={},
            fetched_at=time.time(),
        )
        assert format_index_for_prompt(payload) == "body content"

    def test_skips_empty_parts(self):
        payload = DocPayload(
            slug="index",
            frontmatter={"publish": True},
            body="",
            agent_directives={},
            fetched_at=time.time(),
        )
        out = format_index_for_prompt(payload, _page_index(LLMS_TXT))
        assert out.startswith("page_index:")

    def test_index_todo_stays_out_of_the_system_prompt(self):
        payload = DocPayload(
            slug="index",
            frontmatter={"publish": True},
            body="body content",
            agent_directives={"todo": ["internal note"]},
            fetched_at=time.time(),
        )
        # `todo` is filtered at parse time and the index no longer reads comments
        # at all, so there are two reasons it cannot reach the prompt.
        assert "internal note" not in format_index_for_prompt(
            payload, _page_index(LLMS_TXT)
        )
