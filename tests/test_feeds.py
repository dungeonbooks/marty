"""Tests for the RSS feed aggregator."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.discord_bot.feeds import (
    FEEDS,
    FeedEntry,
    FeedsCog,
    _extract_summary,
    _format_digest,
    _parse_ten_foot_pole,
    _split_message,
    _strip_html,
    fetch_feed,
)


class TestStripHtml:
    def test_removes_tags(self):
        assert _strip_html("<p>hello</p>") == "hello"

    def test_decodes_entities(self):
        assert _strip_html("it&#8217;s a test") == "it\u2019s a test"
        assert _strip_html("rock &amp; roll") == "rock & roll"

    def test_collapses_whitespace(self):
        assert _strip_html("  too   much   space  ") == "too much space"

    def test_handles_empty_string(self):
        assert _strip_html("") == ""


class TestParseTenFootPole:
    def _make_entry(self, content_html="", summary="", tags=None):
        entry = MagicMock()
        entry.summary = summary
        if content_html:
            entry.content = [{"value": content_html}]
        else:
            entry.content = []
        entry.tags = []
        if tags:
            for t in tags:
                tag = MagicMock()
                tag.term = t
                entry.tags.append(tag)
        return entry

    def test_extracts_metadata_from_pre_block(self):
        html = """
        <figure><img src="cover.jpg" /></figure>
        <pre class="wp-block-preformatted">By Pedro Gil<br>La Marco del Este<br>OSR<br>Levels 4-6</pre>
        <p>A great adventure in the jungle.</p>
        """
        summary, tags = _parse_ten_foot_pole(self._make_entry(content_html=html))

        assert "Pedro Gil" in summary
        assert "La Marco del Este" in summary
        assert "OSR" in summary
        assert "Levels 4-6" in summary
        assert "·" in summary
        assert "A great adventure in the jungle." in summary

    def test_skips_link_paragraphs(self):
        html = """
        <pre class="wp-block-preformatted">By Author<br>Publisher<br>OSR</pre>
        <p>https://www.drivethrurpg.com/product/12345</p>
        <p>The real description here.</p>
        """
        summary, _ = _parse_ten_foot_pole(self._make_entry(content_html=html))
        assert "The real description here." in summary
        assert "drivethrurpg" not in summary

    def test_extracts_the_best_tag(self):
        html = '<pre class="wp-block-preformatted">By A<br>B<br>OSE</pre><p>Good stuff.</p>'
        _, tags = _parse_ten_foot_pole(
            self._make_entry(content_html=html, tags=["Reviews", "The Best"])
        )
        assert "The Best" in tags

    def test_falls_back_to_summary_without_content(self):
        summary, _ = _parse_ten_foot_pole(
            self._make_entry(summary="Fallback summary text here.")
        )
        assert summary == "Fallback summary text here."

    def test_truncates_long_description(self):
        html = (
            '<pre class="wp-block-preformatted">By A<br>B</pre>'
            f"<p>{'x' * 300}</p>"
        )
        summary, _ = _parse_ten_foot_pole(self._make_entry(content_html=html))
        assert summary.endswith("...")
        # Metadata line + newline + truncated description
        desc_part = summary.split("\n", 1)[1]
        assert len(desc_part) <= 200


class TestExtractSummary:
    def test_sabre_gets_longer_limit(self):
        long_text = "x" * 350
        entry = MagicMock()
        entry.summary = long_text

        result = _extract_summary(entry, "Sabre Games OSR News")
        assert len(result) == 300

    def test_default_limit(self):
        long_text = "x" * 250
        entry = MagicMock()
        entry.summary = long_text

        result = _extract_summary(entry, "Questing Beast")
        assert len(result) == 200

    def test_short_text_unchanged(self):
        entry = MagicMock()
        entry.summary = "Short text"

        result = _extract_summary(entry, "Questing Beast")
        assert result == "Short text"


class TestFormatDigest:
    def _entry(self, title="Test", source="Ten Foot Pole", tags=None, **kwargs):
        return FeedEntry(
            title=title,
            url=f"https://example.com/{title.lower().replace(' ', '-')}",
            source=source,
            published=datetime(2026, 3, 25, tzinfo=UTC),
            summary="A test summary.",
            tags=tags or [],
            **kwargs,
        )

    def test_empty_entries(self):
        assert _format_digest([]) == ""

    def test_basic_formatting(self):
        result = _format_digest([self._entry(title="Cool Review")])
        assert "**RPG News Roundup**" in result
        assert "__**Ten Foot Pole**__" in result
        assert "[Cool Review]" in result
        assert "(Mar 25)" in result
        assert "A test summary." in result

    def test_the_best_star(self):
        result = _format_digest([self._entry(tags=["The Best"])])
        assert "⭐" in result

    def test_no_star_without_tag(self):
        result = _format_digest([self._entry()])
        assert "⭐" not in result

    def test_respects_feed_order(self):
        entries = [
            self._entry(title="TFP Post", source="Ten Foot Pole"),
            self._entry(title="QB Post", source="Questing Beast"),
            self._entry(title="Sabre Post", source="Sabre Games OSR News"),
        ]
        result = _format_digest(entries)

        qb_pos = result.index("Questing Beast")
        sabre_pos = result.index("Sabre Games OSR News")
        tfp_pos = result.index("Ten Foot Pole")

        assert qb_pos < sabre_pos < tfp_pos

    def test_entry_without_summary(self):
        entry = self._entry()
        entry.summary = ""
        result = _format_digest([entry])
        assert "— " not in result


class TestSplitMessage:
    def test_short_message_single_chunk(self):
        result = _split_message("short message", limit=100)
        assert result == ["short message"]

    def test_splits_on_newlines(self):
        msg = "\n".join(["x" * 50] * 5)
        result = _split_message(msg, limit=120)
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= 120

    def test_empty_message(self):
        result = _split_message("")
        assert result == []


class TestFetchFeed:
    @pytest.mark.asyncio
    async def test_returns_entries_on_success(self):
        rss_xml = """<?xml version="1.0"?>
        <rss version="2.0">
        <channel>
            <item>
                <title>Test Post</title>
                <link>https://example.com/post</link>
                <description>A description.</description>
                <pubDate>Mon, 25 Mar 2026 12:00:00 +0000</pubDate>
            </item>
        </channel>
        </rss>"""

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value=rss_xml)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))
        )

        feed = {"name": "Test Feed", "url": "https://example.com/feed"}
        entries = await fetch_feed(mock_session, feed)

        assert len(entries) == 1
        assert entries[0].title == "Test Post"
        assert entries[0].url == "https://example.com/post"
        assert entries[0].source == "Test Feed"

    @pytest.mark.asyncio
    async def test_returns_empty_on_http_error(self):
        mock_resp = AsyncMock()
        mock_resp.status = 404

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))
        )

        feed = {"name": "Test Feed", "url": "https://example.com/feed"}
        entries = await fetch_feed(mock_session, feed)
        assert entries == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_network_error(self):
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=Exception("Connection refused"))

        feed = {"name": "Test Feed", "url": "https://example.com/feed"}
        entries = await fetch_feed(mock_session, feed)
        assert entries == []

    @pytest.mark.asyncio
    async def test_skips_entries_without_url(self):
        rss_xml = """<?xml version="1.0"?>
        <rss version="2.0">
        <channel>
            <item>
                <title>No Link Post</title>
                <description>Missing link element.</description>
            </item>
        </channel>
        </rss>"""

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.text = AsyncMock(return_value=rss_xml)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))
        )

        feed = {"name": "Test Feed", "url": "https://example.com/feed"}
        entries = await fetch_feed(mock_session, feed)
        assert entries == []


class TestFeedsCog:
    @pytest.mark.asyncio
    async def test_digest_calls_post_digest(self):
        mock_bot = MagicMock()
        cog = FeedsCog(mock_bot)

        with patch.object(cog, "_post_digest", new_callable=AsyncMock) as mock_post:
            mock_ctx = MagicMock()
            mock_ctx.typing.return_value = AsyncMock()
            mock_ctx.channel = MagicMock()
            await FeedsCog.digest.callback(cog, mock_ctx)
            mock_post.assert_called_once_with(
                channel_override=mock_ctx.channel, skip_dedup=True
            )

    @pytest.mark.asyncio
    async def test_post_digest_skips_without_channel_id(self):
        mock_bot = MagicMock()
        cog = FeedsCog(mock_bot)

        with patch("src.discord_bot.feeds.config") as mock_config:
            mock_config.RPG_NEWS_CHANNEL_ID = None
            await cog._post_digest()
            # Should return without error

    @pytest.mark.asyncio
    async def test_dedup_with_redis(self):
        mock_bot = MagicMock()
        cog = FeedsCog(mock_bot)
        cog._redis = AsyncMock()
        cog._redis.sismember = AsyncMock(return_value=True)

        assert await cog._is_seen("https://example.com/post") is True

    @pytest.mark.asyncio
    async def test_dedup_without_redis(self):
        mock_bot = MagicMock()
        cog = FeedsCog(mock_bot)
        cog._redis = None

        assert await cog._is_seen("https://example.com/post") is False

    @pytest.mark.asyncio
    async def test_mark_seen_with_redis(self):
        mock_bot = MagicMock()
        cog = FeedsCog(mock_bot)
        cog._redis = AsyncMock()

        urls = ["https://example.com/1", "https://example.com/2"]
        await cog._mark_seen(urls)

        cog._redis.sadd.assert_called_once()
        cog._redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_seen_noop_without_redis(self):
        mock_bot = MagicMock()
        cog = FeedsCog(mock_bot)
        cog._redis = None

        await cog._mark_seen(["https://example.com/1"])
        # Should not raise
