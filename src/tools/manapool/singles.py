import logging

import aiohttp

logger = logging.getLogger(__name__)

API_BASE = "https://manapool.com/api/v1"


async def fetch_product_url(scryfall_id: str) -> str | None:
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
                    return items[0].get("url")
                return None
    except Exception as e:
        logger.warning(f"Manapool lookup failed for {scryfall_id}: {e}")
        return None
