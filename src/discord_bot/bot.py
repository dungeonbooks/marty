import os
import re
from datetime import UTC, datetime
from typing import Any

import discord  # type: ignore
import structlog
from discord import app_commands  # type: ignore
from discord.ext import commands  # type: ignore

from ..ai_client import ConversationMessage, generate_ai_response
from ..config import config
from ..database import (
    ConversationCreate,
    CustomerCreate,
    MessageCreate,
    add_message,
    create_conversation,
    create_customer,
    get_active_conversation,
    get_conversation_messages,
    get_customer_by_discord_id,
    get_db_session,
)
from ..tools.external.hardcover import HardcoverTool
from ..tools.scryfall.cards import Card, search_card
from .embeds import create_book_embed, create_recent_releases_embed
from .feeds import FeedsCog
from .mtg import CardsCog, build_card_embed, send_card_reply

logger = structlog.get_logger(__name__)


# These return many books and are presented as a condensed list, not as one
# embed per title.
_LIST_BOOK_ACTIONS = frozenset({"get_trending_books", "get_recent_releases"})


# Marty bolds book titles and nothing else (prompt style rule 4), so **...**
# is the marker for "he just named a book".
_BOLD_TITLE = re.compile(r"\*\*([^*\n]{3,80})\*\*")

# Two embeds is already a wall; past that it buries the reply.
_MAX_AUTO_EMBEDS = 2

# The per-thread embed record is bookkeeping, not state worth keeping. Bounded
# so a long-lived bot does not retain a set for every thread it has ever seen.
_MAX_TRACKED_THREADS = 500


def _normalize_title(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _titles_match(mentioned: str, resolved: str) -> bool:
    """Guard against a search returning a confidently wrong book.

    Without this, a bolded phrase that is not a book resolves to whatever
    Hardcover ranks first and Marty appears to cite a title he never named.
    """
    a, b = _normalize_title(mentioned), _normalize_title(resolved)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    at, bt = set(a.split()), set(b.split())
    return len(at & bt) / max(len(at), len(bt)) >= 0.6


def _is_embeddable(book: dict) -> bool:
    """Whether a record carries enough to be worth showing as an embed.

    Hardcover carries stub records - a title someone created with no author,
    cover or rating. Rendering one produces an embed reading "by []" with a
    single Links field, which looks broken next to a real result.
    """
    if not book.get("title"):
        return False
    # cached_contributors is create_book_embed's author fallback, so a record
    # carrying only that still renders correctly and must not be filtered out.
    return any(
        book.get(k)
        for k in ("author", "cached_contributors", "image", "rating", "description")
    )


async def search_book_shared(hardcover_tool, query: str):
    """Shared logic for book search commands."""
    if not query.strip():
        return None, "need a book title or something to search for"

    try:
        result = await hardcover_tool.execute(
            action="search_books", query=query, limit=1
        )

        if not result.success or not result.data:
            return (
                None,
                f"hmm that book might exist in another dimension, lemme double check '{query}'",
            )

        book_data = result.data[0]
        embed = create_book_embed(book_data)
        return embed, None

    except Exception as e:
        logger.error(f"Error in shared book search: {e}")
        return None, "search spell malfunctioned, try that again"


async def get_recent_releases_shared(hardcover_tool):
    """Shared logic for recent releases commands."""
    try:
        result = await hardcover_tool.execute(action="get_recent_releases", limit=10)

        if not result.success or not result.data:
            return None, "couldn't find any recent releases right now, try again later"

        books = result.data
        if not books:
            return None, "no recent releases found, that's weird"

        # Use centralized embed creation function
        embed = create_recent_releases_embed(books)
        return embed, None

    except Exception as e:
        logger.error(f"Error in shared recent releases: {e}")
        return None, "recent releases spell malfunctioned, try that again"


async def search_card_shared(query: str):
    """Shared logic for card search commands."""
    if not query.strip():
        return None, "need a card name to search for"

    try:
        card = await search_card(query)
        if card is None:
            return None, f"couldn't find a card called '{query}'"
        return card, None

    except Exception as e:
        logger.exception("Error in shared card search: %s", e)
        return None, "scrying spell malfunctioned, try that again"


class MartyBot(commands.Bot):
    """Discord bot for Marty, the AI bookstore assistant."""

    def __init__(self) -> None:
        intents = discord.Intents.default()  # type: ignore
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self._renamed_threads: set[int] = set()
        self._embedded_books: dict[int, set[str]] = {}

        # Initialize Hardcover API tool
        try:
            self.hardcover = HardcoverTool()
        except Exception as e:
            logger.error(f"Failed to initialize Hardcover API: {e}")
            self.hardcover = None

    async def on_ready(self) -> None:
        """Called when the bot has finished logging in and setting up."""
        logger.info(f"{self.user} has connected to Discord!")

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")

    async def on_message(self, message: Any) -> None:
        """Handle incoming Discord messages."""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Ignore messages that start with command prefix
        if message.content.startswith(self.command_prefix):
            await self.process_commands(message)
            return

        # Check if this is a message in a thread created by the bot
        is_bot_thread = (
            hasattr(message.channel, "owner") and message.channel.owner == self.user
        )

        # Ignore replies to bot messages (e.g. /book responses)
        if message.reference and not is_bot_thread:
            return

        # Only respond to @ mentions, DMs, or messages in bot's threads
        if not (
            self.user.mentioned_in(message)
            or isinstance(message.channel, discord.DMChannel)
            or is_bot_thread
        ):
            return

        # Check if user has any assigned role (skip for DMs and dev environment)
        if not isinstance(message.channel, discord.DMChannel):
            # Skip role check in development environment
            if os.getenv("ENV") != "dev":
                # Allow anyone with any role (excluding @everyone)
                user_roles = [
                    role for role in message.author.roles if role.name != "@everyone"
                ]

                if not user_roles:
                    await message.reply(
                        "sorry, i'm only available to members with assigned roles right now. ping `@nachi` if you need access."
                    )
                    return

        # Process the message through Marty's AI system
        await self.process_marty_message(message)

    async def process_marty_message(self, message: Any) -> None:
        """Process a Discord message through Marty's conversation system."""
        user_id = str(message.author.id)
        username = message.author.display_name
        user_message = message.content
        channel_id = str(message.channel.id)
        guild_id = str(message.guild.id) if message.guild else None

        # Scope history to the thread. Keying on the parent channel instead gave
        # every thread in a channel one shared, never-ending conversation, so a
        # fresh thread opened with history from an unrelated one 20 minutes
        # earlier and Marty answered with "already got u covered just above".
        # A thread is Discord's own topic boundary; a top-level mention that
        # starts one keys on the channel until the thread exists.
        conversation_channel_id = channel_id

        logger.info(
            f"Processing Discord message from {username} ({user_id}): {user_message}"
        )

        try:
            async with message.channel.typing():
                async with get_db_session() as db:
                    # Get or create customer
                    customer = await get_customer_by_discord_id(db, user_id)
                    if not customer:
                        customer_data = CustomerCreate(
                            discord_user_id=user_id,
                            discord_username=username,
                            platform="discord",
                        )
                        customer = await create_customer(db, customer_data)
                        logger.info(f"Created new customer for Discord user {username}")

                    # Get or create active conversation
                    # Use parent channel ID for thread conversations to maintain history
                    conversation = await get_active_conversation(
                        db,
                        user_id,
                        platform="discord",
                        channel_id=conversation_channel_id,
                    )
                    if not conversation:
                        conversation_data = ConversationCreate(
                            customer_id=customer.id,
                            discord_user_id=user_id,
                            discord_channel_id=conversation_channel_id,
                            discord_guild_id=guild_id,
                            platform="discord",
                            status="active",
                        )
                        conversation = await create_conversation(db, conversation_data)
                        logger.info(
                            f"Created new conversation for Discord user {username}"
                        )

                    # Get recent conversation history FIRST (before saving new message)
                    recent_messages = await get_conversation_messages(
                        db, conversation.id, limit=config.CONVERSATION_HISTORY_LIMIT
                    )

                    # Convert to ConversationMessage format (reverse for chronological order)
                    conversation_history = []
                    for msg in reversed(
                        recent_messages
                    ):  # Reverse to get chronological order
                        conversation_history.append(
                            ConversationMessage(
                                role="user"
                                if msg.direction == "inbound"
                                else "assistant",
                                content=msg.content,
                                timestamp=msg.timestamp,
                            )
                        )

                    # Save the incoming message AFTER getting history
                    incoming_message = MessageCreate(
                        conversation_id=conversation.id,
                        direction="inbound",
                        content=user_message,
                    )
                    await add_message(db, incoming_message)

                    logger.debug(
                        f"Conversation history: {len(conversation_history)} messages"
                    )
                    for i, msg in enumerate(
                        conversation_history[-3:]
                    ):  # Show last 3 messages
                        logger.debug(f"  {i}: {msg.role}: {msg.content[:50]}...")

                    # Prepare customer context
                    customer_context = {
                        "customer_id": customer.id,
                        "discord_user_id": user_id,
                        "discord_username": username,
                        "name": customer.name or username,
                        "current_time": datetime.now(UTC).strftime("%I:%M %p"),
                        "current_date": datetime.now(UTC).strftime("%B %d, %Y"),
                        "current_day": datetime.now(UTC).strftime("%A"),
                        "platform": "discord",
                    }

                    # Generate AI response
                    ai_response, tool_results = await generate_ai_response(
                        user_message=user_message,
                        conversation_history=conversation_history,
                        customer_context=customer_context,
                    )

                    # Save the response message to database
                    response_message = MessageCreate(
                        conversation_id=conversation.id,
                        direction="outbound",
                        content=ai_response,
                    )
                    await add_message(db, response_message)

                    # Send response to Discord
                    # Check if we need to create a thread for this conversation
                    is_bot_thread = (
                        hasattr(message.channel, "owner")
                        and message.channel.owner == self.user
                    )

                    if not is_bot_thread and not isinstance(
                        message.channel, discord.DMChannel
                    ):
                        # Create a thread for the conversation
                        try:
                            thread = await message.create_thread(name="Chat with Marty")
                            await thread.send(ai_response)

                            # The opening mention was keyed to the channel because
                            # the thread did not exist yet. Move the conversation
                            # onto the thread so replies continue it, and so the
                            # next mention in this channel starts fresh.
                            conversation.discord_channel_id = str(thread.id)
                            await db.commit()

                            # Handle any tool results (like thread renaming)
                            await self._handle_tool_results(
                                tool_results, thread, username
                            )
                            await self._send_embeds_for_mentioned_books(
                                ai_response, thread, username
                            )

                            logger.info(
                                f"Created thread and sent Discord response to {username}"
                            )
                        except Exception as thread_error:
                            logger.error(f"Failed to create thread: {thread_error}")
                            # Fallback to regular reply
                            await message.reply(ai_response)

                            # Handle tool results in fallback case too
                            try:
                                await self._handle_tool_results(
                                    tool_results, message.channel, username
                                )
                            except Exception as tool_error:
                                logger.warning(
                                    f"Failed to handle tool results in fallback: {tool_error}"
                                )

                            logger.info(
                                f"Sent Discord response to {username} (fallback)"
                            )
                    else:
                        # Already in thread or DM, reply normally
                        await message.reply(ai_response)

                        # Handle tool results for existing threads and DMs
                        if is_bot_thread or isinstance(
                            message.channel, discord.DMChannel
                        ):
                            await self._handle_tool_results(
                                tool_results, message.channel, username
                            )
                            await self._send_embeds_for_mentioned_books(
                                ai_response, message.channel, username
                            )

                        logger.info(f"Sent Discord response to {username}")

        except Exception as e:
            logger.error(f"Error processing Discord message from {username}: {e}")
            # Send error message in Marty's voice
            error_message = "sorry my brain's lagging, give me a moment"
            try:
                # Use same thread logic for error messages
                is_bot_thread = (
                    hasattr(message.channel, "owner")
                    and message.channel.owner == self.user
                )

                if not is_bot_thread and not isinstance(
                    message.channel, discord.DMChannel
                ):
                    # Try to create thread for error message too
                    try:
                        thread = await message.create_thread(name="Chat with Marty")
                        await thread.send(error_message)
                    except Exception:
                        # Fallback to regular reply
                        await message.reply(error_message)
                else:
                    await message.reply(error_message)
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")

    async def _handle_tool_results(
        self, tool_results: list[dict], thread, username: str
    ) -> None:
        """Handle tool results from AI response."""
        for tool_result in tool_results:
            tool_name = tool_result.get("tool_name")
            result = tool_result.get("result")

            if tool_name == "rename_thread" and result and result.success:
                try:
                    thread_name = result.data.get("thread_name")
                    thread_id = getattr(thread, "id", None)
                    if thread_name and hasattr(thread, "edit") and thread_id:
                        if thread_id in self._renamed_threads:
                            logger.debug(
                                f"Skipping thread rename (already renamed) for {username}"
                            )
                        else:
                            await thread.edit(name=thread_name)
                            self._renamed_threads.add(thread_id)
                            logger.info(
                                f"Renamed thread to '{thread_name}' for {username}"
                            )
                except Exception as e:
                    logger.warning(f"Failed to rename thread: {e}")

            elif tool_name == "hardcover_api" and result and result.success:
                try:
                    await self._send_book_embeds(tool_result, thread, username)
                except Exception as e:
                    logger.warning(f"Failed to send book embed: {e}")

            elif tool_name == "scryfall_api" and result and result.success:
                try:
                    await self._send_card_embed(tool_result, thread, username)
                except Exception as e:
                    logger.warning(f"Failed to send card embed: {e}")

    def _embedded_titles(self, thread_id: int | None) -> set[str] | None:
        """Titles already embedded in one thread, or None if it has no id.

        Returning None rather than falling back to a shared key keeps unrelated
        id-less channels from deduping against each other.
        """
        if thread_id is None:
            return None
        already = self._embedded_books.get(thread_id)
        if already is None:
            already = self._embedded_books[thread_id] = set()
            while len(self._embedded_books) > _MAX_TRACKED_THREADS:
                oldest = next(iter(self._embedded_books))
                self._embedded_books.pop(oldest)
        return already

    async def _emit_book_embed(self, book: dict, thread, username: str) -> bool:
        """Send one book embed, at most once per book per thread.

        Both embed paths funnel through here. A book Marty looks up is usually
        also a book he names, so without shared bookkeeping the tool-driven and
        prose-driven paths each sent their own copy of the same embed.
        """
        key = _normalize_title(book.get("title", ""))
        if not key:
            return False

        already = self._embedded_titles(getattr(thread, "id", None))
        if already is not None:
            if key in already:
                logger.debug("duplicate_book_embed_skipped", title=book.get("title"))
                return False
            already.add(key)

        try:
            await thread.send(embed=create_book_embed(book))
            logger.info("book_embed_sent", title=book.get("title"), username=username)
            return True
        except Exception as e:
            logger.error(f"Error sending book embed: {e}")
            if already is not None:
                already.discard(key)
            return False

    async def _send_embeds_for_mentioned_books(
        self, response_text: str, thread, username: str
    ) -> None:
        """Embed every real book Marty names, whether or not he called a tool.

        He answers from his own knowledge most of the time, so keying embeds off
        tool calls missed the common case. Resolving each bolded title also
        doubles as a reality check: a title that no catalogue carries gets no
        embed, which is the visible difference between a real recommendation and
        an invented one.
        """
        if not self.hardcover or thread is None:
            return

        already = self._embedded_titles(getattr(thread, "id", None))

        sent = 0
        for title in dict.fromkeys(_BOLD_TITLE.findall(response_text)):
            if sent >= _MAX_AUTO_EMBEDS:
                break

            mentioned_key = _normalize_title(title)
            if not mentioned_key:
                continue
            if already is not None and mentioned_key in already:
                continue

            try:
                result = await self.hardcover.execute(
                    action="search_books", query=title, limit=1
                )
            except Exception as e:
                logger.warning(f"Book lookup failed for '{title}': {e}")
                continue

            if not result.success or not result.data:
                logger.info("mentioned_book_unresolved", title=title)
                continue

            book = result.data[0]
            if not _is_embeddable(book) or not _titles_match(
                title, book.get("title", "")
            ):
                logger.info(
                    "mentioned_book_rejected",
                    title=title,
                    resolved=book.get("title"),
                )
                continue

            if await self._emit_book_embed(book, thread, username):
                sent += 1
                # The cache keys on the resolved title, so record the phrasing
                # Marty used as well. Otherwise "Dune" re-queries Hardcover on
                # every turn even though "Dune: A Novel" is already embedded.
                if already is not None:
                    already.add(mentioned_key)

    async def _send_book_embeds(self, tool_result: dict, thread, username: str) -> None:
        """Send book embeds for Hardcover API results."""
        result = tool_result.get("result")
        tool_input = tool_result.get("tool_input", {})
        action = tool_input.get("action", "")

        if not result or not result.success or not result.data:
            return

        # The embed is how a book gets shown, so anything that resolves to a
        # specific book should produce one. Listing the actions individually
        # meant search_books_intelligent - the one the prompt tells Marty to
        # reach for first - silently produced no embed at all.
        if action in _LIST_BOOK_ACTIONS:
            # Own presentation elsewhere (condensed list), not one embed each.
            return

        if isinstance(result.data, dict):
            candidates = [result.data]
        elif isinstance(result.data, list):
            candidates = [b for b in result.data if isinstance(b, dict)]
        else:
            return

        # Several results means a search, and only the top hit is the subject.
        limit = len(candidates) if action == "get_books_by_ids" else 1
        books_data = [b for b in candidates if _is_embeddable(b)][:limit]

        if not books_data:
            logger.info(
                "no_embeddable_book",
                action=action,
                candidates=len(candidates),
                detail="results lacked the metadata an embed needs",
            )
            return

        # Send embeds for books (limit to 3 to avoid spam)
        for book_data in books_data[:3]:
            if book_data and isinstance(book_data, dict):
                await self._emit_book_embed(book_data, thread, username)

    async def _send_card_embed(self, tool_result: dict, thread, username: str) -> None:
        """Send a card embed for Scryfall API results."""
        result = tool_result.get("result")

        if not result or not result.success or not result.data:
            return

        card_data = result.data
        if not isinstance(card_data, dict):
            return

        try:
            card = Card(
                name=card_data.get("name"),
                price=card_data.get("price"),
                url=card_data.get("url"),
                mana_cost=card_data.get("mana_cost"),
                image=card_data.get("image"),
                type_line=card_data.get("type_line"),
                oracle_text=card_data.get("oracle_text"),
                power=card_data.get("power"),
                toughness=card_data.get("toughness"),
                rarity=card_data.get("rarity"),
                set_name=card_data.get("set_name"),
                scryfall_id=card_data.get("scryfall_id"),
            )
            embed = await build_card_embed(card, self)
            await thread.send(embed=embed)
            logger.info(f"Sent card embed for '{card.name}' to {username}")
        except Exception as e:
            logger.error(f"Error creating card embed: {e}")


def create_bot() -> MartyBot:
    """Create and return a MartyBot instance."""
    bot = MartyBot()

    @bot.command()
    async def book(ctx: commands.Context, *, query: str) -> None:
        """Search for a book and display its information using Hardcover API."""
        if not bot.hardcover:
            await ctx.send("search spell's broken rn, try again later")
            return

        async with ctx.typing():
            embed, error_msg = await search_book_shared(bot.hardcover, query)

            if error_msg:
                await ctx.send(error_msg)
                return

            await ctx.send(embed=embed)
            logger.info("Sent book embed via !book command")

    @bot.command()
    async def recent(ctx: commands.Context) -> None:
        """Show recent book releases using Hardcover API."""
        if not bot.hardcover:
            await ctx.send("search spell's broken rn, try again later")
            return

        async with ctx.typing():
            embed, error_msg = await get_recent_releases_shared(bot.hardcover)

            if error_msg:
                await ctx.send(error_msg)
                return

            await ctx.send(embed=embed)
            logger.info("Sent recent releases via !recent command")

    @bot.tree.command(
        name="book", description="Search for a book and get detailed information"
    )
    @app_commands.describe(query="Book title or author to search for")
    async def book_slash(interaction: discord.Interaction, query: str) -> None:
        """Slash command version of book search."""
        if not bot.hardcover:
            await interaction.response.send_message(
                "search spell's broken rn, try again later", ephemeral=True
            )
            return

        await interaction.response.defer()

        embed, error_msg = await search_book_shared(bot.hardcover, query)

        if error_msg:
            await interaction.followup.send(error_msg)
            return

        await interaction.followup.send(embed=embed)
        logger.info("Sent book embed via /book slash command")

    @bot.tree.command(
        name="recent", description="Show the 10 most recent book releases in a list"
    )
    async def recent_slash(interaction: discord.Interaction) -> None:
        """Slash command to show recent book releases in a grid format."""
        if not bot.hardcover:
            await interaction.response.send_message(
                "search spell's broken rn, try again later", ephemeral=True
            )
            return

        await interaction.response.defer()

        embed, error_msg = await get_recent_releases_shared(bot.hardcover)

        if error_msg:
            await interaction.followup.send(error_msg)
            return

        await interaction.followup.send(embed=embed)
        logger.info("Sent recent releases via /recent slash command")

    @bot.command()
    async def card(ctx: commands.Context, *, query: str) -> None:
        """Search for an MTG card and display its information."""
        async with ctx.typing():
            card_result, error_msg = await search_card_shared(query)

            if error_msg:
                await ctx.send(error_msg)
                return

            await send_card_reply(ctx.message, card_result, bot)
            logger.info("Sent card embed via !card command")

    @bot.tree.command(name="card", description="Search for an MTG card and get details")
    @app_commands.describe(query="Card name to search for")
    async def card_slash(interaction: discord.Interaction, query: str) -> None:
        """Slash command to search for an MTG card."""
        from .mtg import build_card_embed

        await interaction.response.defer()

        card_result, error_msg = await search_card_shared(query)

        if error_msg:
            await interaction.followup.send(error_msg)
            return

        embed = await build_card_embed(card_result, bot)
        await interaction.followup.send(embed=embed)
        logger.info("Sent card embed via /card slash command")

    async def setup():
        await bot.add_cog(CardsCog(bot))
        await bot.add_cog(FeedsCog(bot))

    bot.setup_hook = setup  # ty: ignore[invalid-assignment]

    return bot


async def run_bot() -> None:
    """Run the Discord bot."""
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable is required")

    bot = create_bot()
    await bot.start(token)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_bot())
