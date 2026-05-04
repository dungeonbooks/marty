"""
Example Chat Flow - Demonstrates tool calling with ToolRegistry.

This example shows how to use the ToolRegistry system for:
1. Programmatic tool calling
2. Tool discovery and registration
3. Claude-compatible tool definitions
4. Tool result handling and error management
"""

import asyncio
import logging
from typing import Any

import structlog

from src.ai_client import ConversationMessage, generate_ai_response
from src.tools import tool_registry

logger = structlog.get_logger(__name__)


class ToolCallingChatProcessor:
    """Demonstrates tool calling patterns using ToolRegistry."""

    def __init__(self):
        self.registry = tool_registry
        self.available_tools = self.registry.list_tools()
        logger.info(f"Available tools: {self.available_tools}")

    async def process_chat_message(
        self, phone: str, user_message: str
    ) -> dict[str, Any]:
        """
        Process a chat message using tool calling patterns.

        Flow:
        1. Load conversation using tool registry
        2. Generate AI response
        3. Enrich response using tool registry
        4. Save enriched response using tool registry
        5. Return comprehensive result
        """

        # Step 1: Load conversation using tool registry
        conv_tool = self.registry.get_tool("conversation_manager")
        if not conv_tool:
            raise Exception("ConversationManager tool not available")

        # Add user message to conversation
        logger.info(f"Adding user message via tool: {conv_tool.name}")
        result = await conv_tool.execute(
            action="add_message", phone=phone, content=user_message, direction="inbound"
        )

        if not result.success:
            raise Exception(f"Failed to add user message: {result.error}")

        conversation = result.data
        logger.info(f"Conversation loaded: {conversation.conversation_id}")

        # Step 2: Prepare conversation history for AI
        ai_history = []
        for msg in conversation.messages[
            -5:
        ]:  # Last 5 messages for context (now in chronological order)
            role = "user" if msg.direction == "inbound" else "assistant"
            ai_history.append(
                ConversationMessage(
                    role=role, content=msg.content, timestamp=msg.timestamp
                )
            )

        # Step 3: Generate AI response (could be enhanced with tool-calling)
        customer_context = {
            "phone": phone,
            "customer_id": conversation.customer_id,
            "current_time": "2025-01-12 16:30:00 PST",
            "current_date": "2025-01-12",
            "current_day": "Sunday",
        }

        ai_response, tool_results = await generate_ai_response(
            user_message,
            ai_history[:-1],  # Exclude the current user message from history
            customer_context,
        )

        # Step 4: Enrich AI response using tool registry
        enricher_tool = self.registry.get_tool("book_enricher")
        if not enricher_tool:
            logger.warning("BookEnricher tool not available - skipping enrichment")
            enriched_response = None
        else:
            logger.info(f"Enriching response via tool: {enricher_tool.name}")
            enrichment_result = await enricher_tool.execute(
                ai_response=ai_response,
                conversation_id=conversation.conversation_id,
                message_id=f"ai_msg_{conversation.conversation_id}_{len(conversation.messages)}",
            )

            if enrichment_result.success:
                enriched_response = enrichment_result.data
                logger.info(f"Enrichment successful: {enrichment_result.metadata}")
            else:
                logger.error(f"Enrichment failed: {enrichment_result.error}")
                enriched_response = None

        # Step 5: Save AI response using tool registry
        final_response = (
            enriched_response.original_response if enriched_response else ai_response
        )

        metadata = {}
        if enriched_response:
            metadata = {
                "books_mentioned": len(enriched_response.book_mentions),
                "books_validated": len(enriched_response.validated_books),
                "enrichment_metadata": enriched_response.enrichment_metadata,
            }

        logger.info(f"Saving AI response via tool: {conv_tool.name}")
        final_result = await conv_tool.execute(
            action="add_message",
            phone=phone,
            content=final_response,
            direction="outbound",
            metadata=metadata,
        )

        if not final_result.success:
            raise Exception(f"Failed to add AI response: {final_result.error}")

        final_conversation = final_result.data

        # Step 6: Return comprehensive result
        return {
            "response": final_response,
            "conversation_id": conversation.conversation_id,
            "books_mentioned": [
                {
                    "title": book.title,
                    "author": book.author,
                    "validated": book.validated,
                    "hardcover_id": book.hardcover_id,
                    "confidence": book.confidence,
                }
                for book in (
                    enriched_response.book_mentions if enriched_response else []
                )
            ],
            "validated_books": enriched_response.validated_books
            if enriched_response
            else [],
            "message_count": len(final_conversation.messages),
            "tools_used": [
                conv_tool.name,
                enricher_tool.name if enricher_tool else None,
            ],
            "tool_registry_stats": {
                "available_tools": len(self.available_tools),
                "tools_called": 2 if enricher_tool else 1,
            },
        }

    async def demonstrate_tool_discovery(self) -> None:
        """Demonstrate tool discovery and introspection."""
        print("\n🔧 Tool Registry Discovery")
        print("=" * 50)

        # List all available tools
        print(f"📋 Available tools: {self.available_tools}")

        # Get tool descriptions
        for tool_name in self.available_tools:
            tool = self.registry.get_tool(tool_name)
            if tool:
                print(f"\n🛠️  {tool.name}")
                print(f"   Description: {tool.description}")
                print(f"   Parameters: {list(tool.parameters.keys())}")

        # Show OpenAI-compatible tool definitions (used by Together/Kimi)
        print("\n🤖 OpenAI-Compatible Tool Definitions:")
        openai_tools = self.registry.get_openai_tools()
        for tool_def in openai_tools:
            fn = tool_def["function"]
            print(f"\n📝 {fn['name']}")
            print(f"   Description: {fn['description']}")
            print(f"   Required params: {fn['parameters']['required']}")

    async def simulate_claude_tool_calling(
        self, phone: str, user_message: str
    ) -> dict[str, Any]:
        """
        Simulate how Claude might use tools autonomously.

        This shows the potential for Claude to:
        1. Decide which tools to use
        2. Execute multiple tools in sequence
        3. Handle tool results intelligently
        """
        print("\n🤖 Claude Tool Calling Simulation")
        print("=" * 50)

        # Simulate Claude's tool decision-making process
        print("🧠 Claude analyzes message and decides to use tools...")

        # Tool 1: Load conversation context
        print("\n📞 Claude chooses: conversation_manager (load context)")
        conv_tool = self.registry.get_tool("conversation_manager")

        if conv_tool:
            result = await conv_tool.execute(action="load", phone=phone)
            if result.success:
                print(
                    f"✅ Context loaded: {result.data.conversation_id if result.data else 'new conversation'}"
                )
            else:
                print(f"❌ Context load failed: {result.error}")

        # Tool 2: Check for book-related content
        if any(
            word in user_message.lower()
            for word in ["book", "read", "recommend", "author"]
        ):
            print("\n📚 Claude detects book-related content, chooses: hardcover_api")
            hardcover_tool = self.registry.get_tool("hardcover_api")

            if hardcover_tool:
                # Extract search terms (simplified)
                search_terms = (
                    user_message.lower()
                    .replace("book", "")
                    .replace("recommend", "")
                    .strip()
                )
                if len(search_terms) > 3:
                    result = await hardcover_tool.execute(
                        action="search_books", query=search_terms, limit=3
                    )
                    if result.success:
                        books = result.data
                        print(f"✅ Found {len(books)} books matching query")
                        for book in books[:2]:  # Show first 2
                            print(
                                f"   📖 {book.get('title', 'Unknown')} by {book.get('authors', [{}])[0].get('name', 'Unknown') if book.get('authors') else 'Unknown'}"
                            )
                    else:
                        print(f"❌ Book search failed: {result.error}")

        # Tool 3: Generate contextual response
        print("\n💬 Claude generates contextual response...")

        # Simulate tool-enhanced response
        return {
            "response": "Based on your interests, I found some great books! Let me know if you'd like more details about any of them.",
            "tools_used": ["conversation_manager", "hardcover_api"],
            "tool_decisions": [
                "Loaded conversation context for personalization",
                "Searched book database for relevant recommendations",
                "Generated contextual response with book suggestions",
            ],
            "claude_reasoning": "User mentioned books, so I used both conversation context and book search to provide relevant recommendations.",
        }

    async def close(self) -> None:
        """Clean up resources."""
        # Close any tools that need cleanup
        for tool_name in self.available_tools:
            tool = self.registry.get_tool(tool_name)
            if tool and hasattr(tool, "close") and callable(tool.close):
                await tool.close()  # type: ignore


async def example_tool_calling_conversation():
    """Example conversation demonstrating tool calling patterns."""

    processor = ToolCallingChatProcessor()
    phone = "+1234567890"

    print("🤖 Marty Tool Calling Example")
    print("=" * 50)

    try:
        # Demonstrate tool discovery
        await processor.demonstrate_tool_discovery()

        # Process a book recommendation request
        print("\n\n📚 Processing Book Recommendation Request")
        print("=" * 50)
        print("👤 User: I'm looking for a good fantasy book to read")

        result1 = await processor.process_chat_message(
            phone, "I'm looking for a good fantasy book to read"
        )

        print(f"\n🤖 Marty: {result1['response']}")
        print(f"📊 Tools used: {result1['tools_used']}")
        print(f"📚 Books mentioned: {len(result1['books_mentioned'])}")
        print(f"✅ Books validated: {len(result1['validated_books'])}")

        if result1["validated_books"]:
            for book in result1["validated_books"]:
                print(
                    f"   📖 {book['title']} by {book.get('cached_contributors', 'Unknown')}"
                )

        # Follow-up question
        print("\n👤 User: Tell me more about The Name of the Wind")

        result2 = await processor.process_chat_message(
            phone, "Tell me more about The Name of the Wind"
        )

        print(f"\n🤖 Marty: {result2['response']}")
        print(f"📊 Tools used: {result2['tools_used']}")
        print(f"📚 Books mentioned: {len(result2['books_mentioned'])}")

        # Simulate Claude autonomous tool calling
        print("\n\n🧠 Claude Autonomous Tool Calling")
        print("=" * 50)

        claude_result = await processor.simulate_claude_tool_calling(
            phone, "Can you recommend a science fiction book?"
        )

        print(f"\n🤖 Claude's response: {claude_result['response']}")
        print(f"🔧 Tools used: {claude_result['tools_used']}")
        print(f"💭 Claude's reasoning: {claude_result['claude_reasoning']}")

        # Show conversation summary using tools
        print("\n\n📊 Conversation Summary via Tools")
        print("=" * 50)

        conv_tool = processor.registry.get_tool("conversation_manager")
        if conv_tool:
            summary_result = await conv_tool.execute(action="summary", phone=phone)

            if summary_result.success:
                summary = summary_result.data
                print(f"📋 Total messages: {summary['message_count']}")
                print(f"🆔 Conversation ID: {summary['conversation_id']}")
                print(f"⏰ Last activity: {summary['last_activity']}")
            else:
                print(f"❌ Failed to get summary: {summary_result.error}")

        # Tool registry statistics
        print("\n📈 Tool Registry Statistics:")
        print(f"   Available tools: {len(processor.available_tools)}")
        print(
            f"   Total tool calls: {result1['tool_registry_stats']['tools_called'] + result2['tool_registry_stats']['tools_called']}"
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Example failed: {e}")

    finally:
        await processor.close()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Run example
    asyncio.run(example_tool_calling_conversation())
