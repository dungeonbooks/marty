import re

from discord import Embed, Message
from discord.ext import commands
from discord.ext.commands import Bot

from src.tools.scryfall.cards import Card, search_card


def send_card_reply(message: Message, card: Card, bot: Bot):
    embed = Embed(
        title=f"{card.name} {card.mana_cost}",
        url=card.url,
        description=f"{card.type_line}\n\n{card.oracle_text}",
    )
    if getattr(card, "image", None):
        embed.set_thumbnail(url=card.image)
    if (bot.user) and (bot.user.avatar):
        embed.set_author(name=bot.user.display_name, icon_url=bot.user.avatar.url)
    return message.reply(embed=embed)


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
