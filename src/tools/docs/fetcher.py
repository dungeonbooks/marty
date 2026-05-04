"""Fetch and parse markdown docs from dungeonbooks/docs.

Uses raw.githubusercontent.com directly. No GitHub API auth, no PAT, read-only.
In-memory TTL cache. The publish gate (`publish: true` frontmatter) is enforced
here as a safety belt — the system-prompt index should already filter drafts
out so Claude never asks for them, but unpublished slugs raise rather than
return content if asked for directly.
"""

import asyncio
import re
import time
from dataclasses import dataclass

import aiohttp
import yaml

DOCS_BASE_URL = "https://raw.githubusercontent.com/dungeonbooks/docs/main"
CACHE_TTL_SECONDS = 15 * 60
HTTP_TIMEOUT_SECONDS = 5

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)", re.DOTALL)
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
    def __init__(self, ttl: float) -> None:
        self.ttl = ttl
        self._store: dict[str, DocPayload] = {}
        self._lock = asyncio.Lock()

    def get(self, slug: str) -> DocPayload | None:
        payload = self._store.get(slug)
        if payload is None:
            return None
        if time.time() - payload.fetched_at > self.ttl:
            return None
        return payload

    def set(self, slug: str, payload: DocPayload) -> None:
        self._store[slug] = payload

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


async def fetch_doc(slug: str, *, force: bool = False) -> DocPayload:
    """Fetch a published doc by slug.

    Raises DocNotFoundError on 404, DocNotPublishedError if the file exists
    but lacks `publish: true` frontmatter.
    """
    if not force:
        cached = _cache.get(slug)
        if cached is not None:
            return cached

    url = f"{DOCS_BASE_URL}/{slug}.md"
    timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)

    async with aiohttp.ClientSession() as session, session.get(
        url, timeout=timeout
    ) as resp:
        if resp.status == 404:
            raise DocNotFoundError(slug)
        resp.raise_for_status()
        raw = await resp.text()

    payload = _parse(slug, raw)
    if payload.frontmatter.get("publish") is not True:
        raise DocNotPublishedError(slug)

    _cache.set(slug, payload)
    return payload


async def fetch_index() -> DocPayload:
    """Fetch the root index.md. Used by system-prompt assembly at boot."""
    return await fetch_doc("index")


def clear_cache() -> None:
    _cache.clear()
