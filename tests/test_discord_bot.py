"""Tests for the Discord bot functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.discord_bot.embeds import MIN_RATING_THRESHOLD, create_book_embed
from src.discord_bot.mtg import CardsCog, send_card_reply
from src.tools.scryfall.cards import Card, search_card


class TestCreateBookEmbed:
    """Test cases for the create_book_embed function."""

    def test_create_book_embed_with_sufficient_ratings(self):
        """Test that rating is shown when there are enough ratings."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": 10,  # Above MIN_RATING_THRESHOLD
            "pages": 200,
            "release_year": 2023,
        }

        embed = create_book_embed(book_data)

        # Check that the embed has the expected fields
        field_names = [field.name for field in embed.fields]
        field_values = [field.value for field in embed.fields]

        assert "Rating" in field_names
        rating_index = field_names.index("Rating")
        assert "⭐ 4.5" in field_values[rating_index]

    def test_create_book_embed_with_insufficient_ratings(self):
        """Test that rating is omitted when there are not enough ratings."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": 3,  # Below MIN_RATING_THRESHOLD
            "pages": 200,
            "release_year": 2023,
        }

        embed = create_book_embed(book_data)

        # Check that rating is not displayed
        field_names = [field.name for field in embed.fields]
        assert "Rating" not in field_names

        # But other fields should still be there
        assert "Pages" in field_names
        assert "Year" in field_names

    def test_create_book_embed_with_cover_image_dict(self):
        """Test that cover image is set when provided as dict with url."""
        book_data = {
            "title": "Test Book with Cover",
            "author": "Test Author",
            "image": {"url": "https://example.com/cover.jpg"},
        }

        embed = create_book_embed(book_data)

        # Check that the embed has the image set
        assert embed.image.url == "https://example.com/cover.jpg"

    def test_create_book_embed_with_cover_image_string(self):
        """Test that cover image is set when provided as string."""
        book_data = {
            "title": "Test Book with Cover",
            "author": "Test Author",
            "image": "https://example.com/cover.jpg",
        }

        embed = create_book_embed(book_data)

        # Check that the embed has the image set
        assert embed.image.url == "https://example.com/cover.jpg"

    def test_create_book_embed_no_cover_image(self):
        """Test that no image is set when none provided."""
        book_data = {
            "title": "Test Book No Cover",
            "author": "Test Author",
        }

        embed = create_book_embed(book_data)

        # Check that no image is set
        assert embed.image.url is None

    def test_create_book_embed_invalid_image_data(self):
        """Test that invalid image data doesn't break embed creation."""
        book_data = {
            "title": "Test Book Invalid Image",
            "author": "Test Author",
            "image": {"invalid": "data"},  # Missing 'url' key
        }

        embed = create_book_embed(book_data)

        # Check that no image is set but embed is still created
        assert embed.image.url is None
        assert embed.title == "Test Book Invalid Image"

    def test_create_book_embed_with_exactly_threshold_ratings(self):
        """Test rating is shown when ratings_count equals MIN_RATING_THRESHOLD."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.2,
            "ratings_count": MIN_RATING_THRESHOLD,  # Exactly at threshold
            "pages": 150,
        }

        embed = create_book_embed(book_data)

        field_names = [field.name for field in embed.fields]
        field_values = [field.value for field in embed.fields]

        assert "Rating" in field_names
        rating_index = field_names.index("Rating")
        assert "⭐ 4.2" in field_values[rating_index]

    def test_create_book_embed_with_no_rating(self):
        """Test that no rating is shown when rating is None."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": None,
            "ratings_count": 10,
            "pages": 200,
        }

        embed = create_book_embed(book_data)

        field_names = [field.name for field in embed.fields]
        assert "Rating" not in field_names

    def test_create_book_embed_with_no_ratings_count(self):
        """Test that no rating is shown when ratings_count is None."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": None,
            "pages": 200,
        }

        embed = create_book_embed(book_data)

        field_names = [field.name for field in embed.fields]
        assert "Rating" not in field_names

    def test_create_book_embed_shows_readers_count_regardless(self):
        """Test that readers count is shown even when rating is omitted."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": 3,  # Below threshold
            "pages": 200,
        }

        embed = create_book_embed(book_data)

        field_names = [field.name for field in embed.fields]
        field_values = [field.value for field in embed.fields]

        # Rating should not be shown
        assert "Rating" not in field_names

        # But readers count should be shown
        assert "Readers" in field_names
        readers_index = field_names.index("Readers")
        assert "3" in field_values[readers_index]

    def test_create_book_embed_with_zero_ratings_count(self):
        """Test that rating is not shown when ratings_count is 0."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": 0,  # Zero ratings
            "pages": 200,
        }

        embed = create_book_embed(book_data)

        field_names = [field.name for field in embed.fields]
        assert "Rating" not in field_names
        # Readers field also shouldn't be shown when count is 0
        assert "Readers" not in field_names

    def test_create_book_embed_basic_fields_always_present(self):
        """Test that basic book information is always present."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "rating": 4.5,
            "ratings_count": 2,  # Below threshold
        }

        embed = create_book_embed(book_data)

        # Basic embed properties should always be set
        assert embed.title == "Test Book"
        assert "Test Author" in embed.description
        assert embed.color.value == 0xFFA227
        assert embed.footer.text == "Dungeon Books • Powered by Hardcover API"


class TestSearchCard:
    """Test cases for the search_card function."""

    @pytest.mark.asyncio
    async def test_search_card_successful(self):
        """Test successful card search returns Card object."""
        mock_scryfall_data = {
            "name": "Black Lotus",
            "mana_cost": "{0}",
            "type_line": "Artifact",
            "oracle_text": "Tap, Sacrifice Black Lotus: Add three mana of any one color.",
            "scryfall_uri": "https://scryfall.com/card/1e/232/black-lotus",
            "prices": {"usd": "1000.00"},
            "image_uris": {"normal": "https://example.com/lotus.jpg"},
        }

        with patch(
            "src.tools.scryfall.cards.get_scryfall_data",
            new_callable=AsyncMock,
            return_value=mock_scryfall_data,
        ):
            card = await search_card("black lotus")

            assert isinstance(card, Card)
            assert card.name == "Black Lotus"
            assert card.mana_cost == "{0}"

    @pytest.mark.asyncio
    async def test_search_card_not_found(self):
        """Test search returns None when card is not found."""
        with patch(
            "src.tools.scryfall.cards.get_scryfall_data",
            new_callable=AsyncMock,
            return_value=None,
        ):
            card = await search_card("nonexistent card xyz 123")

            assert card is None

    @pytest.mark.asyncio
    async def test_search_card_with_special_characters(self):
        """Test searching for card with special characters in name."""
        mock_data = {
            "name": "B.F.M. (Big Furry Monster)",
            "mana_cost": "{2}{R}{R}{R}",
            "type_line": "Creature — Goblin",
            "oracle_text": "Test",
            "scryfall_uri": "https://scryfall.com/card/test",
            "prices": {"usd": "5.00"},
            "image_uris": {"normal": "https://example.com/img.jpg"},
        }

        with patch(
            "src.tools.scryfall.cards.get_scryfall_data",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            card = await search_card("B.F.M. (Big Furry Monster)")

            assert card is not None
            assert "B.F.M." in card.name


class TestSendCardReply:
    """Test cases for the send_card_reply function."""

    @pytest.mark.asyncio
    async def test_send_card_reply_creates_embed(self):
        """Test that send_card_reply creates an embed with card info."""
        card = Card(
            name="Lightning Bolt",
            price="15.00",
            url="https://scryfall.com/card/a25/141/lightning-bolt",
            mana_cost="{R}",
            image="https://example.com/bolt.jpg",
            type_line="Instant",
            oracle_text="Lightning Bolt deals 3 damage to any target.",
        )

        mock_message = AsyncMock()
        mock_reply = AsyncMock()
        mock_message.reply = mock_reply

        mock_bot = MagicMock()
        mock_bot.user = MagicMock()
        mock_bot.user.display_name = "Test Bot"
        mock_bot.user.avatar = MagicMock(url="https://example.com/avatar.jpg")

        await send_card_reply(mock_message, card, mock_bot)

        # Verify that reply was called
        mock_reply.assert_called_once()

        # Get the embed that was passed to reply
        call_args = mock_reply.call_args
        embed = call_args[1]["embed"]

        # Verify embed content
        assert "Lightning Bolt" in embed.title
        assert "{R}" in embed.title
        assert embed.url == "https://scryfall.com/card/a25/141/lightning-bolt"
        assert "Instant" in embed.description
        assert "Lightning Bolt deals 3 damage" in embed.description

    @pytest.mark.asyncio
    async def test_send_card_reply_without_bot_avatar(self):
        """Test send_card_reply when bot has no avatar."""
        card = Card(
            name="Test Card",
            price="1.00",
            url="https://scryfall.com/card/test",
            mana_cost="{1}",
            image="https://example.com/test.jpg",
            type_line="Creature",
            oracle_text="Test oracle text",
        )

        mock_message = AsyncMock()
        mock_reply = AsyncMock()
        mock_message.reply = mock_reply

        mock_bot = MagicMock()
        mock_bot.user = None

        await send_card_reply(mock_message, card, mock_bot)

        mock_reply.assert_called_once()
        call_args = mock_reply.call_args
        embed = call_args[1]["embed"]

        # Embed should still be created without author
        assert "Test Card" in embed.title

    @pytest.mark.asyncio
    async def test_send_card_reply_with_empty_mana_cost(self):
        """Test send_card_reply with card that has no mana cost."""
        card = Card(
            name="Swamp",
            price="0.50",
            url="https://scryfall.com/card/test",
            mana_cost="",
            image="https://example.com/swamp.jpg",
            type_line="Basic Land — Swamp",
            oracle_text="{T}: Add {B}.",
        )

        mock_message = AsyncMock()
        mock_reply = AsyncMock()
        mock_message.reply = mock_reply

        mock_bot = MagicMock()

        await send_card_reply(mock_message, card, mock_bot)

        mock_reply.assert_called_once()
        call_args = mock_reply.call_args
        embed = call_args[1]["embed"]

        assert "Swamp" in embed.title


class TestCardsCog:
    """Test cases for the CardsCog Discord bot cog."""

    @pytest.mark.asyncio
    async def test_cards_cog_initialization(self):
        """Test CardsCog initializes with bot."""
        mock_bot = MagicMock()
        cog = CardsCog(mock_bot)

        assert cog.bot == mock_bot

    @pytest.mark.asyncio
    async def test_cards_cog_on_message_ignores_bot_messages(self):
        """Test that CardsCog ignores messages from bots."""
        mock_bot = MagicMock()
        cog = CardsCog(mock_bot)

        mock_message = MagicMock()
        mock_message.author.bot = True
        mock_message.content = "[[Lightning Bolt]]"

        # Should return early without processing
        await cog.on_message(mock_message)

        # No reply should be sent
        mock_message.reply.assert_not_called()

    @pytest.mark.asyncio
    async def test_cards_cog_on_message_ignores_no_brackets(self):
        """Test that CardsCog ignores messages without card brackets."""
        mock_bot = MagicMock()
        cog = CardsCog(mock_bot)

        mock_message = MagicMock()
        mock_message.author.bot = False
        mock_message.content = "This is just a regular message"

        await cog.on_message(mock_message)

        mock_message.reply.assert_not_called()

    @pytest.mark.asyncio
    async def test_cards_cog_on_message_finds_single_card(self):
        """Test CardsCog finds and replies with single card."""
        mock_bot = MagicMock()
        mock_bot.user = MagicMock()
        mock_bot.user.display_name = "Test Bot"
        mock_bot.user.avatar = MagicMock(url="https://example.com/avatar.jpg")

        cog = CardsCog(mock_bot)

        mock_message = AsyncMock()
        mock_message.author.bot = False
        mock_message.content = "Check out [[Lightning Bolt]]!"

        mock_card = Card(
            name="Lightning Bolt",
            price="15.00",
            url="https://scryfall.com/card/a25/141/lightning-bolt",
            mana_cost="{R}",
            image="https://example.com/bolt.jpg",
            type_line="Instant",
            oracle_text="Lightning Bolt deals 3 damage to any target.",
        )

        with patch(
            "src.discord_bot.mtg.search_card",
            new_callable=AsyncMock,
            return_value=mock_card,
        ):
            await cog.on_message(mock_message)

            mock_message.reply.assert_called_once()

    @pytest.mark.asyncio
    async def test_cards_cog_on_message_multiple_cards(self):
        """Test CardsCog finds and replies with multiple cards."""
        mock_bot = MagicMock()
        mock_bot.user = MagicMock()
        mock_bot.user.avatar = MagicMock(url="https://example.com/avatar.jpg")

        cog = CardsCog(mock_bot)

        mock_message = AsyncMock()
        mock_message.author.bot = False
        mock_message.content = "Compare [[Lightning Bolt]] vs [[Fireball]]"

        mock_card1 = Card(
            name="Lightning Bolt",
            price="15.00",
            url="https://scryfall.com/card/a25/141/lightning-bolt",
            mana_cost="{R}",
            image="https://example.com/bolt.jpg",
            type_line="Instant",
            oracle_text="Lightning Bolt deals 3 damage to any target.",
        )

        mock_card2 = Card(
            name="Fireball",
            price="5.00",
            url="https://scryfall.com/card/test/123/fireball",
            mana_cost="{X}{R}{R}",
            image="https://example.com/fireball.jpg",
            type_line="Instant",
            oracle_text="Fireball deals X damage divided as you choose among any number of targets.",
        )

        async def mock_search_card(name):
            if "Lightning" in name:
                return mock_card1
            elif "Fireball" in name:
                return mock_card2
            return None

        with patch(
            "src.discord_bot.mtg.search_card",
            side_effect=mock_search_card,
        ):
            await cog.on_message(mock_message)

            # Should have replied twice, once for each card
            assert mock_message.reply.call_count == 2

    @pytest.mark.asyncio
    async def test_cards_cog_on_message_card_not_found(self):
        """Test CardsCog handles card not found gracefully."""
        mock_bot = MagicMock()
        cog = CardsCog(mock_bot)

        mock_message = AsyncMock()
        mock_message.author.bot = False
        mock_message.content = "Look for [[Nonexistent Card XYZ]]"

        with patch(
            "src.discord_bot.mtg.search_card",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await cog.on_message(mock_message)

            mock_message.reply.assert_called_once()
            call_args = mock_message.reply.call_args
            assert "not found" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_cards_cog_extracts_multiple_card_names(self):
        """Test regex correctly extracts multiple card names."""
        import re

        message_content = (
            "I have [[Mox Sapphire]], [[Black Lotus]], and [[Time Walk]]"
        )
        cards = re.findall(r"\[\[([^\]]+)\]\]", message_content)

        assert len(cards) == 3
        assert cards[0] == "Mox Sapphire"
        assert cards[1] == "Black Lotus"
        assert cards[2] == "Time Walk"

    @pytest.mark.asyncio
    async def test_cards_cog_extracts_cards_with_spaces(self):
        """Test regex handles card names with spaces."""
        import re

        message_content = "Play [[Supreme Verdict]] next turn!"
        cards = re.findall(r"\[\[([^\]]+)\]\]", message_content)

        assert len(cards) == 1
        assert cards[0] == "Supreme Verdict"

    @pytest.mark.asyncio
    async def test_cards_cog_extracts_cards_with_special_chars(self):
        """Test regex handles card names with special characters."""
        import re

        message_content = (
            "Check [[B.F.M. (Big Furry Monster)]] and [[Æther Vial]]"
        )
        cards = re.findall(r"\[\[([^\]]+)\]\]", message_content)

        assert len(cards) == 2
        assert cards[0] == "B.F.M. (Big Furry Monster)"
        assert cards[1] == "Æther Vial"

    @pytest.mark.asyncio
    async def test_cards_cog_on_message_mixed_found_and_not_found(self):
        """Test CardsCog handles mix of found and not found cards."""
        mock_bot = MagicMock()
        mock_bot.user = MagicMock()
        mock_bot.user.avatar = MagicMock(url="https://example.com/avatar.jpg")

        cog = CardsCog(mock_bot)

        mock_message = AsyncMock()
        mock_message.author.bot = False
        mock_message.content = "Try [[Lightning Bolt]] and [[Fake Card XYZ]]"

        mock_card = Card(
            name="Lightning Bolt",
            price="15.00",
            url="https://scryfall.com/card/a25/141/lightning-bolt",
            mana_cost="{R}",
            image="https://example.com/bolt.jpg",
            type_line="Instant",
            oracle_text="Lightning Bolt deals 3 damage to any target.",
        )

        async def mock_search_card(name):
            if "Lightning" in name:
                return mock_card
            return None

        with patch(
            "src.discord_bot.mtg.search_card",
            side_effect=mock_search_card,
        ):
            await cog.on_message(mock_message)

            # Should have replied twice: once with card, once with not found
            assert mock_message.reply.call_count == 2
