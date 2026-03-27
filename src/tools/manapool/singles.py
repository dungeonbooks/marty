import logging
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)

API_BASE = "https://manapool.com/api/v1"


def _search_url(card_name: str) -> str:
    return f"https://manapool.com/cards?{urlencode({'q': card_name})}"


class ManapoolResult:
    def __init__(self, url: str, price: str | None = None):
        self.url = url
        self.price = price


async def fetch_product(scryfall_id: str, card_name: str) -> ManapoolResult:
    timeout = aiohttp.ClientTimeout(total=3)
    url = f"{API_BASE}/products/singles"
    params = {"scryfall_ids": scryfall_id}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, params=params, timeout=timeout) as resp:
                resp.raise_for_status()
                data = await resp.json()
                items = data.get("data", [])
                if items:
                    item = items[0]
                    product_url = item.get("url")
                    price_cents = item.get("price_cents")
                    price = f"{price_cents / 100:.2f}" if price_cents else None
                    if product_url:
                        return ManapoolResult(url=product_url, price=price)
    except Exception as e:
        logger.warning(f"Manapool lookup failed for {scryfall_id}: {e}")

    return ManapoolResult(url=_search_url(card_name))
