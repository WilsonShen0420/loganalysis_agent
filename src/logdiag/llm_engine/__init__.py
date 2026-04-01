from logdiag.llm_engine.base import BaseLLMEngine
from logdiag.llm_engine.cloud_claude import CloudClaudeEngine
from logdiag.llm_engine.local_ollama import LocalOllamaEngine


def create_engine(backend: str, **kwargs) -> BaseLLMEngine:
    """Factory function to create the appropriate LLM engine."""
    if backend == "cloud":
        return CloudClaudeEngine(**kwargs)
    elif backend == "local":
        return LocalOllamaEngine(**kwargs)
    else:
        raise ValueError(f"Unknown LLM backend: {backend}. Use 'cloud' or 'local'.")
