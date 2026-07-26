"""Coverage for the two paths that turn a Hardcover record into an embed.

`_send_book_embeds` runs off a tool result, `_send_embeds_for_mentioned_books`
off bolded titles in prose. Both funnel through `_emit_book_embed`, and the
bookkeeping they share is where the regressions have been.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.discord_bot.bot import _MAX_AUTO_EMBEDS, _MAX_TRACKED_THREADS, MartyBot


def make_bot():
    with patch("src.discord_bot.bot.HardcoverTool", MagicMock()):
        with patch.object(MartyBot, "__init__", lambda self: None):
            bot = MartyBot()
    bot._embedded_books = {}
    bot.hardcover = MagicMock()
    return bot


def make_thread(thread_id=12345):
    thread = MagicMock()
    thread.id = thread_id
    thread.send = AsyncMock()
    return thread


def tool_result(action, data, success=True):
    result = MagicMock()
    result.success = success
    result.data = data
    return {"result": result, "tool_input": {"action": action}}


def hardcover_hit(book):
    result = MagicMock()
    result.success = True
    result.data = [book]
    return result


def hardcover_miss():
    result = MagicMock()
    result.success = False
    result.data = None
    return result


DUNE = {"title": "Dune", "author": "Frank Herbert"}


@pytest.fixture
def bot():
    return make_bot()


@pytest.fixture
def thread():
    return make_thread()


class TestEmbeddedTitlesCache:
    """Per-thread bookkeeping. A None id used to collapse every id-less
    channel into one shared bucket, and nothing ever evicted."""

    def test_missing_thread_id_gets_no_cache(self, bot):
        assert bot._embedded_titles(None) is None

    def test_id_less_channels_do_not_dedupe_against_each_other(self, bot):
        assert bot._embedded_titles(None) is bot._embedded_titles(None)
        assert bot._embedded_books == {}

    def test_same_thread_returns_same_set(self, bot):
        first = bot._embedded_titles(7)
        first.add("dune")
        assert "dune" in bot._embedded_titles(7)

    def test_distinct_threads_get_distinct_sets(self, bot):
        bot._embedded_titles(1).add("dune")
        assert "dune" not in bot._embedded_titles(2)

    def test_cache_is_bounded(self, bot):
        for thread_id in range(_MAX_TRACKED_THREADS + 25):
            bot._embedded_titles(thread_id)
        assert len(bot._embedded_books) == _MAX_TRACKED_THREADS

    def test_oldest_thread_is_evicted_first(self, bot):
        for thread_id in range(_MAX_TRACKED_THREADS + 1):
            bot._embedded_titles(thread_id)
        assert 0 not in bot._embedded_books
        assert _MAX_TRACKED_THREADS in bot._embedded_books


class TestSendBookEmbedsToolPath:
    """`_send_book_embeds` is driven by whatever action Marty called."""

    @pytest.mark.asyncio
    async def test_single_dict_result_is_embedded(self, bot, thread):
        await bot._send_book_embeds(tool_result("get_book_by_id", DUNE), thread, "n")
        assert thread.send.await_count == 1

    @pytest.mark.asyncio
    async def test_search_embeds_only_the_top_hit(self, bot, thread):
        data = [DUNE, {"title": "Piranesi", "author": "Clarke"}]
        await bot._send_book_embeds(
            tool_result("search_books_intelligent", data), thread, "n"
        )
        assert thread.send.await_count == 1

    @pytest.mark.asyncio
    async def test_get_books_by_ids_embeds_each(self, bot, thread):
        data = [DUNE, {"title": "Piranesi", "author": "Clarke"}]
        await bot._send_book_embeds(tool_result("get_books_by_ids", data), thread, "n")
        assert thread.send.await_count == 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", ["get_trending_books", "get_recent_releases"])
    async def test_list_actions_send_nothing(self, bot, thread, action):
        await bot._send_book_embeds(tool_result(action, [DUNE]), thread, "n")
        assert thread.send.await_count == 0

    @pytest.mark.asyncio
    async def test_stub_records_are_filtered_out(self, bot, thread):
        await bot._send_book_embeds(
            tool_result("search_books", [{"title": "Untitled Stub"}]), thread, "n"
        )
        assert thread.send.await_count == 0

    @pytest.mark.asyncio
    async def test_contributor_only_record_still_embeds(self, bot, thread):
        # create_book_embed falls back to cached_contributors for the author,
        # so this record renders fine and must not be treated as a stub.
        book = {"title": "Some Book", "cached_contributors": "A. Writer"}
        await bot._send_book_embeds(tool_result("search_books", [book]), thread, "n")
        assert thread.send.await_count == 1

    @pytest.mark.asyncio
    async def test_failed_result_sends_nothing(self, bot, thread):
        await bot._send_book_embeds(
            tool_result("search_books", [DUNE], success=False), thread, "n"
        )
        assert thread.send.await_count == 0

    @pytest.mark.asyncio
    async def test_non_dict_entries_are_ignored(self, bot, thread):
        await bot._send_book_embeds(
            tool_result("search_books", ["not a book", 42]), thread, "n"
        )
        assert thread.send.await_count == 0

    @pytest.mark.asyncio
    async def test_unexpected_data_shape_sends_nothing(self, bot, thread):
        await bot._send_book_embeds(
            tool_result("search_books", "a bare string"), thread, "n"
        )
        assert thread.send.await_count == 0


class TestSendEmbedsForMentionedBooks:
    """The prose path: bolded titles resolved against Hardcover."""

    @pytest.mark.asyncio
    async def test_bolded_title_is_resolved_and_embedded(self, bot, thread):
        bot.hardcover.execute = AsyncMock(return_value=hardcover_hit(DUNE))
        await bot._send_embeds_for_mentioned_books("try **Dune** sometime", thread, "n")
        assert thread.send.await_count == 1

    @pytest.mark.asyncio
    async def test_unresolved_title_sends_nothing(self, bot, thread):
        bot.hardcover.execute = AsyncMock(return_value=hardcover_miss())
        await bot._send_embeds_for_mentioned_books("**Book Of Nothing**", thread, "n")
        assert thread.send.await_count == 0

    @pytest.mark.asyncio
    async def test_mismatched_resolution_is_rejected(self, bot, thread):
        # Hardcover confidently returns something unrelated for a phrase that
        # is not a book; embedding it would make Marty look like he cited it.
        bot.hardcover.execute = AsyncMock(return_value=hardcover_hit(DUNE))
        await bot._send_embeds_for_mentioned_books("**a cozy afternoon**", thread, "n")
        assert thread.send.await_count == 0

    @pytest.mark.asyncio
    async def test_lookup_failure_is_swallowed(self, bot, thread):
        bot.hardcover.execute = AsyncMock(side_effect=Exception("hardcover down"))
        await bot._send_embeds_for_mentioned_books("**Dune**", thread, "n")
        assert thread.send.await_count == 0

    @pytest.mark.asyncio
    async def test_embed_count_is_capped(self, bot, thread):
        bot.hardcover.execute = AsyncMock(
            side_effect=lambda **kw: hardcover_hit(
                {"title": kw["query"], "author": "A"}
            )
        )
        prose = " ".join(f"**Book Number {i}**" for i in range(_MAX_AUTO_EMBEDS + 3))
        await bot._send_embeds_for_mentioned_books(prose, thread, "n")
        assert thread.send.await_count == _MAX_AUTO_EMBEDS

    @pytest.mark.asyncio
    async def test_no_hardcover_client_sends_nothing(self, bot, thread):
        bot.hardcover = None
        await bot._send_embeds_for_mentioned_books("**Dune**", thread, "n")
        assert thread.send.await_count == 0

    @pytest.mark.asyncio
    async def test_missing_thread_still_resolves_without_crashing(self, bot):
        bot.hardcover.execute = AsyncMock(return_value=hardcover_hit(DUNE))
        await bot._send_embeds_for_mentioned_books("**Dune**", None, "n")


class TestMentionedTitleAliasing:
    """The cache keys on the *resolved* title. Without also recording the
    phrasing Marty used, "Dune" re-queries Hardcover every turn even though
    "Dune: A Novel" is already embedded."""

    @pytest.mark.asyncio
    async def test_repeat_mention_does_not_requery(self, bot, thread):
        resolved = {"title": "Dune: A Novel", "author": "Frank Herbert"}
        bot.hardcover.execute = AsyncMock(return_value=hardcover_hit(resolved))

        await bot._send_embeds_for_mentioned_books("**Dune**", thread, "n")
        await bot._send_embeds_for_mentioned_books("**Dune**", thread, "n")

        assert bot.hardcover.execute.await_count == 1
        assert thread.send.await_count == 1

    @pytest.mark.asyncio
    async def test_tool_path_then_prose_path_sends_once(self, bot, thread):
        bot.hardcover.execute = AsyncMock(return_value=hardcover_hit(DUNE))

        await bot._send_book_embeds(tool_result("search_books", [DUNE]), thread, "n")
        await bot._send_embeds_for_mentioned_books("**Dune**", thread, "n")

        assert thread.send.await_count == 1

    @pytest.mark.asyncio
    async def test_separate_threads_each_get_their_own_embed(self, bot):
        bot.hardcover.execute = AsyncMock(return_value=hardcover_hit(DUNE))
        first, second = make_thread(1), make_thread(2)

        await bot._send_embeds_for_mentioned_books("**Dune**", first, "n")
        await bot._send_embeds_for_mentioned_books("**Dune**", second, "n")

        assert first.send.await_count == 1
        assert second.send.await_count == 1


class TestEmitBookEmbedFailure:
    @pytest.mark.asyncio
    async def test_failed_send_is_retryable(self, bot, thread):
        # A send that errored never reached the channel, so the title must not
        # stay marked as embedded or the retry is silently dropped.
        thread.send = AsyncMock(side_effect=Exception("discord 500"))
        assert await bot._emit_book_embed(DUNE, thread, "n") is False

        thread.send = AsyncMock()
        assert await bot._emit_book_embed(DUNE, thread, "n") is True

    @pytest.mark.asyncio
    async def test_untitled_book_is_not_embedded(self, bot, thread):
        assert await bot._emit_book_embed({"author": "Nobody"}, thread, "n") is False
        assert thread.send.await_count == 0
