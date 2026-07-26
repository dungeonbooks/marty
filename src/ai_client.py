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


def _build_system_prompt(docs_index: str) -> str:
    """Compose the system prompt from bytes that are stable across customers.

    Nothing per-request belongs here. Neuralwatt caches on the literal token
    prefix, so a customer name or a clock reading in the system message changes
    the prefix and cold-prefills the system prompt, the tool definitions, and
    the entire conversation history on every single call.

    Not immutable: `docs_index` rotates on its 15-minute TTL and when the docs
    repo changes. That invalidates the cached prefix for everyone at once,
    which is the point - it stays shared rather than fragmenting per customer.
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

    return "\n\n".join(parts)


def _format_request_context(customer_context: dict | None) -> str:
    """Render per-request context to ride along with the current user turn.

    This sits at the tail of the prompt, after the history, so everything
    before it stays a stable growing prefix that caches turn over turn.
    """
    if not customer_context:
        return ""

    sections = []

    context_info = []
    if customer_context.get("name"):
        context_info.append(f"Customer name: {customer_context['name']}")
    if customer_context.get("phone"):
        context_info.append(f"Phone: {customer_context['phone']}")
    if customer_context.get("customer_id"):
        context_info.append(f"Customer ID: {customer_context['customer_id']}")
    if context_info:
        sections.append("Customer Context:\n" + " | ".join(context_info))

    time_context = []
    if customer_context.get("current_time"):
        time_context.append(f"Current time: {customer_context['current_time']}")
    if customer_context.get("current_date"):
        time_context.append(f"Current date: {customer_context['current_date']}")
    if customer_context.get("current_day"):
        time_context.append(f"Day of week: {customer_context['current_day']}")
    if time_context:
        sections.append("Current Time & Date:\n" + " | ".join(time_context))

    return "\n\n".join(sections)


def _compose_user_turn(user_message: str, request_context: str) -> str:
    """Attach per-request context to the user's message."""
    if not request_context:
        return user_message
    return f"{request_context}\n\n---\n\n{user_message}"


# Prior messages, not exchanges: 4 means two completed user/assistant rounds,
# so rename_thread first becomes available on the third user turn.
RENAME_THREAD_MIN_HISTORY = 4


def _tools_to_withhold(conversation_history: list[ConversationMessage]) -> set[str]:
    """Tools that should not be offered yet, given how far the conversation has got.

    `rename_thread` is the case that matters. The prompt says to use it "if chat
    gets long enough", but on a first message GLM-5.2-short-fast called it on
    every one of three trials, once inventing a `thread_name` function that does
    not exist. There is no topic to name yet, so withhold it outright.
    """
    if len(conversation_history) < RENAME_THREAD_MIN_HISTORY:
        return {"rename_thread"}
    return set()


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


# Fields Hardcover returns that the model has no use for. `editions` alone is
# ~15k characters per book (every ISBN, printing and format), and a five-result
# search came to 108,799 characters - roughly 27k tokens billed as input, on
# every search. The embed builder and the enricher still read these off
# `result.data`; only the model's view is trimmed.
_BULK_TOOL_RESULT_KEYS = frozenset(
    {"editions", "cached_tags", "cached_contributors", "contributions"}
)

# A blurb is for pitching one book, not reproducing the jacket copy.
_MAX_TEXT_FIELD_CHARS = 400

# Overall budget for one tool result. Ten trending books still came to 16k
# characters after dropping bulk keys, because descriptions dominate.
_MAX_TOOL_RESULT_CHARS = 6000


def _strip_bulk_fields(value):
    """Recursively drop bulk keys and clip long prose the model never needs in full."""
    if isinstance(value, dict):
        return {
            k: _strip_bulk_fields(v)
            for k, v in value.items()
            if k not in _BULK_TOOL_RESULT_KEYS
        }
    if isinstance(value, list):
        return [_strip_bulk_fields(v) for v in value]
    if isinstance(value, str) and len(value) > _MAX_TEXT_FIELD_CHARS:
        return value[:_MAX_TEXT_FIELD_CHARS].rstrip() + "..."
    return value


def _render_tool_result(data) -> str:
    """Render a tool result for the model within a fixed character budget.

    A list of results is trimmed by dropping whole trailing entries, so the
    model never receives a record cut off mid-structure. The first entry is
    always kept so a result is never empty, which means it can overflow the
    budget on its own; that case falls through to the character truncation
    below rather than returning over budget.
    """
    trimmed = _strip_bulk_fields(data)

    note = ""
    if isinstance(trimmed, list):
        kept: list = []
        for item in trimmed:
            candidate = kept + [item]
            if kept and len(str(candidate)) > _MAX_TOOL_RESULT_CHARS:
                break
            kept = candidate
        if len(kept) < len(trimmed):
            note = f"\n\n[showing {len(kept)} of {len(trimmed)} results]"
        trimmed = kept

    rendered = str(trimmed)
    if len(rendered) > _MAX_TOOL_RESULT_CHARS:
        rendered = (
            rendered[:_MAX_TOOL_RESULT_CHARS]
            + f"\n\n[truncated - {len(rendered)} chars total]"
        )
    return rendered + note


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


# The prompt describes a two-step flow (search, then fetch the one book worth
# showing), so one round was never enough. Three leaves headroom without letting
# a confused model spend the budget on tool calls.
MAX_TOOL_ROUNDS = 3


def _assistant_turn(assistant_msg, tool_calls) -> dict:
    """Echo the model's own tool-call turn back so results have something to attach to."""
    return {
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


async def _dispatch_tool_call(tc, offered: set[str], executed: list[dict]) -> dict:
    """Run one tool call and return the tool message to feed back."""

    def message(content: str) -> dict:
        return {
            "role": "tool",
            "tool_call_id": tc.id,
            "name": tc.function.name,
            "content": content,
        }

    tool_name = tc.function.name

    # Withholding a tool from the schema is a hint, not a guarantee - the model
    # can still name one. Dispatch against what was offered for this request.
    if tool_name not in offered:
        logger.warning(
            "tool_call_not_offered",
            tool=tool_name,
            detail="model called a tool that was withheld or does not exist",
        )
        return message(f"Error: {tool_name} is not available right now")

    try:
        tool_input = json.loads(tc.function.arguments) if tc.function.arguments else {}
    except json.JSONDecodeError:
        logger.warning(f"Bad tool arguments JSON for {tool_name}")
        tool_input = {}

    tool = tool_registry.get_tool(tool_name)
    if tool is None:
        logger.warning(f"Tool {tool_name} not in registry")
        return message(f"Error: tool {tool_name} not registered")

    try:
        result = await tool.execute(**tool_input)
    except Exception as e:
        logger.error(f"Tool execution error for {tool_name}: {e}")
        return message(f"Error executing tool: {e}")

    logger.info(
        f"tool_call name={tool_name} success={result.success} error={result.error}"
    )
    _log_hardcover_detail(tool_name, tool_input, result.data, result.success)
    executed.append(
        {"tool_name": tool_name, "tool_input": tool_input, "result": result}
    )

    return message(
        _render_tool_result(result.data) if result.success else f"Error: {result.error}"
    )


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
        system_prompt = _build_system_prompt(docs_index)
        user_turn = _compose_user_turn(
            user_message, _format_request_context(customer_context)
        )

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_turn})

        tools = tool_registry.get_openai_tools(
            exclude=_tools_to_withhold(conversation_history)
        )
        offered = {t["function"]["name"] for t in tools}
        executed_tools: list[dict] = []

        rounds_used = 0
        for round_index in range(MAX_TOOL_ROUNDS):
            rounds_used = round_index + 1
            logger.debug(f"LLM round {round_index + 1} with {len(messages)} messages")
            response = await _complete(messages, tools=tools)
            assistant_msg = response.choices[0].message
            tool_calls = assistant_msg.tool_calls or []

            if not tool_calls:
                text = (assistant_msg.content or "").strip()
                if text:
                    return text, executed_tools
                break

            messages.append(_assistant_turn(assistant_msg, tool_calls))
            for tc in tool_calls:
                messages.append(await _dispatch_tool_call(tc, offered, executed_tools))

        # Either the model kept reaching for tools, or it answered with nothing.
        # Drop the tools so prose is the only legal output and it has to commit.
        logger.info(
            "tool_loop_forcing_answer", rounds=rounds_used, max_rounds=MAX_TOOL_ROUNDS
        )
        final = await _complete(messages)
        text = (final.choices[0].message.content or "").strip()
        return text or "I'm having trouble generating a response right now.", (
            executed_tools
        )

    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return "sorry, brain's lagging. can you try again?", []
