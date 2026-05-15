"""Scryfall tool: look up MTG cards for the AI tool registry."""

from typing import Any

from ..base import BaseTool, ToolResult
from .cards import search_card


class ScryfallTool(BaseTool):
    @property
    def name(self) -> str:
        return "scryfall_api"

    @property
    def description(self) -> str:
        return (
            "Look up a Magic: The Gathering card by name using Scryfall. "
            "Returns card details including mana cost, type, oracle text, "
            "price, and image. Use this when someone asks about an MTG card."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": (
                    "Card name to search for. Supports fuzzy matching. "
                    "Can include set code with pipe: 'Card Name|set' "
                    "or 'Card Name|set-collector'."
                ),
            }
        }

    async def execute(self, **kwargs) -> ToolResult:
        query = (kwargs.get("query") or "").strip()
        if not query:
            return ToolResult(success=False, data=None, error="query is required")

        return await self._handle_errors(self._lookup, query)

    async def _lookup(self, query: str) -> dict[str, Any]:
        card = await search_card(query)
        if card is None:
            raise ValueError(f"Card not found: {query}")

        return {
            "name": card.name,
            "mana_cost": card.mana_cost,
            "type_line": card.type_line,
            "oracle_text": card.oracle_text,
            "power": card.power,
            "toughness": card.toughness,
            "price": card.price,
            "rarity": card.rarity,
            "set_name": card.set_name,
            "url": card.url,
            "image": card.image,
            "scryfall_id": card.scryfall_id,
        }
