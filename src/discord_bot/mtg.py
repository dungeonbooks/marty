import re

from discord import Embed, Message
from discord.ext import commands
from discord.ext.commands import Bot

from src.tools.manapool import fetch_product_url
from src.tools.scryfall.cards import Card, search_card

MANA_EMOJI_NAMES = {
    "W": "manaw",
    "U": "manau",
    "B": "manab",
    "R": "manar",
    "G": "manag",
    "C": "manac",
    "T": "manat",
    "X": "manax",
    "0": "mana0",
    "1": "mana1",
    "2": "mana2",
    "3": "mana3",
    "4": "mana4",
    "5": "mana5",
    "6": "mana6",
}


def _replace_mana_symbols(text: str, bot: Bot) -> str:
    def replace_match(match):
        symbol = match.group(1)
        emoji_name = MANA_EMOJI_NAMES.get(symbol)
        if emoji_name:
            emoji = next((e for e in bot.emojis if e.name == emoji_name), None)
            if emoji:
                return str(emoji)
        return match.group(0)

    return re.sub(r"\{([^}]+)\}", replace_match, text)


RARITY_COLORS = {
    "common": 0x1A1A1A,
    "uncommon": 0xC0C0C0,
    "rare": 0xDAA520,
    "mythic": 0xE85D04,
    "special": 0x9B59B6,
    "bonus": 0x9B59B6,
}


def _build_card_embed(card: Card, bot: Bot, manapool_url: str | None = None) -> Embed:
    mana_cost = _replace_mana_symbols(card.mana_cost, bot) if card.mana_cost else ""
    title = f"{card.name} {mana_cost}" if mana_cost else card.name
    description = card.type_line or ""
    if card.power is not None and card.toughness is not None:
        description += f" ({card.power}/{card.toughness})"
    if card.oracle_text:
        oracle = _replace_mana_symbols(card.oracle_text, bot)
        description += f"\n\n{oracle}"

    embed = Embed(title=title, url=card.url, description=description)
    embed.colour = RARITY_COLORS.get(card.rarity, 0x2B2D31)

    if card.image:
        embed.set_image(url=card.image)

    if card.price:
        embed.add_field(name="Price", value=f"${card.price}", inline=True)

    if manapool_url:
        embed.add_field(name="Buy", value=f"[Manapool]({manapool_url})", inline=True)

    if card.set_name and card.rarity:
        embed.set_footer(text=f"{card.set_name} · {card.rarity.capitalize()}")

    return embed


async def send_card_reply(message: Message, card: Card, bot: Bot):
    manapool_url = (
        await fetch_product_url(card.scryfall_id) if card.scryfall_id else None
    )
    embed = _build_card_embed(card, bot, manapool_url)
    await message.reply(embed=embed)


class CardsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if "[[" not in message.content:
            return

        cards = re.findall(r"\[\[([^\]]+)\]\]", message.content)

        for card_name in cards:
            card = await search_card(card_name)
            if card:
                await send_card_reply(message, card, self.bot)
            else:
                await message.reply(f"Card not found: {card_name}")
