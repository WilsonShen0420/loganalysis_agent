from logdiag.llm_engine.base import BaseLLMEngine
from logdiag.llm_engine.cloud_claude import CloudClaudeEngine
from logdiag.llm_engine.cloud_openai import CloudOpenAIEngine
from logdiag.llm_engine.cloud_gemini import CloudGeminiEngine
from logdiag.llm_engine.local_ollama import LocalOllamaEngine

# Registry of all supported backends
_ENGINE_MAP = {
    "claude": CloudClaudeEngine,
    "openai": CloudOpenAIEngine,
    "gemini": CloudGeminiEngine,
    "local":  LocalOllamaEngine,
}


def create_engine(backend: str, **kwargs) -> BaseLLMEngine:
    """
    Factory function to create the appropriate LLM engine.

    Supported backends:
      - "claude": Anthropic Claude API
      - "openai": OpenAI ChatGPT API
      - "gemini": Google Gemini API
      - "local":  Ollama (local, e.g. Qwen2.5-7B-Instruct)
    """
    engine_class = _ENGINE_MAP.get(backend)
    if engine_class is None:
        supported = ", ".join(sorted(_ENGINE_MAP.keys()))
        raise ValueError(
            f"Unknown LLM backend: '{backend}'. Supported: {supported}"
        )
    return engine_class(**kwargs)
