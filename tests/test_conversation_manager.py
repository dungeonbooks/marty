import json
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.conversation.manager import (
    ConversationContext,
    ConversationManagerTool,
    ConversationMessage,
)


@pytest.fixture
async def tool():
    """Create a ConversationManagerTool instance for testing."""
    redis_port = os.getenv("TEST_REDIS_PORT", "56379")
    redis_url = os.getenv("TEST_REDIS_URL", f"redis://localhost:{redis_port}/1")
    tool = ConversationManagerTool(redis_url)
    yield tool
    await tool.close()


@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.delete.return_value = True
    return redis_mock


@pytest.fixture
def sample_phone():
    """Sample phone number for testing."""
    return "+1234567890"


@pytest.fixture
def sample_conversation_context():
    """Sample conversation context for testing."""
    return ConversationContext(
        customer_id="customer_123",
        phone="+1234567890",
        messages=[
            ConversationMessage(
                id="msg_1",
                content="I'm looking for a good fantasy book",
                direction="inbound",
                timestamp=datetime.now(UTC),
            ),
            ConversationMessage(
                id="msg_2",
                content="I recommend 'The Name of the Wind' by Patrick Rothfuss",
                direction="outbound",
                timestamp=datetime.now(UTC),
            ),
        ],
        conversation_id="conv_123",
        last_activity=datetime.now(UTC),
    )


@pytest.mark.integration
class TestConversationManagerTool:
    """Test suite for ConversationManagerTool class."""

    @pytest.mark.asyncio
    async def test_initialization(self, tool):
        """Test ConversationManagerTool initialization."""
        assert tool.redis_client is None  # Not initialized until first use
        assert tool.message_limit == 10
        assert tool.conversation_ttl == 3600

    def test_tool_properties(self, tool):
        """Test tool properties for BaseTool interface."""
        assert tool.name == "conversation_manager"
        assert "Manages conversation state" in tool.description

        parameters = tool.parameters
        assert "action" in parameters
        assert "phone" in parameters
        assert "content" in parameters
        assert "direction" in parameters
        assert "metadata" in parameters

    def test_validate_input(self, tool):
        """Test input validation."""
        # Valid input for load action
        assert tool.validate_input(action="load", phone="+1234567890") is True

        # Valid input for add_message action
        assert (
            tool.validate_input(
                action="add_message",
                phone="+1234567890",
                content="Hello",
                direction="inbound",
            )
            is True
        )

        # Missing parameters
        assert tool.validate_input() is False
        assert tool.validate_input(action="load") is False
        assert tool.validate_input(action="add_message", phone="+1234567890") is False

    @pytest.mark.asyncio
    async def test_execute_validation_error(self, tool):
        """Test execute with validation error."""
        result = await tool.execute(action="load")  # Missing phone

        assert result.success is False
        assert result.error is not None
        assert "Invalid parameters" in result.error

    @pytest.mark.asyncio
    async def test_conversation_serialization(self, tool, sample_conversation_context):
        """Test conversation serialization and deserialization."""
        # Serialize
        serialized = tool._serialize_conversation(sample_conversation_context)

        assert serialized["customer_id"] == "customer_123"
        assert serialized["phone"] == "+1234567890"
        assert len(serialized["messages"]) == 2

        # Deserialize
        deserialized = tool._deserialize_conversation(serialized)

        assert deserialized.customer_id == sample_conversation_context.customer_id
        assert deserialized.phone == sample_conversation_context.phone
        assert len(deserialized.messages) == len(sample_conversation_context.messages)

    @pytest.mark.asyncio
    @patch("src.database.init_database")
    @patch("src.database.AsyncSessionLocal")
    async def test_load_conversation_from_database(
        self, mock_session_local, mock_init_db, tool, sample_phone
    ):
        """Test loading conversation from database."""
        # Mock database initialization
        mock_init_db.return_value = None

        # Mock database session
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        # Mock customer
        mock_customer = MagicMock()
        mock_customer.id = "customer_123"

        # Mock conversation
        mock_conversation = MagicMock()
        mock_conversation.id = "conv_123"
        mock_conversation.last_message_at = datetime.now(UTC)
        mock_conversation.context = {"test": "data"}

        # Mock messages
        mock_message = MagicMock()
        mock_message.id = "msg_1"
        mock_message.content = "Hello"
        mock_message.direction = "inbound"
        mock_message.timestamp = datetime.now(UTC)

        # Mock database functions
        with (
            patch(
                "src.tools.conversation.manager.get_customer_by_phone",
                return_value=mock_customer,
            ),
            patch(
                "src.tools.conversation.manager.get_active_conversation",
                return_value=mock_conversation,
            ),
            patch(
                "src.tools.conversation.manager.get_conversation_messages",
                return_value=[mock_message],
            ),
        ):
            context = await tool._load_from_database(sample_phone)

            assert context is not None
            assert context.customer_id == "customer_123"
            assert context.phone == sample_phone
            assert len(context.messages) == 1
            assert context.messages[0].content == "Hello"

    @pytest.mark.asyncio
    @patch("src.database.init_database")
    @patch("src.database.AsyncSessionLocal")
    async def test_create_new_conversation(
        self, mock_session_local, mock_init_db, tool, sample_phone
    ):
        """Test creating a new conversation."""
        # Mock database initialization
        mock_init_db.return_value = None

        # Mock database session
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        # Mock customer creation
        mock_customer = MagicMock()
        mock_customer.id = "customer_123"

        # Mock conversation creation
        mock_conversation = MagicMock()
        mock_conversation.id = "conv_123"

        with (
            patch(
                "src.tools.conversation.manager.get_customer_by_phone",
                return_value=None,
            ),
            patch(
                "src.tools.conversation.manager.create_customer",
                return_value=mock_customer,
            ),
            patch(
                "src.tools.conversation.manager.create_conversation",
                return_value=mock_conversation,
            ),
        ):
            context = await tool._create_new_conversation(sample_phone)

            assert context is not None
            assert context.customer_id == "customer_123"
            assert context.phone == sample_phone
            assert len(context.messages) == 0

    @pytest.mark.asyncio
    async def test_cache_conversation(self, tool, sample_conversation_context):
        """Test conversation caching in Redis."""
        with patch.object(tool, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value.__aenter__.return_value = mock_redis

            await tool._cache_conversation(sample_conversation_context)

            # Verify setex was called
            mock_redis.setex.assert_called_once()
            args = mock_redis.setex.call_args[0]

            # Check cache key format
            assert args[0] == f"conversation:{sample_conversation_context.phone}"
            # Check TTL
            assert args[1] == tool.conversation_ttl
            # Check data is JSON
            cached_data = json.loads(args[2])
            assert cached_data["customer_id"] == sample_conversation_context.customer_id

    @pytest.mark.asyncio
    async def test_load_conversation_from_cache(
        self, tool, sample_conversation_context
    ):
        """Test loading conversation from Redis cache."""
        serialized_data = tool._serialize_conversation(sample_conversation_context)

        with patch.object(tool, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = json.dumps(serialized_data)
            mock_get_redis.return_value.__aenter__.return_value = mock_redis

            result = await tool.execute(
                action="load", phone=sample_conversation_context.phone
            )

            assert result.success is True
            assert result.data is not None
            assert result.data.customer_id == sample_conversation_context.customer_id

    @pytest.mark.asyncio
    async def test_add_message_action(self, tool, sample_phone):
        """Test adding a message using execute method."""
        # Create empty conversation context (no existing messages)
        empty_context = ConversationContext(
            customer_id="customer_123",
            phone=sample_phone,
            messages=[],  # No existing messages
            conversation_id="conv_123",
            last_activity=datetime.now(UTC),
        )

        with (
            patch.object(tool, "_load_conversation", return_value=empty_context),
            patch.object(tool, "_save_message_to_database", return_value=None),
            patch.object(tool, "_cache_conversation", return_value=None),
        ):
            result = await tool.execute(
                action="add_message",
                phone=sample_phone,
                content="Hello",
                direction="inbound",
            )

            assert result.success is True
            assert result.data is not None
            assert len(result.data.messages) == 1  # Only the new message
            assert result.data.messages[0].content == "Hello"
            assert result.data.messages[0].direction == "inbound"

    @pytest.mark.asyncio
    async def test_expire_conversation_action(self, tool, sample_phone):
        """Test expiring a conversation using execute method."""
        with patch.object(tool, "_get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value.__aenter__.return_value = mock_redis

            result = await tool.execute(action="expire", phone=sample_phone)

            assert result.success is True
            assert result.data["expired"] is True
            # Verify delete was called with correct key
            mock_redis.delete.assert_called_once_with(f"conversation:{sample_phone}")

    @pytest.mark.asyncio
    async def test_get_conversation_summary_action(
        self, tool, sample_conversation_context
    ):
        """Test getting conversation summary using execute method."""
        with patch.object(
            tool, "_load_conversation", return_value=sample_conversation_context
        ):
            result = await tool.execute(
                action="summary", phone=sample_conversation_context.phone
            )

            assert result.success is True
            assert result.data["exists"] is True
            assert result.data["message_count"] == 2
            assert (
                result.data["conversation_id"]
                == sample_conversation_context.conversation_id
            )

    @pytest.mark.asyncio
    async def test_get_conversation_summary_no_conversation(self, tool, sample_phone):
        """Test getting summary when no conversation exists."""
        with patch.object(tool, "_load_conversation", return_value=None):
            result = await tool.execute(action="summary", phone=sample_phone)

            assert result.success is True
            assert result.data["exists"] is False

    @pytest.mark.asyncio
    async def test_message_limit_enforcement(self, tool, sample_phone):
        """Test that message limit is enforced."""
        # Create conversation with message limit + 1 messages
        messages = [
            ConversationMessage(
                id=f"msg_{i}",
                content=f"Message {i}",
                direction="inbound" if i % 2 == 0 else "outbound",
                timestamp=datetime.now(UTC),
            )
            for i in range(tool.message_limit + 1)
        ]

        context = ConversationContext(
            customer_id="customer_123",
            phone=sample_phone,
            messages=messages,
            conversation_id="conv_123",
            last_activity=datetime.now(UTC),
        )

        with (
            patch.object(tool, "_load_conversation", return_value=context),
            patch.object(tool, "_save_message_to_database", return_value=None),
            patch.object(tool, "_cache_conversation", return_value=None),
        ):
            result = await tool.execute(
                action="add_message",
                phone=sample_phone,
                content="New message",
                direction="inbound",
            )

            assert result.success is True
            # Should have exactly message_limit messages (old ones trimmed)
            assert len(result.data.messages) == tool.message_limit

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool, sample_phone):
        """Test handling of unknown action."""
        result = await tool.execute(action="unknown_action", phone=sample_phone)

        assert result.success is False
        assert "Unknown action" in result.error
