"""
Tests for the chat endpoint with Claude AI integration.
Tests conversation flow, database interactions, and error handling.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

# Create test client
client = TestClient(app)


class TestChatEndpoint:
    """Test chat endpoint with Claude integration."""

    def test_chat_endpoint_new_customer(self, mock_claude_api, claude_response):
        """Test chat endpoint with new customer."""
        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response(
            "hey! I'm Marty, what're you looking for?"
        )

        response = client.post(
            "/chat", json={"message": "Hello", "phone": "+1234567890"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["response"] == "hey! I'm Marty, what're you looking for?"
        assert "conversation_id" in data
        assert "customer_id" in data

    def test_chat_endpoint_existing_customer(self, mock_claude_api, claude_response):
        """Test chat endpoint with existing customer."""
        phone = "+1555123456"

        # First request to create customer
        mock_claude_api.messages.create.return_value = claude_response(
            "hey! what're you looking for?"
        )

        # First chat
        response1 = client.post("/chat", json={"message": "Hello", "phone": phone})

        assert response1.status_code == 200
        data1 = response1.json()
        customer_id1 = data1["customer_id"]
        conversation_id1 = data1["conversation_id"]

        # Second chat (should use existing customer and conversation)
        mock_claude_api.messages.create.return_value = claude_response(
            "try Effective Python"
        )

        response2 = client.post(
            "/chat", json={"message": "I need a Python book", "phone": phone}
        )

        assert response2.status_code == 200
        data2 = response2.json()

        # Should use same customer and conversation
        assert data2["customer_id"] == customer_id1
        assert data2["conversation_id"] == conversation_id1
        assert data2["response"] == "try Effective Python"

    def test_chat_endpoint_conversation_history(self, mock_claude_api, claude_response):
        """Test that conversation history is passed to AI."""
        phone = "+1555999888"

        # First message
        mock_claude_api.messages.create.return_value = claude_response("first response")

        # First message
        client.post("/chat", json={"message": "Hello Marty", "phone": phone})

        # Second message - should include history
        mock_claude_api.messages.create.return_value = claude_response(
            "second response"
        )

        client.post("/chat", json={"message": "I need a book", "phone": phone})

        # Check that the second call included conversation history
        assert mock_claude_api.messages.create.call_count == 2
        second_call = mock_claude_api.messages.create.call_args_list[1]
        messages = second_call[1]["messages"]

        # Should have previous messages plus current message
        assert len(messages) >= 2

        # Check that conversation history was included
        # (excluding the current message we just added)
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        assert len(user_messages) >= 1

    def test_chat_endpoint_customer_context(self, mock_claude_api, claude_response):
        """Test that customer context is passed to AI."""
        phone = "+1555444333"

        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response("hey there!")

        response = client.post("/chat", json={"message": "Hello", "phone": phone})

        assert response.status_code == 200

        # Check that customer context was passed
        call_args = mock_claude_api.messages.create.call_args
        system_prompt = "\n\n".join(b["text"] for b in call_args[1]["system"])
        assert phone in system_prompt  # Phone should be in customer context

    def test_chat_endpoint_ai_error_handling(self, mock_claude_api, claude_response):
        """Test chat endpoint when AI service fails."""
        # Make the mock raise an exception
        mock_claude_api.messages.create.side_effect = Exception("API Error")

        response = client.post(
            "/chat", json={"message": "Hello", "phone": "+1555000111"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should return error message from AI client
        assert "having trouble thinking" in data["response"]
        assert "🤔" in data["response"]

    def test_chat_endpoint_invalid_request(self):
        """Test chat endpoint with invalid request data."""
        # Missing phone number
        response = client.post("/chat", json={"message": "Hello"})

        assert response.status_code == 422  # Validation error

    def test_chat_endpoint_empty_message(self):
        """Test chat endpoint with empty message."""
        response = client.post("/chat", json={"message": "", "phone": "+1555222333"})

        # Empty messages should return validation error
        assert response.status_code == 500
        data = response.json()
        assert "Chat processing failed" in data["detail"]

    def test_chat_endpoint_long_message(self, mock_claude_api, claude_response):
        """Test chat endpoint with very long message."""
        long_message = "A" * 1000  # 1000 character message

        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response(
            "that's a lot of text!"
        )

        response = client.post(
            "/chat", json={"message": long_message, "phone": "+1555333444"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "that's a lot of text!"

    def test_chat_endpoint_multiple_conversations(
        self, mock_claude_api, claude_response
    ):
        """Test multiple simultaneous conversations."""
        phone1 = "+1555111111"
        phone2 = "+1555222222"

        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response("response")

        # Start two conversations
        response1 = client.post(
            "/chat", json={"message": "Hello from phone 1", "phone": phone1}
        )

        response2 = client.post(
            "/chat", json={"message": "Hello from phone 2", "phone": phone2}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Should have different customers and conversations
        assert data1["customer_id"] != data2["customer_id"]
        assert data1["conversation_id"] != data2["conversation_id"]

    def test_chat_endpoint_database_error_handling(self):
        """Test chat endpoint error handling for database errors."""
        with patch(
            "src.main.get_customer_by_phone", side_effect=Exception("Database Error")
        ):
            response = client.post(
                "/chat", json={"message": "Hello", "phone": "+1555777888"}
            )

            assert response.status_code == 500
            data = response.json()
            assert "Chat processing failed" in data["detail"]

    def test_chat_endpoint_response_format(self, mock_claude_api, claude_response):
        """Test that chat endpoint returns correct response format."""
        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response("test response")

        response = client.post(
            "/chat", json={"message": "Hello", "phone": "+1555666777"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        required_fields = ["response", "conversation_id", "customer_id"]
        for field in required_fields:
            assert field in data
            assert isinstance(data[field], str)
            assert len(data[field]) > 0

    def test_chat_endpoint_special_characters(self, mock_claude_api, claude_response):
        """Test chat endpoint with special characters in message."""
        special_message = (
            "Hello! 🤖 Can you help me find a book with émojis and accénts?"
        )

        # Use the global mock with a specific response
        mock_claude_api.messages.create.return_value = claude_response(
            "sure! what genre?"
        )

        response = client.post(
            "/chat", json={"message": special_message, "phone": "+1555888999"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "sure! what genre?"

        # Verify the message was passed correctly to AI
        call_args = mock_claude_api.messages.create.call_args
        messages = call_args[1]["messages"]
        user_message = next(msg for msg in messages if msg["role"] == "user")
        assert user_message["content"] == special_message


class TestChatIntegrationScenarios:
    """Test realistic chat integration scenarios."""

    def test_book_recommendation_conversation(self, mock_claude_api, claude_response):
        """Test a complete book recommendation conversation."""
        phone = "+1555123000"

        # Mock AI responses for a book recommendation flow
        ai_responses = [
            "hey! I'm Marty, what're you looking for?",
            "what level are you at?",
            "try Effective Python by Brett Slatkin, it's perfect for intermediate",
            "cool! want me to ship it or you picking up?",
        ]

        user_messages = [
            "Hello",
            "I need a Python book",
            "intermediate level",
            "I'll take it",
        ]

        customer_id: str | None = None
        conversation_id: str | None = None

        for i, (user_msg, ai_resp) in enumerate(
            zip(user_messages, ai_responses, strict=True)
        ):
            # Use the global mock with a specific response
            mock_claude_api.messages.create.return_value = claude_response(ai_resp)

            response = client.post("/chat", json={"message": user_msg, "phone": phone})

            assert response.status_code == 200
            data = response.json()
            assert data["response"] == ai_resp

            # All messages should use the same customer and conversation
            if i == 0:
                customer_id = data["customer_id"]
                conversation_id = data["conversation_id"]
            else:
                assert data["customer_id"] == customer_id
                assert data["conversation_id"] == conversation_id

    def test_error_recovery_conversation(self, mock_claude_api, claude_response):
        """Test conversation recovery after AI errors."""
        phone = "+1555999000"

        # First message fails
        mock_claude_api.messages.create.side_effect = Exception("AI Error")

        response1 = client.post("/chat", json={"message": "Hello", "phone": phone})

        assert response1.status_code == 200
        data1 = response1.json()
        assert "having trouble thinking" in data1["response"]

        # Second message succeeds
        mock_claude_api.messages.create.side_effect = None
        mock_claude_api.messages.create.return_value = claude_response(
            "hey! what're you looking for?"
        )

        response2 = client.post("/chat", json={"message": "Try again", "phone": phone})

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["response"] == "hey! what're you looking for?"

        # Should use same customer and conversation
        assert data2["customer_id"] == data1["customer_id"]
        assert data2["conversation_id"] == data1["conversation_id"]
