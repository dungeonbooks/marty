"""
Tests for AI client and Claude integration.
Tests prompt loading, response generation, error handling, and mocking.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ai_client import (
    MARTY_SYSTEM_PROMPT,
    ConversationMessage,
    generate_ai_response,
    load_system_prompt,
)


class TestSystemPromptLoading:
    """Test system prompt loading functionality."""

    def test_load_system_prompt_success(self):
        """Test successful loading of system prompt."""
        prompt = load_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 1000  # Should be substantial
        assert "Martinus Trismegistus" in prompt
        assert "Never invent books" in prompt  # Safety feature
        assert "Text Formatting Rules" in prompt  # Operational details

    def test_load_system_prompt_custom_file(self):
        """Test loading system prompt from custom file."""
        # Create a temporary test prompt file
        test_prompt = "Test prompt content"
        test_file = Path(__file__).parent / "test_prompt.txt"
        test_file.write_text(test_prompt)

        try:
            prompt = load_system_prompt(str(test_file))
            assert prompt == test_prompt
        finally:
            test_file.unlink()  # Clean up

    def test_load_system_prompt_file_not_found(self):
        """Test fallback when prompt file doesn't exist."""
        with patch("src.ai_client.logger.warning") as mock_warning:
            prompt = load_system_prompt("nonexistent_file.txt")

            assert isinstance(prompt, str)
            assert "Marty" in prompt  # Should contain fallback content
            assert len(prompt) > 10  # Should not be empty

            # Check that warning was logged instead of printed
            mock_warning.assert_called_once()
            assert "nonexistent_file.txt" in mock_warning.call_args[0][0]
            assert "not found" in mock_warning.call_args[0][0]


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
    async def test_generate_ai_response_success(self, mock_claude_api, claude_response):
        """Test successful AI response generation."""
        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response(
            "hey! what're you looking for?"
        )

        response = await generate_ai_response("Hello Marty!", [])

        assert response == ("hey! what're you looking for?", [])
        mock_claude_api.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_conversation_history(
        self, mock_claude_api, claude_response
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
        mock_claude_api.messages.create.return_value = claude_response(
            "try Effective Python"
        )

        response = await generate_ai_response("intermediate", history)

        assert response == ("try Effective Python", [])

        # Check that conversation history was included in the first call
        call_args = mock_claude_api.messages.create.call_args
        messages = call_args[1]["messages"]
        # The first call should have 3 messages: 2 history + 1 current
        assert len(messages) >= 3  # May have additional tool-related messages
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "I need a Python book"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "what level are you?"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "intermediate"

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_customer_context(
        self, mock_claude_api, claude_response
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
        mock_claude_api.messages.create.return_value = claude_response(
            "hey John! looking for any specific genre?"
        )

        response = await generate_ai_response("Hello", [], customer_context)

        assert response == ("hey John! looking for any specific genre?", [])

        # Check that customer context was included in system prompt
        call_args = mock_claude_api.messages.create.call_args
        system_prompt = call_args[1]["system"]
        assert "Customer name: John Doe" in system_prompt
        assert "Phone: +1234567890" in system_prompt
        assert "Customer ID: 123" in system_prompt
        assert "Current time: 2024-01-15T10:30:00Z" in system_prompt
        assert "Current date: 2024-01-15" in system_prompt
        assert "Day of week: Monday" in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_with_cultural_name(
        self, mock_claude_api, claude_response
    ):
        """Test AI response generation with culturally diverse names."""
        customer_context = {
            "name": "José García-López",
            "phone": "+1234567890",
            "customer_id": "789",
        }

        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response(
            "¡Hola José García-López!"
        )

        response = await generate_ai_response("Hello", [], customer_context)

        assert response == ("¡Hola José García-López!", [])

        # Check that full name is passed to Claude for cultural handling
        call_args = mock_claude_api.messages.create.call_args
        system_prompt = call_args[1]["system"]
        assert "Customer name: José García-López" in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_single_name(
        self, mock_claude_api, claude_response
    ):
        """Test AI response generation with single name (e.g., Madonna, Cher)."""
        customer_context = {
            "name": "Madonna",
            "phone": "+1234567890",
            "customer_id": "101",
        }

        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response(
            "hey Madonna! what can I help you with?"
        )

        response = await generate_ai_response("Hello", [], customer_context)

        assert response == ("hey Madonna! what can I help you with?", [])

        # Check that single name is handled correctly
        call_args = mock_claude_api.messages.create.call_args
        system_prompt = call_args[1]["system"]
        assert "Customer name: Madonna" in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_no_customer_context(
        self, mock_claude_api, claude_response
    ):
        """Test AI response generation without customer context."""
        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response(
            "hey! what can I help you with?"
        )

        response = await generate_ai_response("Hello", [])

        assert response == ("hey! what can I help you with?", [])

        # Check that only base system prompt is used
        call_args = mock_claude_api.messages.create.call_args
        system_prompt = call_args[1]["system"]
        assert "Customer Context:" not in system_prompt
        assert "Current Time & Date:" not in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_empty_customer_context(
        self, mock_claude_api, claude_response
    ):
        """Test AI response generation with empty customer context."""
        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response(
            "hello! what are you looking for?"
        )

        response = await generate_ai_response("Hello", [], {})

        assert response == ("hello! what are you looking for?", [])

        # Check that empty context doesn't add extra sections
        call_args = mock_claude_api.messages.create.call_args
        system_prompt = call_args[1]["system"]
        assert "Customer Context:" not in system_prompt
        assert "Current Time & Date:" not in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_minimal_context(
        self, mock_claude_api, claude_response
    ):
        """Test AI response generation with minimal customer context."""
        customer_context = {
            "customer_id": "999",
            # Only customer_id provided
        }

        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response(
            "hello! what are you looking for?"
        )

        response = await generate_ai_response("Hello", [], customer_context)

        assert response == ("hello! what are you looking for?", [])

        # Check that only customer_id is included
        call_args = mock_claude_api.messages.create.call_args
        system_prompt = call_args[1]["system"]
        assert "Customer ID: 999" in system_prompt
        assert "Customer name:" not in system_prompt
        assert "Phone:" not in system_prompt

    @pytest.mark.asyncio
    async def test_generate_ai_response_api_error(self, mock_claude_api):
        """Test error handling when Claude API fails."""
        # Make the mock raise an exception
        mock_claude_api.messages.create.side_effect = Exception("API Error")

        with patch("src.ai_client.logger.error") as mock_error:
            response = await generate_ai_response("Hello", [])

            assert "having trouble thinking" in response[0]
            assert "🤔" in response[0]
            assert response[1] == []
            mock_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_ai_response_empty_content(self, mock_claude_api):
        """Test handling of empty response content."""
        # Create a mock response with empty content
        mock_response = MagicMock()
        mock_response.content = []
        mock_claude_api.messages.create.return_value = mock_response

        response = await generate_ai_response("Hello", [])

        assert response == ("I'm having trouble generating a response right now.", [])

    @pytest.mark.asyncio
    async def test_generate_ai_response_non_text_content(self, mock_claude_api):
        """Test handling of non-text content in response."""
        # Create a mock response that returns a string when converted to string
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "fallback content"  # Just give it a text attribute
        mock_response.content = [mock_content]
        mock_claude_api.messages.create.return_value = mock_response

        response = await generate_ai_response("Hello", [])

        # Should get the text content
        assert isinstance(response, tuple)
        assert response == ("fallback content", [])

    @pytest.mark.asyncio
    async def test_claude_api_parameters(self, mock_claude_api, claude_response):
        """Test that correct parameters are passed to Claude API."""
        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response("test response")

        await generate_ai_response("Hello", [])

        call_args = mock_claude_api.messages.create.call_args
        assert call_args[1]["model"] == "claude-sonnet-4-6"
        assert call_args[1]["max_tokens"] == 500
        assert call_args[1]["temperature"] == 0.7
        assert "system" in call_args[1]
        assert "messages" in call_args[1]

    @pytest.mark.asyncio
    async def test_system_prompt_with_context(self, mock_claude_api, claude_response):
        """Test system prompt construction with customer context."""
        customer_context = {
            "name": "John",
            "phone": "+1234567890",
            "customer_id": "123",
            "current_time": "2024-01-15T10:30:00Z",
            "current_date": "2024-01-15",
            "current_day": "Monday",
        }

        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response("hey John!")

        await generate_ai_response("Hello", [], customer_context)

        call_args = mock_claude_api.messages.create.call_args
        system_prompt = call_args[1]["system"]

        # Check base prompt is included
        assert len(system_prompt) > 1000  # Should be substantial

        # Check customer context is appended
        assert "Customer Context:" in system_prompt
        assert "Current Time & Date:" in system_prompt
        assert "Current time: 2024-01-15T10:30:00Z" in system_prompt
        assert "Current date: 2024-01-15" in system_prompt
        assert "Day of week: Monday" in system_prompt
        assert "Customer name: John" in system_prompt


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
        assert "Martinus Trismegistus" in MARTY_SYSTEM_PROMPT
        assert "Never invent books" in MARTY_SYSTEM_PROMPT
        assert "Text Formatting Rules" in MARTY_SYSTEM_PROMPT
        assert len(MARTY_SYSTEM_PROMPT) > 1000

    def test_system_prompt_is_loaded_correctly(self):
        """Test that system prompt is loaded correctly from file."""
        # The prompt should be loaded from the file
        assert isinstance(MARTY_SYSTEM_PROMPT, str)
        assert len(MARTY_SYSTEM_PROMPT) > 10

    @pytest.mark.asyncio
    async def test_system_prompt_used_in_generation(
        self, mock_claude_api, claude_response
    ):
        """Test that system prompt is used in AI generation."""
        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response("test response")

        await generate_ai_response("Hello", [])

        call_args = mock_claude_api.messages.create.call_args
        system_prompt = call_args[1]["system"]

        # Should start with the loaded system prompt
        assert "Martinus Trismegistus" in system_prompt
        assert len(system_prompt) > 1000


class TestResponseProcessing:
    """Test response processing and content extraction."""

    @pytest.mark.asyncio
    async def test_response_content_extraction(self, mock_claude_api):
        """Test proper extraction of response content."""
        # Create a mock response with proper structure
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "extracted text response"
        mock_response.content = [mock_content]
        mock_claude_api.messages.create.return_value = mock_response

        response = await generate_ai_response("Hello", [])

        assert response == ("extracted text response", [])

    @pytest.mark.asyncio
    async def test_response_fallback_handling(self, mock_claude_api):
        """Test fallback handling for malformed responses."""
        # Create a mock response with no content
        mock_response = MagicMock()
        mock_response.content = None
        mock_claude_api.messages.create.return_value = mock_response

        response = await generate_ai_response("Hello", [])

        assert response == ("I'm having trouble generating a response right now.", [])
