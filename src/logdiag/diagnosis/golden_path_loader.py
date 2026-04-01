"""
Golden Path knowledge base loader.

Reads the YAML file containing expected log sequences for each
diagnosable operation and provides lookup/formatting utilities.
"""

from typing import Any, Dict, List, Optional

import yaml


class GoldenPathLoader:
    """Loads and provides access to Golden Path definitions."""

    def __init__(self, yaml_path: str):
        self._yaml_path = yaml_path
        self._paths: Dict[str, Any] = {}
        self._load()

    def _load(self):
        """Load Golden Paths from the YAML file."""
        with open(self._yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid golden_paths.yaml: expected dict, got {type(data)}")
        self._paths = data

    def reload(self):
        """Reload the YAML file (useful if updated at runtime)."""
        self._load()

    @property
    def path_ids(self) -> List[str]:
        """Return all Golden Path IDs."""
        return list(self._paths.keys())

    def get_path(self, path_id: str) -> Optional[Dict[str, Any]]:
        """Get a single Golden Path definition by ID."""
        return self._paths.get(path_id)

    def get_all_paths(self) -> Dict[str, Any]:
        """Get all Golden Path definitions."""
        return dict(self._paths)

    def format_for_prompt(self) -> str:
        """
        Format all Golden Paths as a readable string for inclusion in
        the LLM system prompt.
        """
        lines = []
        for path_id, path_def in self._paths.items():
            lines.append(f"## {path_id}")
            lines.append(f"描述: {path_def.get('description', 'N/A')}")
            lines.append(f"觸發條件: {path_def.get('trigger', 'N/A')}")
            lines.append("")

            steps = path_def.get("steps", [])
            lines.append("預期步驟序列:")
            for i, step in enumerate(steps, 1):
                pattern = step.get("pattern", "?")
                timeout = step.get("timeout_ms")
                on_missing = step.get("on_missing", "")
                alts = step.get("alternatives", [])

                timeout_str = f"{timeout}ms" if timeout else "無限制"
                lines.append(f"  {i}. pattern: \"{pattern}\" (超時: {timeout_str})")
                if alts:
                    lines.append(f"     替代 pattern: {alts}")
                if on_missing:
                    lines.append(f"     缺失原因: {on_missing}")

            error_patterns = path_def.get("error_patterns", [])
            if error_patterns:
                lines.append("")
                lines.append("已知錯誤 pattern:")
                for ep in error_patterns:
                    lines.append(f"  - \"{ep.get('pattern', '?')}\": {ep.get('meaning', '')}")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)
