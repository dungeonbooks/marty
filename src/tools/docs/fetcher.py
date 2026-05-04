"""Fetch and parse markdown docs from dungeonbooks/docs.

Uses raw.githubusercontent.com directly. No GitHub API auth, no PAT, read-only.
In-memory TTL cache with single-lock refill and stale-on-network-failure
fallback. The publish gate (`publish: true` frontmatter) is enforced here as a
safety belt — the system-prompt index should already filter drafts out so
Claude never asks for them, but unpublished slugs raise rather than return
content if asked for directly.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass

import aiohttp
import yaml

logger = logging.getLogger(__name__)

DOCS_BASE_URL = "https://raw.githubusercontent.com/dungeonbooks/docs/main"
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


@dataclass
class DocPayload:
    slug: str
    frontmatter: dict
    body: str
    agent_guidance: list[str]
    fetched_at: float


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


def _parse(slug: str, raw: str) -> DocPayload:
    match = _FRONTMATTER_RE.match(raw)
    if match:
        frontmatter = yaml.safe_load(match.group(1)) or {}
        body = match.group(2)
    else:
        frontmatter = {}
        body = raw

    agent_guidance = [c.strip() for c in _HTML_COMMENT_RE.findall(body)]
    body_clean = _HTML_COMMENT_RE.sub("", body).strip()

    return DocPayload(
        slug=slug,
        frontmatter=frontmatter,
        body=body_clean,
        agent_guidance=agent_guidance,
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

    Includes the customer-facing body and the `agent_guidance` HTML-comment
    blocks. Claude reads both — the body gives him the slug list with
    one-line summaries; the agent_index comment gives him the canonical
    slug→summary mapping.
    """
    parts = [payload.body.strip()]
    parts.extend(g.strip() for g in payload.agent_guidance)
    return "\n\n".join(p for p in parts if p)


def clear_cache() -> None:
    _cache.clear()
