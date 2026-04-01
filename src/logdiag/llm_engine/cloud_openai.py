"""Cloud LLM engine using OpenAI ChatGPT API."""

import json
import os
from typing import Any, Dict, List, Optional

import openai

from logdiag.llm_engine.base import BaseLLMEngine


def _convert_tools_to_openai_format(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert our tool definitions to OpenAI function-calling format."""
    openai_tools = []
    for tool in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        })
    return openai_tools


def _convert_messages_to_openai_format(
    messages: List[Dict[str, Any]],
    system_prompt: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convert conversation messages to OpenAI chat format."""
    openai_messages = []
    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})

    for msg in messages:
        role = msg["role"]

        if role == "assistant":
            entry: Dict[str, Any] = {"role": "assistant"}
            entry["content"] = msg.get("content") or None
            if msg.get("tool_calls"):
                entry["tool_calls"] = []
                for tc in msg["tool_calls"]:
                    entry["tool_calls"].append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                        },
                    })
            openai_messages.append(entry)

        elif role == "tool":
            openai_messages.append({
                "role": "tool",
                "tool_call_id": msg["tool_call_id"],
                "content": msg["content"],
            })

        elif role == "user":
            openai_messages.append({"role": "user", "content": msg["content"]})

    return openai_messages


class CloudOpenAIEngine(BaseLLMEngine):
    """OpenAI ChatGPT API backend."""

    def __init__(self, api_key: str = "", model: str = "gpt-4o",
                 max_tokens: int = 4096, **kwargs):
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "OpenAI API key not provided. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )
        self._client = openai.OpenAI(api_key=resolved_key)
        self._model = model
        self._max_tokens = max_tokens

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        openai_messages = _convert_messages_to_openai_format(messages, system_prompt)

        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": openai_messages,
            "max_tokens": self._max_tokens,
        }
        if tools:
            kwargs["tools"] = _convert_tools_to_openai_format(tools)

        response = self._client.chat.completions.create(**kwargs)
        return self._normalize_response(response)

    @staticmethod
    def _normalize_response(response) -> Dict[str, Any]:
        """Convert OpenAI response to our normalized format."""
        choice = response.choices[0]
        message = choice.message

        content_text = message.content
        tool_calls = None

        if message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                arguments = tc.function.arguments
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": arguments,
                })

        return {
            "role": "assistant",
            "content": content_text,
            "tool_calls": tool_calls,
        }
