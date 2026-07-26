"""Generate Marty responses against GLM via Neuralwatt (OpenAI-compatible)."""

import json
from datetime import datetime
from pathlib import Path

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel

from .config import config
from .tools import tool_registry

logger = structlog.get_logger(__name__)


def get_llm_client() -> AsyncOpenAI:
    """Get or create the Neuralwatt (OpenAI-compatible) client."""
    if not config.NEURALWATT_API_KEY:
        logger.warning(
            "neuralwatt_api_key_missing",
            detail="NEURALWATT_API_KEY is unset; LLM calls will fail",
        )
    return AsyncOpenAI(
        api_key=config.llm_api_key(),
        base_url=config.NEURALWATT_BASE_URL,
    )


client = get_llm_client()


class ConversationMessage(BaseModel):
    """A message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


def load_system_prompt() -> str:
    """Load the system prompt from the prompts directory."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "marty_system_prompt.md"
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        logger.warning(f"Prompt file {prompt_path} not found. Using fallback prompt.")
        return (
            "You are Marty, a helpful AI assistant who works at Dungeon Books. "
            "Help customers find great books!"
        )


MARTY_SYSTEM_PROMPT = load_system_prompt()


def _build_system_prompt(customer_context: dict | None, docs_index: str) -> str:
    """Compose the system prompt: stable persona, then docs index, then per-request context.

    Stable bytes go first so Neuralwatt's prefix cache hits across requests.
    Variable per-request bytes (customer name, time) go last.
    """
    parts = [MARTY_SYSTEM_PROMPT]

    if docs_index:
        parts.append(
            "## Operational documentation\n\n"
            "Use the `get_doc` tool with one of the slugs below to fetch the "
            "full file before answering customer questions about policies, "
            "hours, store info, returns, events, or orders. Each fetched "
            "doc returns a body plus `agent_guidance` directives - follow "
            "those directives when crafting the reply.\n\n"
            f"{docs_index}"
        )

    if customer_context:
        context_info = []
        if customer_context.get("name"):
            context_info.append(f"Customer name: {customer_context['name']}")
        if customer_context.get("phone"):
            context_info.append(f"Phone: {customer_context['phone']}")
        if customer_context.get("customer_id"):
            context_info.append(f"Customer ID: {customer_context['customer_id']}")
        if context_info:
            parts.append("Customer Context:\n" + " | ".join(context_info))

        time_context = []
        if customer_context.get("current_time"):
            time_context.append(f"Current time: {customer_context['current_time']}")
        if customer_context.get("current_date"):
            time_context.append(f"Current date: {customer_context['current_date']}")
        if customer_context.get("current_day"):
            time_context.append(f"Day of week: {customer_context['current_day']}")
        if time_context:
            parts.append("Current Time & Date:\n" + " | ".join(time_context))

    return "\n\n".join(parts)


async def _fetch_docs_index() -> str:
    try:
        from src.tools.docs.fetcher import fetch_index, format_index_for_prompt

        payload = await fetch_index()
        return format_index_for_prompt(payload)
    except Exception as e:
        logger.warning(f"docs index fetch failed, continuing without it: {e}")
        return ""


def _log_usage(response) -> None:
    """Log token, cache, and energy accounting from a Neuralwatt response."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return

    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) if details else None
    cost = getattr(response, "cost", None) or {}
    energy = getattr(response, "energy", None) or {}

    logger.info(
        "llm_usage",
        model=getattr(response, "model", None),
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
        cached_tokens=cached,
        request_cost_usd=cost.get("request_cost_usd")
        if isinstance(cost, dict)
        else None,
        energy_joules=energy.get("energy_joules") if isinstance(energy, dict) else None,
    )


def _log_hardcover_detail(
    tool_name: str, tool_input: dict, result_data, success: bool
) -> None:
    if tool_name != "hardcover_api" or not success:
        return
    action = tool_input.get("action", "unknown")
    query = tool_input.get("query", "")

    if isinstance(result_data, list):
        books_info = []
        for book in result_data:
            if isinstance(book, dict):
                title = book.get("title", "Unknown")
                author = book.get("author", "Unknown")
                year = book.get("release_year", "Unknown")
                books_info.append(f"{title} by {author} ({year})")
        logger.info(f"Hardcover {action} '{query}' returned: {'; '.join(books_info)}")
        return

    if isinstance(result_data, dict):
        if action == "get_trending_books" and "books" in result_data:
            books = result_data.get("books", [])
            books_info = []
            for book in books:
                if isinstance(book, dict):
                    title = book.get("title", "Unknown")
                    author = book.get("author", "Unknown")
                    year = book.get("release_year", "Unknown")
                    books_info.append(f"{title} by {author} ({year})")
            logger.info(
                f"Hardcover {action} returned: "
                f"{'; '.join(books_info) if books_info else 'No books found'}"
            )
        else:
            book = result_data
            title = book.get("title", "Unknown")
            author = book.get("author", "Unknown")
            year = book.get("release_year", "Unknown")
            logger.info(f"Hardcover {action} returned: {title} by {author} ({year})")


async def _complete(messages: list[dict], tools: list[dict] | None = None):
    """Issue one chat completion with Marty's standard parameters."""
    kwargs: dict = {
        "model": config.MARTY_MODEL,
        "max_tokens": config.MARTY_MAX_TOKENS,
        "temperature": config.MARTY_TEMPERATURE,
        "messages": messages,
        "reasoning_effort": config.MARTY_CHAT_REASONING_EFFORT,
    }
    if tools:
        kwargs["tools"] = tools

    response = await client.chat.completions.create(**kwargs)
    _log_usage(response)
    return response


async def generate_ai_response(
    user_message: str,
    conversation_history: list[ConversationMessage],
    customer_context: dict | None = None,
) -> tuple[str, list[dict]]:
    """Generate a Marty response, executing tool calls as needed.

    Args:
        user_message: The current message from the user
        conversation_history: Previous messages in the conversation
        customer_context: Optional context about the customer

    Returns:
        Tuple of (AI-generated response, list of executed tool records)
    """
    try:
        docs_index = await _fetch_docs_index()
        system_prompt = _build_system_prompt(customer_context, docs_index)

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})

        tools = tool_registry.get_openai_tools()

        logger.debug(f"Calling LLM with {len(messages)} messages")
        response = await _complete(messages, tools=tools)

        assistant_msg = response.choices[0].message
        tool_calls = assistant_msg.tool_calls or []

        if not tool_calls:
            text = (assistant_msg.content or "").strip()
            return text or "I'm having trouble generating a response right now.", []

        # Echo the assistant's tool-call turn back before submitting results
        messages.append(
            {
                "role": "assistant",
                "content": assistant_msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        executed_tools: list[dict] = []
        for tc in tool_calls:
            tool_name = tc.function.name
            try:
                tool_input = (
                    json.loads(tc.function.arguments) if tc.function.arguments else {}
                )
            except json.JSONDecodeError:
                logger.warning(f"Bad tool arguments JSON for {tool_name}")
                tool_input = {}

            tool = tool_registry.get_tool(tool_name)
            if tool is None:
                logger.warning(f"Tool {tool_name} not in registry")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tool_name,
                        "content": f"Error: tool {tool_name} not registered",
                    }
                )
                continue

            try:
                result = await tool.execute(**tool_input)
                logger.info(
                    f"tool_call name={tool_name} "
                    f"success={result.success} error={result.error}"
                )
                _log_hardcover_detail(
                    tool_name, tool_input, result.data, result.success
                )

                content = (
                    str(result.data) if result.success else f"Error: {result.error}"
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tool_name,
                        "content": content,
                    }
                )
                executed_tools.append(
                    {
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "result": result,
                    }
                )
            except Exception as e:
                logger.error(f"Tool execution error for {tool_name}: {e}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tool_name,
                        "content": f"Error executing tool: {e}",
                    }
                )

        final_response = await _complete(messages, tools=tools)
        text = (final_response.choices[0].message.content or "").strip()
        if text:
            return text, executed_tools

        # Final turn came back empty: retry without the tool history
        logger.debug("Final response empty, attempting fallback without tool history")
        fallback = await _complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            tools=tools,
        )
        text = (fallback.choices[0].message.content or "").strip()
        return text or "I'm having trouble generating a response right now.", (
            executed_tools
        )

    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return "sorry, brain's lagging. can you try again?", []
