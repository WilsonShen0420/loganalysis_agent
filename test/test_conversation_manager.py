"""Tests for the conversation manager with a mock LLM engine."""

import os
import pytest

from logdiag.llm_engine.base import BaseLLMEngine
from logdiag.tools.log_fetcher import LogFetcher
from logdiag.diagnosis.golden_path_loader import GoldenPathLoader
from logdiag.diagnosis.prompt_builder import PromptBuilder
from logdiag.conversation.manager import ConversationManager

GOLDEN_PATH_FILE = os.path.join(
    os.path.dirname(__file__), "..", "config", "golden_paths.yaml"
)

SAMPLE_LOG_NORMAL = os.path.join(
    os.path.dirname(__file__), "sample_logs", "localization_normal.txt"
)

SAMPLE_LOG_ABNORMAL = os.path.join(
    os.path.dirname(__file__), "sample_logs", "localization_missing_maploading.txt"
)


class MockLLMEngine(BaseLLMEngine):
    """Mock LLM that simulates a tool-use then final response flow."""

    def __init__(self, responses):
        """
        Args:
            responses: List of dicts to return in sequence on each chat() call.
        """
        self._responses = list(responses)
        self._call_count = 0

    def chat(self, messages, tools=None, system_prompt=None):
        if self._call_count < len(self._responses):
            resp = self._responses[self._call_count]
            self._call_count += 1
            return resp
        return {"role": "assistant", "content": "No more mock responses.", "tool_calls": None}


class MockLogFetcher(LogFetcher):
    """Mock log fetcher that returns sample log data."""

    def __init__(self, sample_log_path):
        super().__init__()
        with open(sample_log_path, "r") as f:
            self._sample_data = f.read()

    def execute_tool_call(self, arguments):
        return self._sample_data


@pytest.fixture
def gp_loader():
    return GoldenPathLoader(GOLDEN_PATH_FILE)


def test_diagnose_with_tool_call_then_response(gp_loader):
    """Test a flow where LLM calls a tool once, then returns a final answer."""
    mock_responses = [
        # First response: LLM wants to call a tool
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_001",
                "name": "query_parser_log",
                "arguments": {"time_range": "2026/03/31", "filter": "loc"},
            }],
        },
        # Second response: LLM returns final diagnosis
        {
            "role": "assistant",
            "content": "**問題摘要**: 定位載圖流程正常完成，未發現異常。",
            "tool_calls": None,
        },
    ]

    engine = MockLLMEngine(mock_responses)
    fetcher = MockLogFetcher(SAMPLE_LOG_NORMAL)
    builder = PromptBuilder(gp_loader)

    manager = ConversationManager(
        llm_engine=engine,
        prompt_builder=builder,
        log_fetcher=fetcher,
        max_tool_calls=10,
    )

    result = manager.diagnose("幫我看看今天的定位載圖是否正常")

    assert result["status"] == 0
    assert result["session_id"]
    assert "未發現異常" in result["content"]


def test_diagnose_blocked_tool(gp_loader):
    """Test that disallowed tool calls are blocked."""
    mock_responses = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_bad",
                "name": "reboot_system",
                "arguments": {},
            }],
        },
        {
            "role": "assistant",
            "content": "無法執行該操作。",
            "tool_calls": None,
        },
    ]

    engine = MockLLMEngine(mock_responses)
    fetcher = MockLogFetcher(SAMPLE_LOG_NORMAL)
    builder = PromptBuilder(gp_loader)

    manager = ConversationManager(
        llm_engine=engine,
        prompt_builder=builder,
        log_fetcher=fetcher,
    )

    result = manager.diagnose("reboot the system")
    assert result["status"] == 0


def test_session_continuity(gp_loader):
    """Test that the same session_id resumes the conversation."""
    mock_responses = [
        {"role": "assistant", "content": "第一次回應", "tool_calls": None},
        {"role": "assistant", "content": "第二次回應", "tool_calls": None},
    ]

    engine = MockLLMEngine(mock_responses)
    fetcher = MockLogFetcher(SAMPLE_LOG_NORMAL)
    builder = PromptBuilder(gp_loader)

    manager = ConversationManager(
        llm_engine=engine,
        prompt_builder=builder,
        log_fetcher=fetcher,
    )

    result1 = manager.diagnose("第一個問題")
    sid = result1["session_id"]

    result2 = manager.diagnose("追問", session_id=sid)
    assert result2["session_id"] == sid


def test_max_tool_calls_limit(gp_loader):
    """Test that the manager stops after max_tool_calls."""
    # All responses are tool calls — should hit the limit
    tool_response = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_loop",
            "name": "query_parser_log",
            "arguments": {"time_range": "2026/03/31"},
        }],
    }
    # 5 tool call responses + 1 final forced response
    mock_responses = [tool_response] * 5 + [
        {"role": "assistant", "content": "Reached limit.", "tool_calls": None},
    ]

    engine = MockLLMEngine(mock_responses)
    fetcher = MockLogFetcher(SAMPLE_LOG_NORMAL)
    builder = PromptBuilder(gp_loader)

    manager = ConversationManager(
        llm_engine=engine,
        prompt_builder=builder,
        log_fetcher=fetcher,
        max_tool_calls=3,
    )

    result = manager.diagnose("test max tool calls")
    assert result["status"] == 0
