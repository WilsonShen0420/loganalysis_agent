"""Tests for LLM engine factory and message format conversion."""

import json
import pytest

from logdiag.llm_engine import create_engine, _ENGINE_MAP
from logdiag.llm_engine.cloud_claude import (
    _convert_messages_to_claude_format,
    _convert_tools_to_claude_format,
)
from logdiag.llm_engine.cloud_openai import (
    _convert_messages_to_openai_format,
    _convert_tools_to_openai_format,
)
from logdiag.llm_engine.cloud_gemini import (
    _convert_messages_to_gemini_format,
    _convert_tools_to_gemini_format,
    CloudGeminiEngine,
)
from logdiag.llm_engine.local_ollama import (
    _convert_messages_to_ollama_format,
    _convert_tools_to_ollama_format,
    LocalOllamaEngine,
)


# ---- Shared fixtures ----

SAMPLE_TOOLS = [
    {
        "name": "query_parser_log",
        "description": "查詢 log",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_range": {"type": "string"},
                "filter": {"type": "string"},
            },
            "required": ["time_range"],
        },
    }
]

SAMPLE_MESSAGES = [
    {"role": "user", "content": "幫我看 SLAM log"},
    {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "tc_001",
            "name": "query_parser_log",
            "arguments": {"time_range": "2026/03/31", "filter": "slam"},
        }],
    },
    {
        "role": "tool",
        "tool_call_id": "tc_001",
        "tool_name": "query_parser_log",
        "content": "2026/03/31:100000:000 - slam:slam_start_request",
    },
    {
        "role": "assistant",
        "content": "SLAM 啟動正常。",
        "tool_calls": None,
    },
]


# ---- Factory tests ----

def test_factory_supported_backends():
    assert "claude" in _ENGINE_MAP
    assert "openai" in _ENGINE_MAP
    assert "gemini" in _ENGINE_MAP
    assert "local" in _ENGINE_MAP


def test_factory_unknown_backend():
    with pytest.raises(ValueError, match="Unknown LLM backend"):
        create_engine("nonexistent")


# ---- Claude format conversion ----

def test_claude_tool_format():
    result = _convert_tools_to_claude_format(SAMPLE_TOOLS)
    assert len(result) == 1
    assert result[0]["name"] == "query_parser_log"
    assert "input_schema" in result[0]


def test_claude_message_format():
    result = _convert_messages_to_claude_format(SAMPLE_MESSAGES)
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
    # tool_use block
    assert result[1]["content"][0]["type"] == "tool_use"
    # tool_result
    assert result[2]["role"] == "user"
    assert result[2]["content"][0]["type"] == "tool_result"
    # final text
    assert result[3]["role"] == "assistant"


# ---- OpenAI format conversion ----

def test_openai_tool_format():
    result = _convert_tools_to_openai_format(SAMPLE_TOOLS)
    assert len(result) == 1
    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "query_parser_log"
    assert "parameters" in result[0]["function"]


def test_openai_message_format():
    result = _convert_messages_to_openai_format(SAMPLE_MESSAGES, system_prompt="你是助手")
    # system prompt is first
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "你是助手"
    # user
    assert result[1]["role"] == "user"
    # assistant with tool_calls
    assert result[2]["role"] == "assistant"
    assert len(result[2]["tool_calls"]) == 1
    assert result[2]["tool_calls"][0]["id"] == "tc_001"
    # tool result
    assert result[3]["role"] == "tool"
    assert result[3]["tool_call_id"] == "tc_001"


# ---- Gemini format conversion ----

def test_gemini_tool_format():
    result = _convert_tools_to_gemini_format(SAMPLE_TOOLS)
    assert len(result) == 1
    decls = result[0]["function_declarations"]
    assert len(decls) == 1
    assert decls[0]["name"] == "query_parser_log"


def test_gemini_message_format():
    result = _convert_messages_to_gemini_format(SAMPLE_MESSAGES)
    # user
    assert result[0]["role"] == "user"
    assert result[0]["parts"][0]["text"] == "幫我看 SLAM log"
    # model with functionCall
    assert result[1]["role"] == "model"
    assert "functionCall" in result[1]["parts"][0]
    # functionResponse
    assert result[2]["role"] == "user"
    assert "functionResponse" in result[2]["parts"][0]
    # final model text
    assert result[3]["role"] == "model"


def test_gemini_normalize_response():
    raw = {
        "candidates": [{
            "content": {
                "parts": [
                    {"text": "分析結果：正常"}
                ]
            }
        }]
    }
    normalized = CloudGeminiEngine._normalize_response(raw)
    assert normalized["role"] == "assistant"
    assert normalized["content"] == "分析結果：正常"
    assert normalized["tool_calls"] is None


def test_gemini_normalize_response_with_tool_call():
    raw = {
        "candidates": [{
            "content": {
                "parts": [{
                    "functionCall": {
                        "name": "query_parser_log",
                        "args": {"time_range": "2026/03/31"},
                    }
                }]
            }
        }]
    }
    normalized = CloudGeminiEngine._normalize_response(raw)
    assert normalized["tool_calls"] is not None
    assert len(normalized["tool_calls"]) == 1
    assert normalized["tool_calls"][0]["name"] == "query_parser_log"


def test_gemini_normalize_empty_response():
    normalized = CloudGeminiEngine._normalize_response({"candidates": []})
    assert "No response" in normalized["content"]


# ---- Ollama format conversion ----

def test_ollama_tool_format():
    result = _convert_tools_to_ollama_format(SAMPLE_TOOLS)
    assert len(result) == 1
    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "query_parser_log"


def test_ollama_message_format():
    result = _convert_messages_to_ollama_format(SAMPLE_MESSAGES)
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
    assert result[2]["role"] == "tool"
    assert result[3]["role"] == "assistant"


def test_ollama_normalize_response():
    raw = {
        "message": {
            "role": "assistant",
            "content": "正常",
            "tool_calls": None,
        }
    }
    normalized = LocalOllamaEngine._normalize_response(raw)
    assert normalized["content"] == "正常"
    assert normalized["tool_calls"] is None


def test_ollama_normalize_response_with_tool_call():
    raw = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "query_parser_log",
                    "arguments": {"time_range": "2026/03/31"},
                }
            }],
        }
    }
    normalized = LocalOllamaEngine._normalize_response(raw)
    assert normalized["tool_calls"] is not None
    assert normalized["tool_calls"][0]["name"] == "query_parser_log"
    assert "id" in normalized["tool_calls"][0]
