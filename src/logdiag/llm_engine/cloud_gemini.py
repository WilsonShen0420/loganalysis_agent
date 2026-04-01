"""Cloud LLM engine using Google Gemini API."""

import json
import os
import uuid
from typing import Any, Dict, List, Optional

import requests

from logdiag.llm_engine.base import BaseLLMEngine

# Gemini API endpoint
_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _convert_tools_to_gemini_format(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert our tool definitions to Gemini function declaration format."""
    function_declarations = []
    for tool in tools:
        # Gemini uses "parameters" not "input_schema", and requires OpenAPI-style schema
        params = dict(tool["input_schema"])
        # Remove "required" from inside properties if present; keep at top level
        function_declarations.append({
            "name": tool["name"],
            "description": tool["description"],
            "parameters": params,
        })
    return [{"function_declarations": function_declarations}]


def _convert_messages_to_gemini_format(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert conversation messages to Gemini contents format."""
    contents = []
    for msg in messages:
        role = msg["role"]

        if role == "user":
            contents.append({
                "role": "user",
                "parts": [{"text": msg["content"]}],
            })

        elif role == "assistant":
            parts = []
            if msg.get("content"):
                parts.append({"text": msg["content"]})
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    parts.append({
                        "functionCall": {
                            "name": tc["name"],
                            "args": tc["arguments"],
                        }
                    })
            contents.append({"role": "model", "parts": parts})

        elif role == "tool":
            contents.append({
                "role": "user",
                "parts": [{
                    "functionResponse": {
                        "name": msg.get("tool_name", "query_parser_log"),
                        "response": {"result": msg["content"]},
                    }
                }],
            })

    return contents


class CloudGeminiEngine(BaseLLMEngine):
    """Google Gemini API backend."""

    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash",
                 max_tokens: int = 4096, **kwargs):
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        if not self._api_key:
            raise ValueError(
                "Google API key not provided. "
                "Set GOOGLE_API_KEY environment variable or pass api_key parameter."
            )
        self._model = model
        self._max_tokens = max_tokens

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = (
            f"{_GEMINI_API_BASE}/{self._model}:generateContent"
            f"?key={self._api_key}"
        )

        payload: Dict[str, Any] = {
            "contents": _convert_messages_to_gemini_format(messages),
            "generationConfig": {
                "maxOutputTokens": self._max_tokens,
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        if tools:
            payload["tools"] = _convert_tools_to_gemini_format(tools)

        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        return self._normalize_response(data)

    @staticmethod
    def _normalize_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Gemini response to our normalized format."""
        candidates = data.get("candidates", [])
        if not candidates:
            return {"role": "assistant", "content": "No response from Gemini.", "tool_calls": None}

        parts = candidates[0].get("content", {}).get("parts", [])

        content_text = None
        tool_calls = []

        for part in parts:
            if "text" in part:
                content_text = part["text"]
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append({
                    "id": str(uuid.uuid4()),
                    "name": fc.get("name", ""),
                    "arguments": fc.get("args", {}),
                })

        return {
            "role": "assistant",
            "content": content_text,
            "tool_calls": tool_calls if tool_calls else None,
        }
