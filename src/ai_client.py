import os
from datetime import datetime
from pathlib import Path

import structlog
from anthropic import AsyncAnthropic
from pydantic import BaseModel

from .tools import tool_registry

# Configure logging
logger = structlog.get_logger(__name__)


# Initialize the Claude client
def get_claude_client() -> AsyncAnthropic:
    """Get or create Claude client."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return AsyncAnthropic(api_key=api_key)


# Create client instance
client = get_claude_client()


class ConversationMessage(BaseModel):
    """A message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


def load_system_prompt(prompt_file: str | Path | None = None) -> str:
    """Load the system prompt from the prompts directory, robust to invocation context."""
    if prompt_file is None:
        prompt_path = (
            Path(__file__).parent.parent / "prompts" / "marty_system_prompt.md"
        )
    else:
        prompt_path = Path(prompt_file)

    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.warning(f"Prompt file {prompt_path} not found. Using fallback prompt.")
        return "You are Marty, a helpful AI assistant who works at Dungeon Books. Help customers find great books!"


# Load Marty's character prompt from file
MARTY_SYSTEM_PROMPT = load_system_prompt()


async def generate_ai_response(
    user_message: str,
    conversation_history: list[ConversationMessage],
    customer_context: dict | None = None,
    platform: str = "sms",
) -> tuple[str, list[dict]]:
    """
    Generate an AI response using Claude.

    Args:
        user_message: The current message from the user
        conversation_history: Previous messages in the conversation
        customer_context: Optional context about the customer

    Returns:
        Tuple of (AI-generated response, list of tool results)
    """
    try:
        # Build the conversation history for Claude
        messages = []

        # Add conversation history
        for msg in conversation_history:
            messages.append({"role": msg.role, "content": msg.content})

        # Add the current user message
        messages.append({"role": "user", "content": user_message})

        # Load platform-specific system prompt
        if platform == "discord":
            system_prompt = load_system_prompt(
                Path(__file__).parent.parent
                / "prompts"
                / "marty_discord_system_prompt.md"
            )
            logger.debug(f"Loaded Discord system prompt, length: {len(system_prompt)}")
        else:
            system_prompt = MARTY_SYSTEM_PROMPT
            logger.debug(f"Loaded SMS system prompt, length: {len(system_prompt)}")
        if customer_context:
            context_info = []

            # Use name field - let Claude handle cultural sensitivity
            if customer_context.get("name"):
                context_info.append(f"Customer name: {customer_context['name']}")

            if customer_context.get("phone"):
                context_info.append(f"Phone: {customer_context['phone']}")
            if customer_context.get("customer_id"):
                context_info.append(f"Customer ID: {customer_context['customer_id']}")

            if context_info:
                system_prompt += f"\n\nCustomer Context:\n{' | '.join(context_info)}"

            # Add current date/time context
            time_context = []
            if customer_context.get("current_time"):
                time_context.append(f"Current time: {customer_context['current_time']}")
            if customer_context.get("current_date"):
                time_context.append(f"Current date: {customer_context['current_date']}")
            if customer_context.get("current_day"):
                time_context.append(f"Day of week: {customer_context['current_day']}")

            if time_context:
                system_prompt += f"\n\nCurrent Time & Date:\n{' | '.join(time_context)}"

        # Generate response with Claude including tools
        logger.debug(f"Calling Claude API with {len(messages)} messages")
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            temperature=0.7,
            system=system_prompt,
            messages=messages,
            tools=tool_registry.get_claude_tools(),
        )
        logger.debug(f"Claude API response received: {type(response)}")

        # Handle tool use and generate final response
        if response.content:
            logger.debug(f"Response content type: {type(response.content)}")
            logger.debug(f"Response content length: {len(response.content)}")

            tool_results = []
            executed_tools = []  # Track tool executions for return
            messages.append({"role": "assistant", "content": response.content})

            # Execute any tool calls
            for content_block in response.content:
                logger.debug(f"Content block type: {type(content_block)}")
                if hasattr(content_block, "type") and content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_use_id = content_block.id

                    # Execute the tool
                    tool = tool_registry.get_tool(tool_name)
                    if tool:
                        try:
                            result = await tool.execute(**tool_input)

                            # Log Hardcover API response details
                            if tool_name == "hardcover_api" and result.success:
                                action = tool_input.get("action", "unknown")
                                query = tool_input.get("query", "")

                                if isinstance(result.data, list):
                                    books_info = []
                                    for book in result.data:
                                        if isinstance(book, dict):
                                            title = book.get("title", "Unknown")
                                            author = book.get("author", "Unknown")
                                            year = book.get("release_year", "Unknown")
                                            books_info.append(
                                                f"{title} by {author} ({year})"
                                            )
                                    logger.info(
                                        f"Hardcover {action} '{query}' returned: {'; '.join(books_info)}"
                                    )

                                elif isinstance(result.data, dict):
                                    # Handle trending books response which has books list nested inside
                                    if (
                                        action == "get_trending_books"
                                        and "books" in result.data
                                    ):
                                        books = result.data.get("books", [])
                                        books_info = []
                                        for book in books:
                                            if isinstance(book, dict):
                                                title = book.get("title", "Unknown")
                                                author = book.get("author", "Unknown")
                                                year = book.get(
                                                    "release_year", "Unknown"
                                                )
                                                books_info.append(
                                                    f"{title} by {author} ({year})"
                                                )
                                        logger.info(
                                            f"Hardcover {action} returned: {'; '.join(books_info) if books_info else 'No books found'}"
                                        )
                                    else:
                                        # Handle single book response
                                        book = result.data
                                        title = book.get("title", "Unknown")
                                        author = book.get("author", "Unknown")
                                        year = book.get("release_year", "Unknown")
                                        logger.info(
                                            f"Hardcover {action} returned: {title} by {author} ({year})"
                                        )

                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": str(result.data)
                                    if result.success
                                    else f"Error: {result.error}",
                                }
                            )
                            # Track executed tool for return
                            executed_tools.append(
                                {
                                    "tool_name": tool_name,
                                    "tool_input": tool_input,
                                    "result": result,
                                }
                            )
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": f"Error executing tool: {str(e)}",
                                }
                            )

            # If tools were used, get final response
            if tool_results:
                # Format tool results properly for Claude
                tool_results_content = []
                for result in tool_results:
                    tool_results_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": result["tool_use_id"],
                            "content": result["content"],
                        }
                    )

                messages.append({"role": "user", "content": tool_results_content})
                logger.debug(
                    f"Added tool results to messages: {len(tool_results)} results"
                )

                final_response = await client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=500,
                    temperature=0.7,
                    system=system_prompt,
                    messages=messages,
                )
                logger.debug(f"Final response received: {type(final_response)}")

                if final_response.content and len(final_response.content) > 0:
                    content_block = final_response.content[0]
                    logger.debug(f"Final content block type: {type(content_block)}")

                    # Try different ways to extract text
                    if hasattr(content_block, "text"):
                        response_text = content_block.text
                    elif hasattr(content_block, "content"):
                        response_text = content_block.content
                    else:
                        response_text = str(content_block)

                    logger.debug(f"Final response text: {response_text[:100]}...")
                    return response_text, executed_tools
                else:
                    logger.warning(
                        "Final response has no content, checking initial response for text"
                    )

                    # Check if the initial response had any text content alongside tool calls
                    initial_text = ""
                    for content_block in response.content:
                        if (
                            hasattr(content_block, "type")
                            and content_block.type == "text"
                        ):
                            if hasattr(content_block, "text"):
                                initial_text += content_block.text

                    if initial_text.strip():
                        logger.debug(
                            f"Using text from initial response: {initial_text[:100]}..."
                        )
                        return initial_text.strip(), executed_tools

                    # Fallback: try to generate a response without tools
                    logger.debug("Attempting fallback response without tools")
                    fallback_response = await client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=500,
                        temperature=0.7,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_message}],
                    )

                    if fallback_response.content and len(fallback_response.content) > 0:
                        content_block = fallback_response.content[0]
                        if hasattr(content_block, "text"):
                            response_text = content_block.text
                        else:
                            response_text = str(content_block)
                    else:
                        response_text = (
                            "I'm having trouble generating a response right now."
                        )
                    return response_text, executed_tools
            else:
                # No tools used, extract text directly
                logger.debug("No tools used, extracting text directly")
                if len(response.content) > 0:
                    content_block = response.content[0]
                    logger.debug(f"Content block type: {type(content_block)}")
                    logger.debug(f"Content block attributes: {dir(content_block)}")

                    # Try different ways to extract text
                    if hasattr(content_block, "text"):
                        response_text = content_block.text
                    elif hasattr(content_block, "content"):
                        response_text = content_block.content
                    else:
                        response_text = str(content_block)

                    logger.debug(f"Extracted response text: {response_text[:100]}...")
                else:
                    logger.error("Response has no content blocks")
                    response_text = (
                        "I'm having trouble generating a response right now."
                    )
                return response_text, []
        else:
            logger.error("Response has no content")
            response_text = "I'm having trouble generating a response right now."

        return response_text, []

    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return "Sorry, I'm having trouble thinking right now. Can you try again? 🤔", []
