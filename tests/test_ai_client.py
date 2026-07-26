"""
Tests for AI client and Claude integration.
Tests prompt loading, response generation, error handling, and mocking.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.ai_client import (
    MARTY_SYSTEM_PROMPT,
    RENAME_THREAD_MIN_HISTORY,
    ConversationMessage,
    _render_tool_result,
    generate_ai_response,
    load_system_prompt,
)
from src.config import config


class TestSystemPromptLoading:
    """Test system prompt loading functionality."""

    def test_load_system_prompt_success(self):
        """Test successful loading of system prompt."""
        prompt = load_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 1000  # Should be substantial
        assert "martinus trismegistus" in prompt
        assert "never invent books" in prompt.lower()

    def test_load_system_prompt_file_not_found(self, tmp_path):
        """Test fallback when prompt file doesn't exist."""
        with (
            patch.object(Path, "read_text", side_effect=FileNotFoundError),
            patch("src.ai_client.logger.warning"),
        ):
            prompt = load_system_prompt()
            assert isinstance(prompt, str)
            assert "Marty" in prompt


class TestConversationMessageValidation:
    """Test conversation message validation and processing."""

    def test_conversation_message_creation(self):
        """Test creating a ConversationMessage."""
        from datetime import datetime

        message = ConversationMessage(
            role="user", content="Hello", timestamp=datetime.now()
        )

        assert message.role == "user"
        assert message.content == "Hello"
        assert isinstance(message.timestamp, datetime)

    def test_conversation_message_validation(self):
        """Test validation of ConversationMessage fields."""
        from datetime import datetime

        # Test valid roles
        valid_roles = ["user", "assistant"]
        for role in valid_roles:
            msg = ConversationMessage(
                role=role, content="test", timestamp=datetime.now()
            )
            assert msg.role == role


class TestGenerateAIResponse:
    """Test AI response generation with mocked Claude API."""

    @pytest.mark.asyncio
    async def test_generate_ai_response_success(self, mock_llm_api, llm_response):
        """Test successful AI response generation."""
        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "hey! what're you looking for?"
        )

        response = await generate_ai_response("Hello Marty!", [])

        assert response == ("hey! what're you looking for?", [])
        mock_llm_api.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_conversation_history(
        self, mock_llm_api, llm_response
    ):
        """Test AI response generation with conversation history."""
        from datetime import datetime

        history = [
            ConversationMessage(
                role="user", content="I need a Python book", timestamp=datetime.now()
            ),
            ConversationMessage(
                role="assistant",
                content="what level are you?",
                timestamp=datetime.now(),
            ),
        ]

        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "try Effective Python"
        )

        response = await generate_ai_response("intermediate", history)

        assert response == ("try Effective Python", [])

        # Check that conversation history was included in the first call
        call_args = mock_llm_api.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        # system turn, then 2 history messages, then the current one
        assert len(messages) >= 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "I need a Python book"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "what level are you?"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "intermediate"

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_customer_context(
        self, mock_llm_api, llm_response
    ):
        """Test AI response generation with customer context."""
        customer_context = {
            "name": "John Doe",
            "phone": "+1234567890",
            "customer_id": "123",
            "current_time": "2024-01-15T10:30:00Z",
            "current_date": "2024-01-15",
            "current_day": "Monday",
        }

        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "hey John! looking for any specific genre?"
        )

        response = await generate_ai_response("Hello", [], customer_context)

        assert response == ("hey John! looking for any specific genre?", [])

        # Per-request context rides on the final user turn, not the system message
        call_args = mock_llm_api.chat.completions.create.call_args
        user_turn = call_args[1]["messages"][-1]["content"]
        assert "Customer name: John Doe" in user_turn
        assert "Phone: +1234567890" in user_turn
        assert "Customer ID: 123" in user_turn
        assert "Current time: 2024-01-15T10:30:00Z" in user_turn
        assert "Current date: 2024-01-15" in user_turn
        assert "Day of week: Monday" in user_turn

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_cultural_name(
        self, mock_llm_api, llm_response
    ):
        """Test AI response generation with culturally diverse names."""
        customer_context = {
            "name": "José García-López",
            "phone": "+1234567890",
            "customer_id": "789",
        }

        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "¡Hola José García-López!"
        )

        response = await generate_ai_response("Hello", [], customer_context)

        assert response == ("¡Hola José García-López!", [])

        # Full name is passed through for the model to handle culturally
        call_args = mock_llm_api.chat.completions.create.call_args
        user_turn = call_args[1]["messages"][-1]["content"]
        assert "Customer name: José García-López" in user_turn

    @pytest.mark.asyncio
    async def test_generate_ai_response_single_name(self, mock_llm_api, llm_response):
        """Test AI response generation with single name (e.g., Madonna, Cher)."""
        customer_context = {
            "name": "Madonna",
            "phone": "+1234567890",
            "customer_id": "101",
        }

        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "hey Madonna! what can I help you with?"
        )

        response = await generate_ai_response("Hello", [], customer_context)

        assert response == ("hey Madonna! what can I help you with?", [])

        # Check that single name is handled correctly
        call_args = mock_llm_api.chat.completions.create.call_args
        user_turn = call_args[1]["messages"][-1]["content"]
        assert "Customer name: Madonna" in user_turn

    @pytest.mark.asyncio
    async def test_generate_ai_response_no_customer_context(
        self, mock_llm_api, llm_response
    ):
        """Test AI response generation without customer context."""
        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "hey! what can I help you with?"
        )

        response = await generate_ai_response("Hello", [])

        assert response == ("hey! what can I help you with?", [])

        # Check that only base system prompt is used
        call_args = mock_llm_api.chat.completions.create.call_args
        user_turn = call_args[1]["messages"][-1]["content"]
        assert "Customer Context:" not in user_turn
        assert "Current Time & Date:" not in user_turn

    @pytest.mark.asyncio
    async def test_generate_ai_response_empty_customer_context(
        self, mock_llm_api, llm_response
    ):
        """Test AI response generation with empty customer context."""
        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "hello! what are you looking for?"
        )

        response = await generate_ai_response("Hello", [], {})

        assert response == ("hello! what are you looking for?", [])

        # Check that empty context doesn't add extra sections
        call_args = mock_llm_api.chat.completions.create.call_args
        user_turn = call_args[1]["messages"][-1]["content"]
        assert "Customer Context:" not in user_turn
        assert "Current Time & Date:" not in user_turn

    @pytest.mark.asyncio
    async def test_generate_ai_response_minimal_context(
        self, mock_llm_api, llm_response
    ):
        """Test AI response generation with minimal customer context."""
        customer_context = {
            "customer_id": "999",
            # Only customer_id provided
        }

        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "hello! what are you looking for?"
        )

        response = await generate_ai_response("Hello", [], customer_context)

        assert response == ("hello! what are you looking for?", [])

        # Check that only customer_id is included
        call_args = mock_llm_api.chat.completions.create.call_args
        user_turn = call_args[1]["messages"][-1]["content"]
        assert "Customer ID: 999" in user_turn
        assert "Customer name:" not in user_turn
        assert "Phone:" not in user_turn

    @pytest.mark.asyncio
    async def test_generate_ai_response_api_error(self, mock_llm_api):
        """Test error handling when Claude API fails."""
        # Make the mock raise an exception
        mock_llm_api.chat.completions.create.side_effect = Exception("API Error")

        with patch("src.ai_client.logger.error") as mock_error:
            response = await generate_ai_response("Hello", [])

            assert "brain's lagging" in response[0]
            assert response[1] == []
            mock_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_ai_response_empty_content(self, mock_llm_api, llm_response):
        """Test handling of empty response content."""
        mock_llm_api.chat.completions.create.return_value = llm_response("")

        response = await generate_ai_response("Hello", [])

        assert response == ("I'm having trouble generating a response right now.", [])

    @pytest.mark.asyncio
    async def test_generate_ai_response_whitespace_content(
        self, mock_llm_api, llm_response
    ):
        """Whitespace-only content is treated as empty."""
        mock_llm_api.chat.completions.create.return_value = llm_response("   \n  ")

        response = await generate_ai_response("Hello", [])

        assert response == ("I'm having trouble generating a response right now.", [])

    @pytest.mark.asyncio
    async def test_llm_api_parameters(self, mock_llm_api, llm_response):
        """Test that correct parameters are passed to the LLM API."""
        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "test response"
        )

        await generate_ai_response("Hello", [])

        call_args = mock_llm_api.chat.completions.create.call_args
        assert call_args[1]["model"] == config.MARTY_MODEL
        assert call_args[1]["max_tokens"] == config.MARTY_MAX_TOKENS
        assert call_args[1]["temperature"] == config.MARTY_TEMPERATURE
        assert call_args[1]["reasoning_effort"] == config.MARTY_CHAT_REASONING_EFFORT
        assert call_args[1]["messages"][0]["role"] == "system"
        assert call_args[1]["tools"]

    @pytest.mark.asyncio
    async def test_context_rides_on_user_turn_not_system(
        self, mock_llm_api, llm_response
    ):
        """Per-request context must sit on the user turn, never in the system message."""
        customer_context = {
            "name": "John",
            "phone": "+1234567890",
            "customer_id": "123",
            "current_time": "2024-01-15T10:30:00Z",
            "current_date": "2024-01-15",
            "current_day": "Monday",
        }

        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response("hey John!")

        await generate_ai_response("Hello", [], customer_context)

        call_args = mock_llm_api.chat.completions.create.call_args
        system_prompt = call_args[1]["messages"][0]["content"]
        user_turn = call_args[1]["messages"][-1]["content"]

        # The persona still lives in the system message
        assert len(system_prompt) > 1000
        assert "martinus trismegistus" in system_prompt

        # ...but nothing per-request does
        assert "Customer Context:" not in system_prompt
        assert "Current Time & Date:" not in system_prompt
        assert "John" not in system_prompt

        assert "Customer Context:" in user_turn
        assert "Current Time & Date:" in user_turn
        assert "Current time: 2024-01-15T10:30:00Z" in user_turn
        assert "Current date: 2024-01-15" in user_turn
        assert "Day of week: Monday" in user_turn
        assert "Customer name: John" in user_turn


class TestEnvironmentIntegration:
    """Test environment integration and configuration."""

    def test_anthropic_api_key_loading(self):
        """Test that API key is loaded from environment."""
        # Test with environment variable
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            # Import client after setting env var
            from src.ai_client import client

            assert hasattr(client, "api_key")

    def test_missing_api_key_handling(self):
        """Test behavior when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise an error during import
            from src.ai_client import client

            # Client should be created but with empty API key
            assert hasattr(client, "api_key")


class TestSystemPromptContent:
    """Test system prompt content and structure."""

    def test_system_prompt_contains_required_elements(self):
        """Test that system prompt contains required elements."""
        assert "martinus trismegistus" in MARTY_SYSTEM_PROMPT
        assert "never invent books" in MARTY_SYSTEM_PROMPT.lower()
        assert len(MARTY_SYSTEM_PROMPT) > 1000

    def test_system_prompt_is_loaded_correctly(self):
        """Test that system prompt is loaded correctly from file."""
        # The prompt should be loaded from the file
        assert isinstance(MARTY_SYSTEM_PROMPT, str)
        assert len(MARTY_SYSTEM_PROMPT) > 10

    @pytest.mark.asyncio
    async def test_system_prompt_used_in_generation(self, mock_llm_api, llm_response):
        """Test that system prompt is used in AI generation."""
        # Use the global mock with a specific response
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "test response"
        )

        await generate_ai_response("Hello", [])

        call_args = mock_llm_api.chat.completions.create.call_args
        system_prompt = call_args[1]["messages"][0]["content"]

        # Should start with the loaded system prompt
        assert "martinus trismegistus" in system_prompt
        assert len(system_prompt) > 1000


class TestToolResultRendering:
    """Tool results are billed as input, so the model's view is budgeted."""

    def test_bulk_fields_dropped(self):
        book = {
            "title": "Dune",
            "author": "Frank Herbert",
            "editions": [{"isbn": str(i)} for i in range(500)],
            "cached_tags": {"Genre": ["scifi"] * 200},
        }

        rendered = _render_tool_result([book])

        assert "Dune" in rendered
        assert "Frank Herbert" in rendered
        assert "editions" not in rendered
        assert "cached_tags" not in rendered

    def test_source_data_is_not_mutated(self):
        """The embed builder and enricher still read the untouched result."""
        book = {"title": "Dune", "editions": [{"isbn": "1"}], "cached_tags": {"a": 1}}

        _render_tool_result([book])

        assert book["editions"] == [{"isbn": "1"}]
        assert book["cached_tags"] == {"a": 1}

    def test_long_prose_is_clipped(self):
        book = {"title": "Dune", "description": "x" * 5000}

        rendered = _render_tool_result([book])

        assert len(rendered) < 1000
        assert "..." in rendered

    def test_long_lists_drop_whole_entries(self):
        books = [{"title": f"Book {i}", "description": "y" * 300} for i in range(100)]

        rendered = _render_tool_result(books)

        assert "showing" in rendered and "of 100 results" in rendered
        # Whole records only - never a record severed mid-structure
        assert rendered.split("\n\n[showing")[0].endswith("]")

    def test_small_results_pass_through(self):
        data = {"slug": "returns", "body": "7 days with receipt"}

        assert _render_tool_result(data) == str(data)


class TestToolGating:
    """rename_thread must not be offered before there is a topic to name."""

    @pytest.mark.asyncio
    async def test_rename_thread_withheld_on_first_message(
        self, mock_llm_api, llm_response
    ):
        mock_llm_api.chat.completions.create.return_value = llm_response("ok")

        await generate_ai_response("recommend me some fantasy books", [])

        tools = mock_llm_api.chat.completions.create.call_args[1]["tools"]
        names = [t["function"]["name"] for t in tools]
        assert "rename_thread" not in names
        assert "hardcover_api" in names, "only rename_thread should be withheld"

    @pytest.mark.asyncio
    async def test_withheld_tool_is_refused_if_called_anyway(
        self, mock_llm_api, llm_response
    ):
        """The schema is a hint; dispatch is where the gate has to hold."""
        from unittest.mock import MagicMock

        call = MagicMock()
        call.id = "call_1"
        call.function.name = "rename_thread"
        call.function.arguments = '{"thread_name": "sci-fi recs"}'

        mock_llm_api.chat.completions.create.side_effect = [
            llm_response("", tool_calls=[call]),
            llm_response("sure, what are you after?"),
        ]

        with patch("src.tools.ToolRegistry.get_tool") as get_tool:
            text, executed = await generate_ai_response("hi", [])

            get_tool.assert_not_called()

        assert executed == []
        assert text == "sure, what are you after?"

        follow_up = mock_llm_api.chat.completions.create.call_args_list[1][1][
            "messages"
        ]
        refusal = next(m for m in follow_up if m["role"] == "tool")
        assert "not available" in refusal["content"]

    @pytest.mark.asyncio
    async def test_rename_thread_offered_once_conversation_has_legs(
        self, mock_llm_api, llm_response
    ):
        from datetime import datetime

        mock_llm_api.chat.completions.create.return_value = llm_response("ok")
        history = [
            ConversationMessage(
                role="user" if i % 2 == 0 else "assistant",
                content=f"message {i}",
                timestamp=datetime.now(),
            )
            for i in range(RENAME_THREAD_MIN_HISTORY)
        ]

        await generate_ai_response("and something darker", history)

        tools = mock_llm_api.chat.completions.create.call_args[1]["tools"]
        assert "rename_thread" in [t["function"]["name"] for t in tools]


class TestPromptOrdering:
    """Neuralwatt caches on the literal token prefix, so stable bytes must come first.

    There is no cache_control breakpoint to set - ordering is the only lever.
    """

    @pytest.mark.asyncio
    async def test_system_prompt_identical_across_customers(
        self, mock_llm_api, llm_response
    ):
        """The cached head must be byte-identical for every customer."""
        mock_llm_api.chat.completions.create.return_value = llm_response("ok")

        await generate_ai_response(
            "hi", [], {"name": "John", "current_time": "2024-01-15T10:00:00Z"}
        )
        first = mock_llm_api.chat.completions.create.call_args[1]["messages"][0][
            "content"
        ]

        await generate_ai_response(
            "hi", [], {"name": "Jane", "current_time": "2024-06-02T22:31:00Z"}
        )
        second = mock_llm_api.chat.completions.create.call_args[1]["messages"][0][
            "content"
        ]

        assert first == second

    @pytest.mark.asyncio
    async def test_history_precedes_volatile_context(self, mock_llm_api, llm_response):
        """Context goes on the final turn so history stays a stable growing prefix."""
        from datetime import datetime

        mock_llm_api.chat.completions.create.return_value = llm_response("ok")
        history = [
            ConversationMessage(
                role="user", content="earlier question", timestamp=datetime.now()
            )
        ]

        await generate_ai_response("hi", history, {"name": "John"})

        messages = mock_llm_api.chat.completions.create.call_args[1]["messages"]
        assert messages[1]["content"] == "earlier question"
        assert "Customer Context:" not in messages[1]["content"]
        assert "Customer Context:" in messages[-1]["content"]
        assert messages[-1]["content"].endswith("hi")

    @pytest.mark.asyncio
    async def test_tools_sent_on_every_call(self, mock_llm_api, llm_response):
        """A call that omits tools changes the prefix and cold-prefills."""
        mock_llm_api.chat.completions.create.return_value = llm_response("ok")
        await generate_ai_response("hi", [])
        for call in mock_llm_api.chat.completions.create.call_args_list:
            assert call[1].get("tools"), "every call must carry the tool definitions"


class TestResponseProcessing:
    """Test response processing and content extraction."""

    @pytest.mark.asyncio
    async def test_response_content_extraction(self, mock_llm_api, llm_response):
        """Test proper extraction of response content."""
        mock_llm_api.chat.completions.create.return_value = llm_response(
            "extracted text response"
        )

        response = await generate_ai_response("Hello", [])

        assert response == ("extracted text response", [])

    @pytest.mark.asyncio
    async def test_response_fallback_handling(self, mock_llm_api, llm_response):
        """Test fallback handling when the model returns no content."""
        mock_llm_api.chat.completions.create.return_value = llm_response(None)

        response = await generate_ai_response("Hello", [])

        assert response == ("I'm having trouble generating a response right now.", [])
