"""Tests for the multi-round tool loop.

The single-pass version passed tools on the final call, so the model answered
with another tool call, `.content` came back empty, and a fallback rebuilt the
prompt as bare system+user - discarding every tool result. Users saw Marty say
"lemme check" and stop.
"""

from unittest.mock import MagicMock

import pytest

from src.ai_client import MAX_TOOL_ROUNDS, generate_ai_response


def _tool_call(name: str, arguments: str = "{}", call_id: str = "call_1"):
    call = MagicMock()
    call.id = call_id
    call.function.name = name
    call.function.arguments = arguments
    return call


class TestToolLoop:
    @pytest.mark.asyncio
    async def test_answers_after_a_tool_call(self, mock_llm_api, llm_response):
        """The regression: tool call, then a real answer, not a fallback."""
        mock_llm_api.chat.completions.create.side_effect = [
            llm_response("lemme check", tool_calls=[_tool_call("get_doc")]),
            llm_response("returns are 7 days with a receipt"),
        ]

        text, executed = await generate_ai_response("whats ur return policy", [])

        assert text == "returns are 7 days with a receipt"
        assert [t["tool_name"] for t in executed] == ["get_doc"]
        assert mock_llm_api.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_chains_two_rounds_of_tools(self, mock_llm_api, llm_response):
        """The prompt's search-then-fetch flow needs more than one round."""
        mock_llm_api.chat.completions.create.side_effect = [
            llm_response("", tool_calls=[_tool_call("hardcover_api", call_id="a")]),
            llm_response("", tool_calls=[_tool_call("get_doc", call_id="b")]),
            llm_response("here you go"),
        ]

        text, executed = await generate_ai_response("tell me about a book", [])

        assert text == "here you go"
        assert [t["tool_name"] for t in executed] == ["hardcover_api", "get_doc"]

    @pytest.mark.asyncio
    async def test_forces_prose_when_rounds_run_out(self, mock_llm_api, llm_response):
        """A model that will not stop calling tools still has to answer."""
        mock_llm_api.chat.completions.create.side_effect = [
            llm_response("", tool_calls=[_tool_call("get_doc", call_id=str(i))])
            for i in range(MAX_TOOL_ROUNDS)
        ] + [llm_response("ok here is the answer")]

        text, _ = await generate_ai_response("hi", [])

        assert text == "ok here is the answer"
        assert mock_llm_api.chat.completions.create.call_count == MAX_TOOL_ROUNDS + 1

    @pytest.mark.asyncio
    async def test_final_call_withholds_tools(self, mock_llm_api, llm_response):
        """Tools are dropped on the forcing call so prose is the only option."""
        mock_llm_api.chat.completions.create.side_effect = [
            llm_response("", tool_calls=[_tool_call("get_doc", call_id=str(i))])
            for i in range(MAX_TOOL_ROUNDS)
        ] + [llm_response("fine, here")]

        await generate_ai_response("hi", [])

        last = mock_llm_api.chat.completions.create.call_args_list[-1]
        assert "tools" not in last[1]

    @pytest.mark.asyncio
    async def test_tool_results_stay_in_context(self, mock_llm_api, llm_response):
        """The old fallback threw tool output away; the answer must still see it."""
        mock_llm_api.chat.completions.create.side_effect = [
            llm_response("", tool_calls=[_tool_call("get_doc")]),
            llm_response("answer"),
        ]

        await generate_ai_response("whats ur return policy", [])

        second_call_messages = mock_llm_api.chat.completions.create.call_args_list[1][
            1
        ]["messages"]
        roles = [m["role"] for m in second_call_messages]
        assert "tool" in roles
        assert roles.count("system") == 1

    @pytest.mark.asyncio
    async def test_no_tool_call_returns_immediately(self, mock_llm_api, llm_response):
        mock_llm_api.chat.completions.create.side_effect = [llm_response("yo")]

        text, executed = await generate_ai_response("hi", [])

        assert (text, executed) == ("yo", [])
        assert mock_llm_api.chat.completions.create.call_count == 1
