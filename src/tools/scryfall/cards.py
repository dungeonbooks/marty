import asyncio
import logging
import time

import aiohttp

logger = logging.getLogger(__name__)


class Card:
    def __init__(
        self,
        name,
        price,
        url,
        mana_cost,
        image,
        type_line,
        oracle_text,
        power,
        toughness,
        rarity,
        set_name,
        scryfall_id,
    ) -> None:
        self.name = name
        self.price = price
        self.url = url
        self.mana_cost = mana_cost
        self.image = image
        self.type_line = type_line
        self.oracle_text = oracle_text
        self.power = power
        self.toughness = toughness
        self.rarity = rarity
        self.set_name = set_name
        self.scryfall_id = scryfall_id

    @classmethod
    def from_scryfall(cls, data):
        image_uris = data.get("image_uris", {})
        image = image_uris.get("large") or image_uris.get("normal")
        return cls(
            name=data.get("name"),
            price=data.get("prices", {}).get("usd"),
            url=data.get("scryfall_uri"),
            mana_cost=data.get("mana_cost"),
            image=image,
            type_line=data.get("type_line"),
            oracle_text=data.get("oracle_text"),
            power=data.get("power"),
            toughness=data.get("toughness"),
            rarity=data.get("rarity"),
            set_name=data.get("set_name"),
            scryfall_id=data.get("id"),
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


async def fetch_scryfall(
    session: aiohttp.ClientSession,
    search_string: str,
    set_code: str | None = None,
    collector_number: str | None = None,
):
    timeout = aiohttp.ClientTimeout(total=3)

    if set_code and collector_number:
        url = f"https://api.scryfall.com/cards/{set_code}/{collector_number}"
        async with session.get(
            url=url, timeout=timeout, raise_for_status=False
        ) as resp:
            if resp.status == 404:
                return None
            resp.raise_for_status()
            return await resp.json()

    params = {"fuzzy": search_string}
    if set_code:
        params["set"] = set_code

    async with session.get(
        url="https://api.scryfall.com/cards/named",
        params=params,
        timeout=timeout,
        raise_for_status=False,
    ) as resp:
        if resp.status == 404:
            return None

        resp.raise_for_status()
        return await resp.json()


def _parse_query(query: str) -> tuple[str, str | None, str | None]:
    parts = query.split("|", maxsplit=1)
    card_name = parts[0].strip()
    if len(parts) == 1:
        return card_name, None, None

    set_part = parts[1].strip().lower()
    if "-" in set_part:
        set_code, collector_number = set_part.rsplit("-", 1)
        return card_name, set_code, collector_number

    return card_name, set_part, None


async def get_scryfall_data(
    search_string: str,
    set_code: str | None = None,
    collector_number: str | None = None,
):
    await api_limiter.acquire()

    try:
        async with aiohttp.ClientSession() as session:
            return await fetch_scryfall(
                session, search_string, set_code, collector_number
            )

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


async def search_card(query: str) -> Card | None:
    card_name, set_code, collector_number = _parse_query(query)
    data = await get_scryfall_data(card_name, set_code, collector_number)
    if data is None:
        return None
    return Card.from_scryfall(data)
