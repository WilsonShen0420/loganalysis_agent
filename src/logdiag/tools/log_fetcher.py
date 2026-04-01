"""
Log fetcher tool — wraps the AUMOBO getparserlog ROS service.

This module provides:
1. TOOL_DEFINITION: The tool schema exposed to the LLM for tool-use.
2. LogFetcher: Class that executes the actual ROS service call.
"""

import subprocess
from typing import Any, Dict, Optional

try:
    import rospy
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False


# ---- Tool definition exposed to the LLM ----

TOOL_DEFINITION = {
    "name": "query_parser_log",
    "description": (
        "查詢 AUMOBO 系統的 runtime log。透過 ROS service getparserlog "
        "取得指定時間範圍與分類的 log 資料。\n"
        "可用的 log 分類: loc, slam, tcp, error, booting, sensor, "
        "maintenance, nav, network\n"
        "如果不指定 filter，將回傳該時間範圍內所有分類的 log。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "time_range": {
                "type": "string",
                "description": (
                    "時間範圍。格式: 'YYYY/MM/DD' (單日) "
                    "或 'YYYY/MM/DD-YYYY/MM/DD' (區間)"
                ),
            },
            "filter": {
                "type": "string",
                "description": (
                    "log 分類關鍵字篩選，例如: loc, slam, error, sensor, booting 等。"
                    "可留空以取得所有分類。"
                ),
            },
        },
        "required": ["time_range"],
    },
}

# Whitelist of tools the LLM is allowed to call (security constraint)
ALLOWED_TOOLS = frozenset({"query_parser_log"})


class LogFetcher:
    """
    Executes the getparserlog ROS service call and returns log text.

    In production, this calls the actual ROS service via rospy or subprocess.
    In test/offline mode, it can be used with mock data.
    """

    def __init__(self, service_name: str = "/maintenance",
                 service_method: str = "getparserlog"):
        self._service_name = service_name
        self._service_method = service_method

    def fetch(self, time_range: str, filter_category: Optional[str] = None) -> str:
        """
        Query logs via getparserlog.

        Args:
            time_range: Date or date range string (e.g., "2026/03/31").
            filter_category: Optional log category filter (e.g., "slam", "error").

        Returns:
            Raw log text from the service, or an error message.
        """
        if ROS_AVAILABLE:
            return self._fetch_via_ros(time_range, filter_category)
        return self._fetch_via_subprocess(time_range, filter_category)

    def _fetch_via_ros(self, time_range: str,
                       filter_category: Optional[str] = None) -> str:
        """Fetch logs using rospy service proxy."""
        try:
            # Build the service call arguments
            # The actual service type depends on the AUMOBO system definition.
            # We use a generic approach via rosservice call.
            cmd = self._build_rosservice_cmd(time_range, filter_category)
            rospy.loginfo(f"LogFetcher: calling {cmd}")
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return f"[ERROR] getparserlog failed: {result.stderr.strip()}"
            return result.stdout.strip() or "[EMPTY] No log entries found."
        except subprocess.TimeoutExpired:
            return "[ERROR] getparserlog call timed out (30s)."
        except Exception as e:
            return f"[ERROR] getparserlog call failed: {e}"

    def _fetch_via_subprocess(self, time_range: str,
                              filter_category: Optional[str] = None) -> str:
        """Fallback: fetch logs via rosservice CLI command."""
        cmd = self._build_rosservice_cmd(time_range, filter_category)
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return f"[ERROR] getparserlog failed: {result.stderr.strip()}"
            return result.stdout.strip() or "[EMPTY] No log entries found."
        except subprocess.TimeoutExpired:
            return "[ERROR] getparserlog call timed out (30s)."
        except FileNotFoundError:
            return "[ERROR] rosservice command not found. Is ROS environment sourced?"
        except Exception as e:
            return f"[ERROR] getparserlog call failed: {e}"

    def _build_rosservice_cmd(self, time_range: str,
                              filter_category: Optional[str] = None) -> str:
        """Build the rosservice call command string."""
        # rosservice call /maintenance "cmd: 'getparserlog' args: ['2026/03/31','slam']"
        if filter_category:
            args = f"['{time_range}','{filter_category}']"
        else:
            args = f"['{time_range}']"
        return (
            f"rosservice call {self._service_name} "
            f"\"cmd: '{self._service_method}' args: {args}\""
        )

    def execute_tool_call(self, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool call from the LLM.

        Args:
            arguments: The arguments dict from the LLM's tool_call.

        Returns:
            Log text result.
        """
        time_range = arguments.get("time_range", "")
        filter_category = arguments.get("filter", None)
        if not time_range:
            return "[ERROR] time_range is required."
        return self.fetch(time_range, filter_category)
