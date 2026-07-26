"""Which channel id a conversation is keyed to.

Keying on the parent channel gave every thread in a channel one shared,
never-ending conversation, so a fresh thread opened carrying history from an
unrelated one. These lock in the routing: a thread keys on itself, a top-level
mention keys on the channel until the thread exists, then moves onto it.
"""

from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from src.discord_bot.bot import MartyBot

CHANNEL_ID = 111
THREAD_ID = 222


@pytest.fixture(autouse=True)
def bot_user():
    """`Client.user` is a read-only property, so it has to be patched on the
    class rather than assigned on the instance."""
    user = MagicMock(name="bot-user")
    with patch.object(MartyBot, "user", new_callable=PropertyMock, return_value=user):
        yield user


def make_bot():
    with patch("src.discord_bot.bot.HardcoverTool", MagicMock()):
        with patch.object(MartyBot, "__init__", lambda self: None):
            bot = MartyBot()
    bot._embedded_books = {}
    bot._renamed_threads = set()
    bot.hardcover = MagicMock()
    return bot


def make_message(bot, *, in_bot_thread: bool):
    """A mention in a bot-owned thread, or a top-level mention in a channel."""
    channel = MagicMock()
    channel.id = THREAD_ID if in_bot_thread else CHANNEL_ID
    channel.owner = bot.user if in_bot_thread else MagicMock(name="someone-else")
    channel.parent = MagicMock()
    channel.parent.id = CHANNEL_ID

    @asynccontextmanager
    async def typing():
        yield

    channel.typing = typing

    message = MagicMock()
    message.channel = channel
    message.author.id = 42
    message.author.display_name = "nachi"
    message.content = "hey marty"
    message.guild.id = 999
    message.reply = AsyncMock()

    thread = MagicMock()
    thread.id = THREAD_ID
    thread.send = AsyncMock()
    message.create_thread = AsyncMock(return_value=thread)
    return message, thread


@asynccontextmanager
async def fake_session(db):
    yield db


@contextmanager
def bot_deps(conversation, db, **overrides):
    """Patch every collaborator `process_marty_message` reaches for and hand
    the mocks back so tests can assert on the calls directly."""
    mocks = {
        "get_customer_by_discord_id": AsyncMock(return_value=MagicMock(id="1")),
        "get_active_conversation": AsyncMock(return_value=conversation),
        "create_conversation": AsyncMock(return_value=conversation),
        "get_conversation_messages": AsyncMock(return_value=[]),
        "add_message": AsyncMock(),
        "generate_ai_response": AsyncMock(return_value=("sure thing", [])),
    }
    mocks.update(overrides)

    patches = [patch("src.discord_bot.bot.get_db_session", lambda: fake_session(db))]
    patches += [patch(f"src.discord_bot.bot.{k}", v) for k, v in mocks.items()]

    for p in patches:
        p.start()
    try:
        yield mocks
    finally:
        for p in patches:
            p.stop()


def stored(direction, content):
    row = MagicMock()
    row.direction = direction
    row.content = content
    row.timestamp = datetime.now(UTC)
    return row


@pytest.fixture
def conversation():
    convo = MagicMock()
    convo.id = "7"
    convo.discord_channel_id = str(CHANNEL_ID)
    return convo


@pytest.fixture
def db():
    session = MagicMock()
    session.commit = AsyncMock()
    return session


class TestConversationLookupScope:
    @pytest.mark.asyncio
    async def test_thread_message_keys_on_the_thread(self, conversation, db):
        bot = make_bot()
        message, _ = make_message(bot, in_bot_thread=True)

        with bot_deps(conversation, db) as mocks:
            await bot.process_marty_message(message)

        lookup = mocks["get_active_conversation"]
        assert lookup.await_args.kwargs["channel_id"] == str(THREAD_ID)

    @pytest.mark.asyncio
    async def test_top_level_mention_keys_on_the_channel(self, conversation, db):
        bot = make_bot()
        message, _ = make_message(bot, in_bot_thread=False)

        with bot_deps(conversation, db) as mocks:
            await bot.process_marty_message(message)

        lookup = mocks["get_active_conversation"]
        assert lookup.await_args.kwargs["channel_id"] == str(CHANNEL_ID)

    @pytest.mark.asyncio
    async def test_parent_channel_is_never_used_for_a_thread(self, conversation, db):
        """The bug this replaced: threads resolving to their parent channel."""
        bot = make_bot()
        message, _ = make_message(bot, in_bot_thread=True)

        with bot_deps(conversation, db) as mocks:
            await bot.process_marty_message(message)

        lookup = mocks["get_active_conversation"]
        assert lookup.await_args.kwargs["channel_id"] != str(CHANNEL_ID)

    @pytest.mark.asyncio
    async def test_new_conversation_is_created_on_the_same_key(self, conversation, db):
        bot = make_bot()
        message, _ = make_message(bot, in_bot_thread=True)

        with bot_deps(
            conversation, db, get_active_conversation=AsyncMock(return_value=None)
        ) as mocks:
            await bot.process_marty_message(message)

        created = mocks["create_conversation"].await_args.args[1]
        assert created.discord_channel_id == str(THREAD_ID)


class TestConversationMovesOntoThread:
    @pytest.mark.asyncio
    async def test_channel_id_is_rekeyed_after_thread_creation(self, conversation, db):
        """The opening mention keys to the channel because no thread exists yet.
        Once one does, the conversation moves onto it so replies continue it and
        the next mention in the channel starts fresh."""
        bot = make_bot()
        message, thread = make_message(bot, in_bot_thread=False)

        with bot_deps(conversation, db):
            await bot.process_marty_message(message)

        assert conversation.discord_channel_id == str(thread.id)
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_thread_reply_does_not_rekey(self, conversation, db):
        """Already in a thread, so there is nothing to move."""
        bot = make_bot()
        message, _ = make_message(bot, in_bot_thread=True)
        conversation.discord_channel_id = str(THREAD_ID)

        with bot_deps(conversation, db):
            await bot.process_marty_message(message)

        assert conversation.discord_channel_id == str(THREAD_ID)
        message.create_thread.assert_not_awaited()


class TestHistoryIsScopedToTheConversation:
    @pytest.mark.asyncio
    async def test_history_is_fetched_for_the_resolved_conversation(
        self, conversation, db
    ):
        bot = make_bot()
        message, _ = make_message(bot, in_bot_thread=True)

        with bot_deps(conversation, db) as mocks:
            await bot.process_marty_message(message)

        assert mocks["get_conversation_messages"].await_args.args[1] == conversation.id

    @pytest.mark.asyncio
    async def test_history_reaches_the_model_in_chronological_order(
        self, conversation, db
    ):
        bot = make_bot()
        message, _ = make_message(bot, in_bot_thread=True)

        # Stored newest-first, so the bot reverses before handing it to the model.
        rows = [stored("outbound", "second"), stored("inbound", "first")]

        with bot_deps(
            conversation, db, get_conversation_messages=AsyncMock(return_value=rows)
        ) as mocks:
            await bot.process_marty_message(message)

        history = mocks["generate_ai_response"].await_args.kwargs[
            "conversation_history"
        ]
        assert [m.content for m in history] == ["first", "second"]
        assert [m.role for m in history] == ["user", "assistant"]

    @pytest.mark.asyncio
    async def test_empty_history_is_passed_through(self, conversation, db):
        bot = make_bot()
        message, _ = make_message(bot, in_bot_thread=True)

        with bot_deps(conversation, db) as mocks:
            await bot.process_marty_message(message)

        assert (
            mocks["generate_ai_response"].await_args.kwargs["conversation_history"]
            == []
        )
