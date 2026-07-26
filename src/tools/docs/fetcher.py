"""Fetch and parse markdown docs from dungeonbooks/policies.

Uses raw.githubusercontent.com directly. No GitHub API auth, no PAT, read-only.
In-memory TTL cache with single-lock refill and stale-on-network-failure
fallback. The publish gate (`publish: true` frontmatter) is enforced here as a
safety belt — the system-prompt index should already filter drafts out so
Claude never asks for them, but unpublished slugs raise rather than return
content if asked for directly.
"""

import asyncio
import re
import time
from dataclasses import dataclass

import aiohttp
import structlog
import yaml

logger = structlog.get_logger(__name__)

DOCS_BASE_URL = "https://raw.githubusercontent.com/dungeonbooks/policies/main"
CACHE_TTL_SECONDS = 15 * 60
HTTP_TIMEOUT_SECONDS = 5

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
    # Agent-facing keys only, addressable by name. Different consumers want
    # different keys: get_doc reads `agent_guidance`, the index reads
    # `agent_index`. Human-only keys (todo, status) never appear here.
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
    for both bot directives (`agent_guidance`, `agent_index`) and human notes
    (`todo`, `status`). Only `agent_`-prefixed keys are returned.

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


async def fetch_doc(slug: str, *, force: bool = False) -> DocPayload:
    """Fetch a published doc by slug.

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

    Raises:
      - DocNotFoundError on 404 (file is gone, no point serving stale).
      - DocNotPublishedError if the file exists but lacks `publish: true`.
    """
    if not force:
        cached = _cache.get_fresh(slug)
        if cached is not None:
            return cached

    async with _cache.refill_lock():
        if not force:
            cached = _cache.get_fresh(slug)
            if cached is not None:
                return cached

        try:
            payload = await _fetch_remote(slug)
        except DocNotFoundError:
            raise
        except _TRANSIENT_FETCH_ERRORS as e:
            stale = _cache.get_stale(slug)
            if stale is not None:
                logger.warning(
                    f"docs fetch failed for {slug}: {e}; serving stale entry "
                    f"({int(time.time() - stale.fetched_at)}s old, "
                    f"grace {STALE_GRACE_SECONDS}s)"
                )
                _cache.touch(slug, STALE_GRACE_SECONDS)
                return stale
            raise

        if payload.frontmatter.get("publish") is not True:
            raise DocNotPublishedError(slug)

        _cache.set(slug, payload)
        return payload


async def fetch_index() -> DocPayload:
    """Fetch the root index.md. Used by system-prompt assembly."""
    return await fetch_doc("index")


def format_index_for_prompt(payload: DocPayload) -> str:
    """Render an index payload into a flat string for system-prompt injection.

    Includes the customer-facing body and the `agent_index` directive. The body
    gives the slug list with one-line summaries; `agent_index` gives the
    canonical slug→summary mapping.

    Reads `agent_index` by name rather than dumping every comment, so a `todo`
    or `status` block in index.md stays out of the system prompt.
    """
    parts = [payload.body.strip()]

    index = _as_lines(payload.agent_directives.get("agent_index"))
    if index:
        parts.append("agent_index:\n" + "\n".join(f"  {line}" for line in index))

    return "\n\n".join(p for p in parts if p)


def clear_cache() -> None:
    _cache.clear()
