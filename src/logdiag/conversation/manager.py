"""
Conversation manager for the LogDiag tool-use agent loop.

Handles multi-turn conversations where the LLM can call tools (query_parser_log)
multiple times before producing a final diagnostic response.
"""

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from logdiag.llm_engine.base import BaseLLMEngine
from logdiag.tools.log_fetcher import ALLOWED_TOOLS, TOOL_DEFINITION, LogFetcher
from logdiag.diagnosis.prompt_builder import PromptBuilder

try:
    import rospy
    def _log_info(msg): rospy.loginfo(msg)
    def _log_warn(msg): rospy.logwarn(msg)
    def _log_err(msg): rospy.logerr(msg)
except ImportError:
    import logging
    _logger = logging.getLogger("logdiag.conversation")
    def _log_info(msg): _logger.info(msg)
    def _log_warn(msg): _logger.warning(msg)
    def _log_err(msg): _logger.error(msg)


class Session:
    """A single diagnostic conversation session."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.messages: List[Dict[str, Any]] = []
        self.created_at = time.time()

    def add_message(self, message: Dict[str, Any]):
        self.messages.append(message)


class ConversationManager:
    """
    Manages the tool-use conversation loop.

    Flow:
    1. User query → build messages with system prompt
    2. Send to LLM with tool definitions
    3. If LLM responds with tool_calls → execute tools → add results → re-send
    4. Repeat until LLM responds with content (no tool_calls) or max_tool_calls reached
    5. Return final LLM response
    """

    def __init__(
        self,
        llm_engine: BaseLLMEngine,
        prompt_builder: PromptBuilder,
        log_fetcher: LogFetcher,
        max_tool_calls: int = 10,
        session_timeout_sec: int = 600,
    ):
        self._engine = llm_engine
        self._prompt_builder = prompt_builder
        self._fetcher = log_fetcher
        self._max_tool_calls = max_tool_calls
        self._session_timeout = session_timeout_sec
        self._sessions: Dict[str, Session] = {}

    def get_or_create_session(self, session_id: str = "") -> Session:
        """Retrieve an existing session or create a new one."""
        # Clean up expired sessions
        self._cleanup_expired_sessions()

        if session_id and session_id in self._sessions:
            return self._sessions[session_id]

        session = Session()
        self._sessions[session.session_id] = session
        _log_info(f"Created new session: {session.session_id}")
        return session

    def diagnose(self, query: str, session_id: str = "") -> Dict[str, Any]:
        """
        Run a full diagnostic conversation for the given query.

        Args:
            query: Natural language query from the user.
            session_id: Optional session ID to continue an existing conversation.

        Returns:
            Dict with keys: session_id, content, status, error_message
        """
        session = self.get_or_create_session(session_id)

        # Add user message
        user_msg = self._prompt_builder.build_user_message(query)
        session.add_message(user_msg)

        # Build system prompt
        system_prompt = self._prompt_builder.build_system_prompt()

        # Tool definitions
        tools = [TOOL_DEFINITION]

        # Tool-use loop
        tool_call_count = 0
        try:
            while tool_call_count < self._max_tool_calls:
                _log_info(
                    f"[{session.session_id}] Sending to LLM "
                    f"(tool_calls so far: {tool_call_count})"
                )

                response = self._engine.chat(
                    messages=session.messages,
                    tools=tools,
                    system_prompt=system_prompt,
                )

                # If LLM returned tool calls, execute them
                if response.get("tool_calls"):
                    session.add_message(response)

                    for tc in response["tool_calls"]:
                        tool_call_count += 1
                        tool_result = self._execute_tool(tc)
                        session.add_message({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": tool_result,
                        })

                    if tool_call_count >= self._max_tool_calls:
                        _log_warn(
                            f"[{session.session_id}] "
                            f"Max tool calls ({self._max_tool_calls}) reached."
                        )
                        # One final call without tools to force a text response
                        response = self._engine.chat(
                            messages=session.messages,
                            tools=None,
                            system_prompt=system_prompt,
                        )
                        session.add_message(response)
                        break
                else:
                    # LLM returned content (final response)
                    session.add_message(response)
                    break

            content = response.get("content") or ""
            return {
                "session_id": session.session_id,
                "content": content,
                "status": 0,
                "error_message": "",
            }

        except Exception as e:
            _log_err(f"[{session.session_id}] Diagnosis failed: {e}")
            return {
                "session_id": session.session_id,
                "content": "",
                "status": 2,
                "error_message": str(e),
            }

    def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """Execute a single tool call from the LLM, with security checks."""
        tool_name = tool_call.get("name", "")
        arguments = tool_call.get("arguments", {})

        # Security: whitelist check
        if tool_name not in ALLOWED_TOOLS:
            _log_warn(f"Blocked disallowed tool call: {tool_name}")
            return f"[SECURITY] Tool '{tool_name}' is not allowed. Only {list(ALLOWED_TOOLS)} can be used."

        _log_info(f"Executing tool: {tool_name} with args: {arguments}")

        if tool_name == "query_parser_log":
            return self._fetcher.execute_tool_call(arguments)

        return f"[ERROR] Unknown tool: {tool_name}"

    def _cleanup_expired_sessions(self):
        """Remove sessions older than the timeout."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.created_at > self._session_timeout
        ]
        for sid in expired:
            del self._sessions[sid]
            _log_info(f"Cleaned up expired session: {sid}")
