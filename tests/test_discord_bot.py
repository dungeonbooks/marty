"""Tests for the Discord bot functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.discord_bot.embeds import MIN_RATING_THRESHOLD, create_book_embed
from src.discord_bot.mtg import CardsCog, build_card_embed, send_card_reply
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
            power=None,
            toughness=None,
            rarity="uncommon",
            set_name="Masters 25",
            scryfall_id="abc-123",
        )

        mock_message = AsyncMock()
        mock_reply = AsyncMock()
        mock_message.reply = mock_reply

        mock_bot = MagicMock()
        mock_bot.user = MagicMock()
        mock_bot.user.display_name = "Test Bot"
        mock_bot.user.avatar = MagicMock(url="https://example.com/avatar.jpg")
        mock_bot.emojis = []

        with patch(
            "src.discord_bot.mtg.fetch_product",
            new_callable=AsyncMock,
            return_value=None,
        ):
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
            power=None,
            toughness=None,
            rarity="common",
            set_name="Test Set",
            scryfall_id="test-123",
        )

        mock_message = AsyncMock()
        mock_reply = AsyncMock()
        mock_message.reply = mock_reply

        mock_bot = MagicMock()
        mock_bot.user = None
        mock_bot.emojis = []

        with patch(
            "src.discord_bot.mtg.fetch_product",
            new_callable=AsyncMock,
            return_value=None,
        ):
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
            power=None,
            toughness=None,
            rarity="common",
            set_name="Core Set 2021",
            scryfall_id="swamp-123",
        )

        mock_message = AsyncMock()
        mock_reply = AsyncMock()
        mock_message.reply = mock_reply

        mock_bot = MagicMock()
        mock_bot.emojis = []

        with patch(
            "src.discord_bot.mtg.fetch_product",
            new_callable=AsyncMock,
            return_value=None,
        ):
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
        mock_bot.emojis = []

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
            power=None,
            toughness=None,
            rarity="uncommon",
            set_name="Masters 25",
            scryfall_id="abc-123",
        )

        with patch(
            "src.discord_bot.mtg.search_card",
            new_callable=AsyncMock,
            return_value=mock_card,
        ), patch(
            "src.discord_bot.mtg.fetch_product",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await cog.on_message(mock_message)

            mock_message.reply.assert_called_once()

    @pytest.mark.asyncio
    async def test_cards_cog_on_message_multiple_cards(self):
        """Test CardsCog finds and replies with multiple cards."""
        mock_bot = MagicMock()
        mock_bot.user = MagicMock()
        mock_bot.user.avatar = MagicMock(url="https://example.com/avatar.jpg")
        mock_bot.emojis = []

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
            power=None,
            toughness=None,
            rarity="uncommon",
            set_name="Masters 25",
            scryfall_id="abc-123",
        )

        mock_card2 = Card(
            name="Fireball",
            price="5.00",
            url="https://scryfall.com/card/test/123/fireball",
            mana_cost="{X}{R}{R}",
            image="https://example.com/fireball.jpg",
            type_line="Instant",
            oracle_text="Fireball deals X damage divided as you choose among any number of targets.",
            power=None,
            toughness=None,
            rarity="uncommon",
            set_name="Fifth Edition",
            scryfall_id="fireball-123",
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
        ), patch(
            "src.discord_bot.mtg.fetch_product",
            new_callable=AsyncMock,
            return_value=None,
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

        message_content = "I have [[Mox Sapphire]], [[Black Lotus]], and [[Time Walk]]"
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

        message_content = "Check [[B.F.M. (Big Furry Monster)]] and [[Æther Vial]]"
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
        mock_bot.emojis = []

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
            power=None,
            toughness=None,
            rarity="uncommon",
            set_name="Masters 25",
            scryfall_id="abc-123",
        )

        async def mock_search_card(name):
            if "Lightning" in name:
                return mock_card
            return None

        with patch(
            "src.discord_bot.mtg.search_card",
            side_effect=mock_search_card,
        ), patch(
            "src.discord_bot.mtg.fetch_product",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await cog.on_message(mock_message)

            # Should have replied twice: once with card, once with not found
            assert mock_message.reply.call_count == 2


class TestScryfallTool:
    """Test cases for the ScryfallTool."""

    @pytest.mark.asyncio
    async def test_scryfall_tool_name(self):
        """Test ScryfallTool has correct name."""
        from src.tools.scryfall.tool import ScryfallTool

        tool = ScryfallTool()
        assert tool.name == "scryfall_api"

    @pytest.mark.asyncio
    async def test_scryfall_tool_description(self):
        """Test ScryfallTool has a description."""
        from src.tools.scryfall.tool import ScryfallTool

        tool = ScryfallTool()
        assert tool.description
        assert "MTG" in tool.description or "card" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_scryfall_tool_parameters(self):
        """Test ScryfallTool parameters schema."""
        from src.tools.scryfall.tool import ScryfallTool

        tool = ScryfallTool()
        assert "query" in tool.parameters
        assert tool.parameters["query"]["type"] == "string"

    @pytest.mark.asyncio
    async def test_scryfall_tool_execute_success(self):
        """Test ScryfallTool execute returns card data on success."""
        from src.tools.scryfall.tool import ScryfallTool

        mock_card = Card(
            name="Lightning Bolt",
            price="15.00",
            url="https://scryfall.com/card/a25/141/lightning-bolt",
            mana_cost="{R}",
            image="https://example.com/bolt.jpg",
            type_line="Instant",
            oracle_text="Lightning Bolt deals 3 damage to any target.",
            power=None,
            toughness=None,
            rarity="uncommon",
            set_name="Masters 25",
            scryfall_id="abc-123",
        )

        tool = ScryfallTool()

        with patch(
            "src.tools.scryfall.tool.search_card",
            new_callable=AsyncMock,
            return_value=mock_card,
        ):
            result = await tool.execute(query="Lightning Bolt")

            assert result.success
            assert result.data["name"] == "Lightning Bolt"
            assert result.data["mana_cost"] == "{R}"
            assert result.data["type_line"] == "Instant"
            assert result.data["price"] == "15.00"

    @pytest.mark.asyncio
    async def test_scryfall_tool_execute_not_found(self):
        """Test ScryfallTool execute returns error when card not found."""
        from src.tools.scryfall.tool import ScryfallTool

        tool = ScryfallTool()

        with patch(
            "src.tools.scryfall.tool.search_card",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await tool.execute(query="Nonexistent Card XYZ")

            assert not result.success
            assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_scryfall_tool_execute_empty_query(self):
        """Test ScryfallTool execute returns error for empty query."""
        from src.tools.scryfall.tool import ScryfallTool

        tool = ScryfallTool()
        result = await tool.execute(query="")

        assert not result.success
        assert "required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_scryfall_tool_execute_whitespace_query(self):
        """Test ScryfallTool execute returns error for whitespace query."""
        from src.tools.scryfall.tool import ScryfallTool

        tool = ScryfallTool()
        result = await tool.execute(query="   ")

        assert not result.success
        assert "required" in result.error.lower()


class TestSearchCardShared:
    """Test cases for the search_card_shared helper."""

    @pytest.mark.asyncio
    async def test_search_card_shared_success(self):
        """Test search_card_shared returns card on success."""
        from src.discord_bot.bot import search_card_shared

        mock_card = Card(
            name="Lightning Bolt",
            price="15.00",
            url="https://scryfall.com/card/a25/141/lightning-bolt",
            mana_cost="{R}",
            image="https://example.com/bolt.jpg",
            type_line="Instant",
            oracle_text="Lightning Bolt deals 3 damage to any target.",
            power=None,
            toughness=None,
            rarity="uncommon",
            set_name="Masters 25",
            scryfall_id="abc-123",
        )

        with patch(
            "src.discord_bot.bot.search_card",
            new_callable=AsyncMock,
            return_value=mock_card,
        ):
            card_result, error_msg = await search_card_shared("Lightning Bolt")

            assert card_result is not None
            assert error_msg is None
            assert card_result.name == "Lightning Bolt"

    @pytest.mark.asyncio
    async def test_search_card_shared_not_found(self):
        """Test search_card_shared returns error when card not found."""
        from src.discord_bot.bot import search_card_shared

        with patch(
            "src.discord_bot.bot.search_card",
            new_callable=AsyncMock,
            return_value=None,
        ):
            card_result, error_msg = await search_card_shared("Nonexistent Card")

            assert card_result is None
            assert error_msg is not None
            assert "couldn't find" in error_msg

    @pytest.mark.asyncio
    async def test_search_card_shared_empty_query(self):
        """Test search_card_shared returns error for empty query."""
        from src.discord_bot.bot import search_card_shared

        card_result, error_msg = await search_card_shared("  ")

        assert card_result is None
        assert "need a card name" in error_msg


class TestScryfallToolRegistry:
    """Test that ScryfallTool is registered in the tool registry."""

    def test_scryfall_tool_registered(self):
        """Test ScryfallTool is in the tool registry."""
        from src.tools import tool_registry

        assert "scryfall_api" in tool_registry.list_tools()

    def test_scryfall_tool_instantiation(self):
        """Test ScryfallTool can be instantiated from registry."""
        from src.tools import tool_registry

        tool = tool_registry.get_tool("scryfall_api")
        assert tool is not None
        assert tool.name == "scryfall_api"


class TestSendCardEmbed:
    """Test cases for MartyBot._send_card_embed method."""

    @pytest.mark.asyncio
    async def test_send_card_embed_posts_embed(self):
        """Test that _send_card_embed sends a card embed to the thread."""
        from src.discord_bot.bot import MartyBot
        from src.tools.base import ToolResult

        bot = MagicMock(spec=MartyBot)
        bot._renamed_threads = set()

        card_data = {
            "name": "Lightning Bolt",
            "mana_cost": "{R}",
            "type_line": "Instant",
            "oracle_text": "Lightning Bolt deals 3 damage to any target.",
            "power": None,
            "toughness": None,
            "price": "15.00",
            "rarity": "uncommon",
            "set_name": "Masters 25",
            "url": "https://scryfall.com/card/a25/141/lightning-bolt",
            "image": "https://example.com/bolt.jpg",
            "scryfall_id": "abc-123",
        }

        result = ToolResult(success=True, data=card_data, error=None)
        tool_result = {"tool_name": "scryfall_api", "result": result, "tool_input": {"query": "Lightning Bolt"}}

        mock_thread = AsyncMock()

        with patch(
            "src.discord_bot.bot.build_card_embed",
            new_callable=AsyncMock,
        ) as mock_build:
            mock_embed = MagicMock()
            mock_build.return_value = mock_embed

            await MartyBot._send_card_embed(bot, tool_result, mock_thread, "testuser")

            mock_build.assert_called_once()
            call_args = mock_build.call_args
            card_arg = call_args[0][0]
            assert isinstance(card_arg, Card)
            assert card_arg.name == "Lightning Bolt"
            mock_thread.send.assert_called_once_with(embed=mock_embed)

    @pytest.mark.asyncio
    async def test_send_card_embed_skips_on_failure(self):
        """Test that _send_card_embed does nothing when result is not successful."""
        from src.discord_bot.bot import MartyBot
        from src.tools.base import ToolResult

        bot = MagicMock(spec=MartyBot)

        result = ToolResult(success=False, data=None, error="not found")
        tool_result = {"tool_name": "scryfall_api", "result": result, "tool_input": {"query": "bogus"}}

        mock_thread = AsyncMock()

        await MartyBot._send_card_embed(bot, tool_result, mock_thread, "testuser")

        mock_thread.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_card_embed_skips_on_non_dict_data(self):
        """Test that _send_card_embed does nothing when data is not a dict."""
        from src.discord_bot.bot import MartyBot
        from src.tools.base import ToolResult

        bot = MagicMock(spec=MartyBot)

        result = ToolResult(success=True, data=["not", "a", "dict"], error=None)
        tool_result = {"tool_name": "scryfall_api", "result": result, "tool_input": {"query": "test"}}

        mock_thread = AsyncMock()

        await MartyBot._send_card_embed(bot, tool_result, mock_thread, "testuser")

        mock_thread.send.assert_not_called()

