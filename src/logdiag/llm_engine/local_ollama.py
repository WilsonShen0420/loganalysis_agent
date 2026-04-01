"""Local LLM engine using Ollama HTTP API."""

import json
import os
import uuid
from typing import Any, Dict, List, Optional

import requests

from logdiag.llm_engine.base import BaseLLMEngine


def _convert_tools_to_ollama_format(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert our tool definitions to Ollama tool-use format."""
    ollama_tools = []
    for tool in tools:
        ollama_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        })
    return ollama_tools


def _convert_messages_to_ollama_format(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert conversation messages to Ollama chat format."""
    ollama_messages = []
    for msg in messages:
        role = msg["role"]

        if role == "assistant":
            entry: Dict[str, Any] = {"role": "assistant", "content": msg.get("content") or ""}
            if msg.get("tool_calls"):
                entry["tool_calls"] = []
                for tc in msg["tool_calls"]:
                    entry["tool_calls"].append({
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    })
            ollama_messages.append(entry)

        elif role == "tool":
            ollama_messages.append({
                "role": "tool",
                "content": msg["content"],
            })

        elif role == "user":
            ollama_messages.append({"role": "user", "content": msg["content"]})

        elif role == "system":
            ollama_messages.append({"role": "system", "content": msg["content"]})

    return ollama_messages


class LocalOllamaEngine(BaseLLMEngine):
    """Ollama local LLM backend (e.g., Qwen2.5-7B-Instruct)."""

    def __init__(self, base_url: str = "", model: str = "qwen2.5:7b-instruct",
                 max_tokens: int = 4096, **kwargs):
        self._base_url = (
            base_url
            or os.environ.get("OLLAMA_HOST", "")
            or "http://localhost:11434"
        )
        self._model = model
        self._max_tokens = max_tokens

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        ollama_messages.extend(_convert_messages_to_ollama_format(messages))

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": self._max_tokens,
            },
        }
        if tools:
            payload["tools"] = _convert_tools_to_ollama_format(tools)

        url = f"{self._base_url}/api/chat"
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        return self._normalize_response(data)

    @staticmethod
    def _normalize_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Ollama response to our normalized format."""
        message = data.get("message", {})
        content_text = message.get("content") or None
        tool_calls = None

        raw_tool_calls = message.get("tool_calls")
        if raw_tool_calls:
            tool_calls = []
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                arguments = func.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                tool_calls.append({
                    "id": str(uuid.uuid4()),
                    "name": func.get("name", ""),
                    "arguments": arguments,
                })

        return {
            "role": "assistant",
            "content": content_text,
            "tool_calls": tool_calls,
        }
