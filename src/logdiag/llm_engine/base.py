"""Abstract base class for LLM engines."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMEngine(ABC):
    """
    Unified interface for LLM backends (cloud and local).

    All engines must return responses in a normalized format:
    {
        "role": "assistant",
        "content": str | None,
        "tool_calls": [{"id": str, "name": str, "arguments": dict}] | None
    }
    """

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send messages to the LLM and return a normalized response.

        Args:
            messages: Conversation history in OpenAI-style format.
            tools: Tool definitions available for the LLM to call.
            system_prompt: System-level instructions.

        Returns:
            Normalized response dict with "role", "content", and "tool_calls".
        """
        pass
