"""RSS feed aggregator for #rpg-news Discord channel.

Polls RPG industry feeds weekly, deduplicates entries,
and posts a digest to the configured channel.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import aiohttp
import feedparser
import redis.asyncio as redis
from discord.ext import commands, tasks

from ..config import config

logger = logging.getLogger(__name__)

FEEDS = [
    {
        "name": "Questing Beast",
        "url": "https://questingbeast.substack.com/feed",
    },
    {
        "name": "Sabre Games OSR News",
        "url": "https://www.sabregamesandcards.com/blog/categories/osr-news/blog-feed.xml",
    },
    {
        "name": "Ten Foot Pole",
        "url": "https://tenfootpole.org/ironspike/?feed=rss2",
    },
]

FEED_ORDER = [feed["name"] for feed in FEEDS]

SEEN_KEY = "rss:seen"
HEADERS = {"User-Agent": "Marty-Bot/1.0 (Dungeon Books RSS aggregator)"}


@dataclass
class FeedEntry:
    title: str
    url: str
    source: str
    published: datetime | None
    summary: str
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


async def fetch_feed(session: aiohttp.ClientSession, feed: dict) -> list[FeedEntry]:
    """Fetch and parse a single RSS feed."""
    try:
        async with session.get(
            feed["url"], headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status != 200:
                logger.warning(f"Feed {feed['name']} returned {resp.status}")
                return []
            body = await resp.text()
    except Exception as e:
        logger.error(f"Failed to fetch {feed['name']}: {e}")
        return []

    parsed = feedparser.parse(body)
    logger.info(f"Feed {feed['name']}: {len(parsed.entries)} entries fetched")
    entries = []
    for entry in parsed.entries:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6], tzinfo=UTC)
            except (ValueError, TypeError):
                logger.warning(
                    f"Could not parse date for {entry.get('title', 'unknown')}"
                )

        if feed["name"] == "Ten Foot Pole":
            summary, tags = _parse_ten_foot_pole(entry)
        else:
            summary = _extract_summary(entry, feed["name"])
            tags = []

        entries.append(
            FeedEntry(
                title=entry.get("title", "Untitled"),
                url=entry.get("link", ""),
                source=feed["name"],
                published=published,
                summary=summary,
                tags=tags,
            )
        )

    return entries


def _parse_ten_foot_pole(entry) -> tuple[str, list[str]]:
    """Extract clean metadata and summary from Ten Foot Pole's content:encoded."""
    import re

    tags = [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")]

    # Try content:encoded first for structured metadata
    content = ""
    if hasattr(entry, "content") and entry.content:
        content = entry.content[0].get("value", "")

    meta_line = ""
    description = ""

    if content:
        # Metadata is in <pre class="wp-block-preformatted">By X<br>Publisher<br>System<br>Levels</pre>
        pre_match = re.search(
            r'<pre[^>]*class="wp-block-preformatted"[^>]*>(.*?)</pre>',
            content,
            re.DOTALL,
        )
        if pre_match:
            raw_meta = pre_match.group(1)
            parts = [
                _strip_html(p).strip()
                for p in re.split(r"<br\s*/?>", raw_meta)
                if _strip_html(p).strip()
            ]
            # Format: Author | Publisher | System | Levels
            meta_line = " · ".join(parts)

        # First real paragraph after the <pre> block
        paragraphs = re.findall(r"<p>(.*?)</p>", content, re.DOTALL)
        for p in paragraphs:
            clean = _strip_html(p).strip()
            # Skip paragraphs that are just links
            if clean and not clean.startswith("http"):
                description = clean
                break

    if not description:
        raw = getattr(entry, "summary", "")
        description = _strip_html(raw)

    # Truncate description
    if len(description) > 200:
        description = description[:197] + "..."

    summary = f"{meta_line}\n{description}" if meta_line else description
    return summary, tags


def _extract_summary(entry, feed_name: str) -> str:
    """Extract and truncate summary for non-Ten Foot Pole feeds."""
    raw = getattr(entry, "summary", "")
    summary = _strip_html(raw)

    limit = 300 if feed_name == "Sabre Games OSR News" else 200
    if len(summary) > limit:
        summary = summary[: limit - 3] + "..."
    return summary


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    import html
    import re

    clean = re.sub(r"<[^>]+>", "", text)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _format_digest(entries: list[FeedEntry]) -> str:
    """Format entries into a single Discord message."""
    if not entries:
        return ""

    grouped: dict[str, list[FeedEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.source, []).append(entry)

    lines = ["**RPG News Roundup**\n"]

    # Render in FEED_ORDER
    for source in FEED_ORDER:
        items = grouped.get(source)
        if not items:
            continue
        lines.append(f"__**{source}**__")
        for item in items[:10]:
            date_str = ""
            if item.published:
                date_str = f" ({item.published.strftime('%b %d')})"

            best = " ⭐" if "The Best" in item.tags else ""
            title_line = f"[{item.title}](<{item.url}>){date_str}{best}"

            if item.summary:
                lines.append(f"- {title_line}\n  {item.summary}")
            else:
                lines.append(f"- {title_line}")
        lines.append("")

    return "\n".join(lines)


class FeedsCog(commands.Cog):
    """Cog that polls RSS feeds and posts a weekly digest."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._redis: redis.Redis | None = None
        self._first_run_done = False

    async def cog_load(self) -> None:
        redis_url = config.REDIS_URL
        if redis_url:
            try:
                self._redis = redis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
                logger.info("Feeds cog connected to Redis for dedup")
            except Exception as e:
                logger.warning(
                    f"Redis unavailable for feeds dedup, will post all entries: {e}"
                )
                self._redis = None

        self.weekly_digest.start()
        logger.info("Feeds cog loaded, weekly digest scheduled")

    async def cog_unload(self) -> None:
        self.weekly_digest.cancel()
        if self._redis:
            await self._redis.aclose()

    async def _is_seen(self, url: str) -> bool:
        if not self._redis:
            return False
        return await self._redis.sismember(SEEN_KEY, url)

    async def _mark_seen(self, urls: list[str]) -> None:
        if not self._redis or not urls:
            return
        await self._redis.sadd(SEEN_KEY, *urls)
        # Keep the set from growing forever — expire entries after 90 days
        await self._redis.expire(SEEN_KEY, 90 * 24 * 3600)

    async def _fetch_new_entries(self, skip_dedup: bool = False) -> list[FeedEntry]:
        """Fetch all feeds and return only unseen entries."""
        all_entries: list[FeedEntry] = []

        async with aiohttp.ClientSession() as session:
            for feed in FEEDS:
                entries = await fetch_feed(session, feed)
                all_entries.extend(entries)

        # Filter to entries from the last 7 days
        cutoff = datetime.now(UTC) - timedelta(days=7)
        recent = [
            e for e in all_entries if e.published is None or e.published >= cutoff
        ]

        # Dedup against previously seen
        new_entries = []
        for entry in recent:
            if skip_dedup or not await self._is_seen(entry.url):
                new_entries.append(entry)

        # Sort by date (newest first), undated entries at the end
        new_entries.sort(
            key=lambda e: e.published or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )

        return new_entries

    async def _post_digest(
        self, channel_override=None, skip_dedup: bool = False
    ) -> None:
        """Fetch new entries and post digest.

        Args:
            channel_override: Post to this channel instead of #rpg-news.
            skip_dedup: If True, ignore seen entries (for manual testing).
        """
        channel = channel_override
        if not channel:
            channel_id = config.RPG_NEWS_CHANNEL_ID
            if not channel_id:
                logger.warning("RPG_NEWS_CHANNEL_ID not set, skipping digest")
                return
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Could not find channel {channel_id}")
                return

        new_entries = await self._fetch_new_entries(skip_dedup=skip_dedup)
        if not new_entries:
            logger.info("No new RSS entries to post")
            return

        message = _format_digest(new_entries)

        # Discord message limit is 2000 chars
        if len(message) > 2000:
            chunks = _split_message(message)
            for chunk in chunks:
                await channel.send(chunk)
        else:
            await channel.send(message)

        if not skip_dedup:
            await self._mark_seen([e.url for e in new_entries])
        logger.info(f"Posted {len(new_entries)} RSS entries")

    @tasks.loop(hours=168)  # 7 days
    async def weekly_digest(self) -> None:
        if not self._first_run_done:
            # Skip the immediate first invocation — only post on schedule
            self._first_run_done = True
            logger.info("Weekly digest loop started, first post in 7 days")
            return
        await self._post_digest()

    @weekly_digest.before_loop
    async def before_weekly_digest(self) -> None:
        await self.bot.wait_until_ready()

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def digest(self, ctx: commands.Context) -> None:
        """Manually trigger the RPG news digest (posts to current channel, skips dedup)."""
        async with ctx.typing():
            await self._post_digest(channel_override=ctx.channel, skip_dedup=True)


def _split_message(message: str, limit: int = 2000) -> list[str]:
    """Split a message into chunks that fit Discord's character limit."""
    chunks = []
    current = ""
    for line in message.split("\n"):
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks
