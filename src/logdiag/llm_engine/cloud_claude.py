"""Cloud LLM engine using Anthropic Claude API."""

import json
import os
from typing import Any, Dict, List, Optional

import anthropic

from logdiag.llm_engine.base import BaseLLMEngine


def _convert_tools_to_claude_format(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert our tool definitions to Anthropic Claude tool format."""
    claude_tools = []
    for tool in tools:
        claude_tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": tool["input_schema"],
        })
    return claude_tools


def _convert_messages_to_claude_format(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert conversation messages to Anthropic Claude format.

    Claude API uses a different structure for tool calls and tool results
    compared to OpenAI-style messages.
    """
    claude_messages = []
    for msg in messages:
        role = msg["role"]

        if role == "assistant":
            content_blocks = []
            if msg.get("content"):
                content_blocks.append({"type": "text", "text": msg["content"]})
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["arguments"],
                    })
            claude_messages.append({"role": "assistant", "content": content_blocks})

        elif role == "tool":
            claude_messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg["tool_call_id"],
                    "content": msg["content"],
                }],
            })

        elif role == "user":
            claude_messages.append({"role": "user", "content": msg["content"]})

    return claude_messages


class CloudClaudeEngine(BaseLLMEngine):
    """Anthropic Claude API backend."""

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514",
                 max_tokens: int = 4096, **kwargs):
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "Anthropic API key not provided. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )
        self._client = anthropic.Anthropic(api_key=resolved_key)
        self._model = model
        self._max_tokens = max_tokens

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": _convert_messages_to_claude_format(messages),
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = _convert_tools_to_claude_format(tools)

        response = self._client.messages.create(**kwargs)
        return self._normalize_response(response)

    @staticmethod
    def _normalize_response(response) -> Dict[str, Any]:
        """Convert Anthropic response to our normalized format."""
        content_text = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content_text = block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input if isinstance(block.input, dict)
                    else json.loads(block.input),
                })

        return {
            "role": "assistant",
            "content": content_text,
            "tool_calls": tool_calls if tool_calls else None,
        }
