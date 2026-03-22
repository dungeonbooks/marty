import asyncio
import logging
import time

import aiohttp

logger = logging.getLogger(__name__)


class Card:
    def __init__(
        self, name, price, url, mana_cost, image, type_line, oracle_text
    ) -> None:
        self.name = name
        self.price = price
        self.url = url
        self.mana_cost = mana_cost
        self.image = image
        self.type_line = type_line
        self.oracle_text = oracle_text

    @classmethod
    def from_scryfall(cls, data):
        return cls(
            name=data.get("name"),
            price=data.get("prices", {}).get("usd"),
            url=data.get("scryfall_uri"),
            mana_cost=data.get("mana_cost"),
            image=data.get("image_uris", {}).get("normal"),
            type_line=data.get("type_line"),
            oracle_text=data.get("oracle_text"),
        )


# Basic rate limiter: algorithmic optimization unlikely to needed here
class RateLimiter:
    def __init__(self, min_interval: float):
        """min_interval: minimum seconds between calls"""
        self.min_interval = min_interval
        self.last_call = 0
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            elapsed = time.time() - self.last_call
            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)
            self.last_call = time.time()


# Scryfall limits roughly 10 calls per second
api_limiter = RateLimiter(min_interval=0.1)


async def fetch_scryfall(session: aiohttp.ClientSession, search_string: str):
    async with session.get(
        url="https://api.scryfall.com/cards/named",
        params={"fuzzy": search_string},
        timeout=aiohttp.ClientTimeout(total=3),
        raise_for_status=False,
    ) as resp:
        if resp.status == 404:
            return None

        resp.raise_for_status()
        return await resp.json()


async def get_scryfall_data(search_string: str):
    await api_limiter.acquire()

    try:
        async with aiohttp.ClientSession() as session:
            return await fetch_scryfall(session, search_string)

    except TimeoutError:
        logger.warning(f"Timeout searching for: {search_string}")
        return None

    except aiohttp.ClientResponseError as e:
        logger.warning(f"API error {e.status} for '{search_string}': {e.message}")
        return None

    except aiohttp.ClientError as e:
        logger.warning(f"Network error searching for '{search_string}': {e}")
        return None

    except Exception as e:
        logger.warning(f"Unexpected error searching for '{search_string}': {e}")
        return None


async def search_card(search_string: str) -> Card | None:
    data = await get_scryfall_data(search_string)
    if data is None:
        return None
    return Card.from_scryfall(data)
