"""Fetch and parse markdown docs from the published policies site.

Reads https://docs.dungeonbooks.com, which Quartz builds from the policies
vault and Cloudflare Pages serves. The MarkdownSource emitter publishes each
page's source markdown beside its rendered HTML, so this is the same text the
author wrote, agent-guidance HTML comments included.

Reading the site rather than raw.githubusercontent.com is what lets the vault
repo be private: the site is public because Pages serves it, not because GitHub
does. It also means a page that failed the build is simply absent here, rather
than being served from a branch nobody has published yet.

No auth, no PAT, read-only.
In-memory TTL cache with single-lock refill and stale-on-network-failure
fallback. The publish gate (`publish: true` frontmatter) is enforced here as a
safety belt. The site build already drops anything without it, so an
unpublished slug 404s before this check can run, but the check stays: it costs
nothing and it is the last line if a build ever ships something it should not.
"""

import asyncio
import re
import time
from dataclasses import dataclass

import aiohttp
import structlog
import yaml

logger = structlog.get_logger(__name__)

DOCS_BASE_URL = "https://docs.dungeonbooks.com"
CACHE_TTL_SECONDS = 15 * 60
HTTP_TIMEOUT_SECONDS = 5

# The site's own index of published pages, one line per page with a one-line
# summary, written by the MarkdownSource emitter from each page's `description`
# frontmatter. This replaced the hand-kept `agent_index` comment in index.md:
# the summary now lives on the page it describes instead of in a second list
# that had to be updated alongside it.
#
# Safe as a cache key next to page slugs. A slug is a path with the extension
# dropped, so nothing else in the cache can be called "llms.txt".
INDEX_FILE = "llms.txt"

# When we serve a stale entry because the upstream is failing, treat that
# entry as fresh for this many seconds. Prevents concurrent and immediately-
# subsequent callers from each retrying against a broken upstream — they all
# get the same stale payload until the grace expires.
STALE_GRACE_SECONDS = 60

# Errors that justify falling back to a stale cached entry. Keep this narrow:
# parser/content errors should propagate so a bad doc commit surfaces loudly
# instead of being masked by the previous version.
_TRANSIENT_FETCH_ERRORS: tuple[type[Exception], ...] = (
    aiohttp.ClientError,
    asyncio.TimeoutError,
    ConnectionError,
)

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)

# One index entry: `- [Store](https://docs.dungeonbooks.com/store.md): Hours...`
# The description is optional because a page without one still belongs in the
# list; it just arrives unsummarised.
_INDEX_ENTRY_RE = re.compile(
    r"^-\s+\[(?P<title>[^\]]*)\]\((?P<url>[^)\s]+)\)(?:\s*:\s*(?P<description>.*))?$"
)


def _as_lines(value) -> list[str]:
    """Flatten a directive value to lines, whatever shape the author used.

    Authors write these by hand, so a key may hold a list, a bare string, or a
    mapping. Rendering all three the same way keeps a formatting slip in the
    vault from dropping a directive silently.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [line for line in (ln.strip() for ln in value.splitlines()) if line]
    if isinstance(value, dict):
        return [_pair(k, v) for k, v in value.items()]
    if isinstance(value, list):
        lines = []
        for item in value:
            # An unquoted directive containing ": " parses as a mapping rather
            # than a string, so a list entry can arrive as a dict. Render it
            # back to the sentence the author wrote instead of a dict repr.
            if isinstance(item, dict):
                lines.extend(_pair(k, v) for k, v in item.items())
            elif str(item).strip():
                lines.append(str(item).strip())
        return lines
    return [str(value)]


def _pair(key, value) -> str:
    """Render a mapping entry as the sentence the author wrote.

    `text: more text` parses to a key and a value, so both halves are joined
    back together. `text:` with nothing after it parses to a null value, and
    emitting "text: None" would put a word in the author's mouth.
    """
    return str(key).strip() if value is None else f"{key}: {value}".strip()


@dataclass
class DocPayload:
    slug: str
    frontmatter: dict
    body: str
    # Agent-facing keys only, addressable by name. `get_doc` reads
    # `agent_guidance`; the prefix admits others without a code change.
    # Human-only keys (todo, status) never appear here.
    agent_directives: dict
    fetched_at: float

    @property
    def agent_guidance(self) -> list[str]:
        """Per-doc directives, as a flat list of lines."""
        return _as_lines(self.agent_directives.get("agent_guidance"))


class DocNotFoundError(Exception):
    pass


class DocNotPublishedError(Exception):
    pass


class _Cache:
    """In-memory TTL cache with a single global refill lock.

    A single global lock instead of a per-slug dict avoids unbounded growth
    from one-off slug spam. Marty's actual workload (~5 published slugs,
    moderate Discord traffic) sees almost no contention; the lock is held
    for the duration of one HTTP round-trip during cache refills only.
    """

    def __init__(self, ttl: float) -> None:
        self.ttl = ttl
        self._store: dict[str, DocPayload] = {}
        self._refill_lock = asyncio.Lock()

    def get_fresh(self, slug: str) -> DocPayload | None:
        payload = self._store.get(slug)
        if payload is None:
            return None
        if time.time() - payload.fetched_at > self.ttl:
            return None
        return payload

    def get_stale(self, slug: str) -> DocPayload | None:
        return self._store.get(slug)

    def set(self, slug: str, payload: DocPayload) -> None:
        self._store[slug] = payload

    def touch(self, slug: str, grace_seconds: float) -> None:
        """Treat the cached entry as fresh for `grace_seconds` more.

        Used when serving stale on transient fetch failure: subsequent
        callers within the grace window get the same stale payload from
        the fast path instead of each issuing their own retry against
        the broken upstream.
        """
        entry = self._store.get(slug)
        if entry is None:
            return
        # Push fetched_at forward so (now - fetched_at) becomes ttl - grace.
        entry.fetched_at = time.time() - max(0.0, self.ttl - grace_seconds)

    def refill_lock(self) -> asyncio.Lock:
        return self._refill_lock

    def clear(self) -> None:
        self._store.clear()


_cache = _Cache(CACHE_TTL_SECONDS)


AGENT_KEY_PREFIX = "agent_"


def _parse_directives(slug: str, comments: list[str]) -> dict:
    """Extract agent-facing keys from a doc's HTML comments.

    Comments are the agent-only layer: Quartz strips them, so authors use them
    for both bot directives (`agent_guidance`) and human notes (`todo`,
    `status`). Only `agent_`-prefixed keys are returned.

    The prefix is the contract rather than a fixed list of key names, so a new
    directive works without a code change and a new human-only key stays private
    without one. Forgetting the prefix means the bot ignores a directive, which
    is visible the first time it is tested. The opposite default leaks internal
    notes into the prompt silently, which is what this replaces.
    """
    directives: dict = {}
    for comment in comments:
        try:
            parsed = yaml.safe_load(comment)
        except yaml.YAMLError as e:
            # Never fall back to passing the raw comment through: that is the
            # leak. A malformed comment loses its directives and says so.
            logger.warning(
                "doc_directives_unparseable",
                slug=slug,
                error=str(e),
                detail="agent directives dropped for this comment block",
            )
            continue

        if not isinstance(parsed, dict):
            continue

        for key, value in parsed.items():
            if not (isinstance(key, str) and key.startswith(AGENT_KEY_PREFIX)):
                continue
            # A page may split one directive across several comment blocks, so
            # a repeated key accumulates. Overwriting would drop the earlier
            # block silently, which is how guidance goes missing unnoticed.
            if key in directives:
                directives[key] = _merge_directive(directives[key], value)
            else:
                directives[key] = value

    return directives


def _merge_directive(existing, incoming):
    """Combine two values for the same directive key."""
    if isinstance(existing, dict) and isinstance(incoming, dict):
        return {**existing, **incoming}
    return _as_lines(existing) + _as_lines(incoming)


def _parse(slug: str, raw: str) -> DocPayload:
    match = _FRONTMATTER_RE.match(raw)
    if match:
        frontmatter = yaml.safe_load(match.group(1)) or {}
        body = match.group(2)
    else:
        frontmatter = {}
        body = raw

    body_clean = _HTML_COMMENT_RE.sub("", body).strip()

    return DocPayload(
        slug=slug,
        frontmatter=frontmatter,
        body=body_clean,
        agent_directives=_parse_directives(slug, _HTML_COMMENT_RE.findall(body)),
        fetched_at=time.time(),
    )


async def _fetch_remote(slug: str) -> DocPayload:
    """Single-flight remote fetch + parse. Raises DocNotFoundError on 404."""
    url = f"{DOCS_BASE_URL}/{slug}.md"
    timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)

    async with (
        aiohttp.ClientSession() as session,
        session.get(url, timeout=timeout) as resp,
    ):
        if resp.status == 404:
            raise DocNotFoundError(slug)
        resp.raise_for_status()
        raw = await resp.text()

    return _parse(slug, raw)


async def _fetch_cached(
    key: str,
    fetch_remote,
    validate=None,
    *,
    force: bool = False,
) -> DocPayload:
    """Fetch under the cache, with single-flight refill and stale fallback.

    Caching:
      - Fresh hit: return immediately, no network.
      - Expired or missing: acquire the global refill lock and refetch
        under lock so concurrent callers don't fan out duplicate requests.
      - Transient transport error during refetch: serve the stale cached
        entry if present and extend its freshness by STALE_GRACE_SECONDS,
        so the next callers within the grace window don't each retry.
        If no stale entry, propagate the error.
      - Parse / content errors propagate. A bad docs commit surfaces; we
        do not silently mask it with the previous version.

    `validate` runs before the result is cached, so a payload it rejects is
    refetched next time rather than being served from cache for a full TTL.
    """
    if not force:
        cached = _cache.get_fresh(key)
        if cached is not None:
            return cached

    async with _cache.refill_lock():
        if not force:
            cached = _cache.get_fresh(key)
            if cached is not None:
                return cached

        try:
            payload = await fetch_remote()
        except DocNotFoundError:
            raise
        except _TRANSIENT_FETCH_ERRORS as e:
            stale = _cache.get_stale(key)
            if stale is not None:
                logger.warning(
                    f"docs fetch failed for {key}: {e}; serving stale entry "
                    f"({int(time.time() - stale.fetched_at)}s old, "
                    f"grace {STALE_GRACE_SECONDS}s)"
                )
                _cache.touch(key, STALE_GRACE_SECONDS)
                return stale
            raise

        if validate is not None:
            validate(payload)

        _cache.set(key, payload)
        return payload


async def fetch_doc(slug: str, *, force: bool = False) -> DocPayload:
    """Fetch a published doc by slug.

    Raises:
      - DocNotFoundError on 404 (file is gone, no point serving stale).
      - DocNotPublishedError if the file exists but lacks `publish: true`.
    """

    def gate(payload: DocPayload) -> None:
        if payload.frontmatter.get("publish") is not True:
            raise DocNotPublishedError(slug)

    return await _fetch_cached(slug, lambda: _fetch_remote(slug), gate, force=force)


async def fetch_index() -> DocPayload:
    """Fetch the root index.md. Used by system-prompt assembly."""
    return await fetch_doc("index")


async def _fetch_page_index_remote() -> DocPayload:
    """Fetch llms.txt. Raises DocNotFoundError on 404."""
    url = f"{DOCS_BASE_URL}/{INDEX_FILE}"
    timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)

    async with (
        aiohttp.ClientSession() as session,
        session.get(url, timeout=timeout) as resp,
    ):
        if resp.status == 404:
            raise DocNotFoundError(INDEX_FILE)
        resp.raise_for_status()
        raw = await resp.text()

    # llms.txt is generated, not authored: no frontmatter to parse and no
    # comments to filter. It rides in a DocPayload only to reuse the cache.
    return DocPayload(
        slug=INDEX_FILE,
        frontmatter={},
        body=raw,
        agent_directives={},
        fetched_at=time.time(),
    )


async def fetch_page_index(*, force: bool = False) -> DocPayload:
    """Fetch llms.txt, the site's index of published pages.

    No publish gate. The file is emitted by the build from pages that already
    passed it, so there is nothing here to re-check, and llms.txt has no
    frontmatter to check it against.
    """
    return await _fetch_cached(INDEX_FILE, _fetch_page_index_remote, force=force)


@dataclass
class IndexEntry:
    slug: str
    title: str
    description: str | None


def parse_page_index(raw: str) -> list[IndexEntry]:
    """Parse llms.txt into entries.

    Only list lines are read. The heading and the site blurb above them are
    prose for a human or a crawler landing on the file, and re-injecting them
    would repeat what index.md already says in the prompt.

    A line that does not match is skipped rather than guessed at. The file is
    generated, so a non-matching line means the format changed, and inventing a
    slug from it would put a page in the prompt that cannot be fetched.
    """
    entries: list[IndexEntry] = []
    for line in raw.splitlines():
        match = _INDEX_ENTRY_RE.match(line.strip())
        if match is None:
            continue

        slug = _slug_from_url(match.group("url"))
        if not slug:
            continue

        description = (match.group("description") or "").strip()
        entries.append(
            IndexEntry(
                slug=slug,
                title=match.group("title").strip(),
                description=description or None,
            )
        )
    return entries


def _slug_from_url(url: str) -> str:
    """Recover a fetchable slug from an index link.

    Links are absolute, so the site prefix comes off. A link to some other host
    is dropped: `fetch_doc` builds its own URL from the slug, so keeping it
    would produce a slug that resolves to the wrong page or to nothing.
    """
    if url.startswith(("http://", "https://")):
        for prefix in (
            f"{DOCS_BASE_URL}/",
            f"{DOCS_BASE_URL.replace('https://', 'http://')}/",
        ):
            if url.startswith(prefix):
                url = url[len(prefix) :]
                break
        else:
            return ""

    if not url.endswith(".md"):
        return ""
    return url[: -len(".md")].strip("/")


def format_page_index(payload: DocPayload) -> str:
    """Render llms.txt into the slug→summary block for the system prompt."""
    entries = parse_page_index(payload.body)
    if not entries:
        return ""

    lines = [
        f"  {e.slug}: {e.description}" if e.description else f"  {e.slug}"
        for e in entries
    ]
    return "page_index:\n" + "\n".join(lines)


def format_index_for_prompt(
    payload: DocPayload, page_index: DocPayload | None = None
) -> str:
    """Render the docs index into a flat string for system-prompt injection.

    Two parts: index.md's customer-facing body, which says what the docs are and
    links the topics, and the slug→summary list from llms.txt, which is what
    Marty routes on when picking a page to fetch.

    The list used to come from an `agent_index` comment in index.md, maintained
    by hand beside the same summaries in each page's frontmatter. It is read
    from llms.txt now so there is one copy of a page's summary, on the page.
    `page_index` is optional so a failed index fetch degrades to the body alone
    rather than dropping the whole block.
    """
    parts = [payload.body.strip()]

    if page_index is not None:
        parts.append(format_page_index(page_index))

    return "\n\n".join(p for p in parts if p)


def clear_cache() -> None:
    _cache.clear()
