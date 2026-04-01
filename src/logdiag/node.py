"""
LogDiag ROS Node class.

Provides:
- /logdiag/query (Subscriber): Accepts natural language input via topic
- /logdiag/result (Publisher): Publishes diagnostic results
- /logdiag/diagnose (Service): Synchronous request/response diagnostic
"""

import json
import os
import re

import rospy
from std_msgs.msg import String

from logdiag.llm_engine import create_engine
from logdiag.tools.log_fetcher import LogFetcher
from logdiag.diagnosis.golden_path_loader import GoldenPathLoader
from logdiag.diagnosis.prompt_builder import PromptBuilder
from logdiag.conversation.manager import ConversationManager


class LogDiagNode:
    """Main ROS node for the LogDiag service."""

    def __init__(self):
        rospy.init_node("logdiag_node", anonymous=False)
        rospy.loginfo("LogDiag node initializing...")

        # ---- Load parameters ----
        self._llm_backend = rospy.get_param("logdiag/llm_backend", "cloud")
        self._max_tool_calls = rospy.get_param("logdiag/max_tool_calls", 10)
        self._session_timeout = rospy.get_param("logdiag/session_timeout_sec", 600)
        self._log_service_name = rospy.get_param("logdiag/log_service_name", "/maintenance")
        self._log_service_method = rospy.get_param("logdiag/log_service_method", "getparserlog")

        # ---- Initialize components ----

        # Golden Path loader
        golden_path_file = rospy.get_param(
            "logdiag/golden_path_file",
            self._find_golden_path_file(),
        )
        rospy.loginfo(f"Loading Golden Paths from: {golden_path_file}")
        self._gp_loader = GoldenPathLoader(golden_path_file)
        rospy.loginfo(f"Loaded Golden Paths: {self._gp_loader.path_ids}")

        # Prompt builder
        self._prompt_builder = PromptBuilder(self._gp_loader)

        # Log fetcher
        self._log_fetcher = LogFetcher(self._log_service_name, self._log_service_method)

        # LLM engine
        engine_kwargs = self._get_engine_kwargs()
        rospy.loginfo(f"Initializing LLM engine: {self._llm_backend}")
        self._engine = create_engine(self._llm_backend, **engine_kwargs)

        # Conversation manager
        self._conv_manager = ConversationManager(
            llm_engine=self._engine,
            prompt_builder=self._prompt_builder,
            log_fetcher=self._log_fetcher,
            max_tool_calls=self._max_tool_calls,
            session_timeout_sec=self._session_timeout,
        )

        # ---- ROS interfaces ----

        # Publisher for diagnostic results
        self._result_pub = rospy.Publisher(
            "/logdiag/result", String, queue_size=10
        )

        # Subscriber for natural language queries
        self._query_sub = rospy.Subscriber(
            "/logdiag/query", String, self._on_query_received
        )

        # Service for synchronous diagnosis
        # Import the service type dynamically to handle msg generation timing
        try:
            from loganalysis_agent.srv import LogDiagQuery, LogDiagQueryResponse
            from loganalysis_agent.msg import DiagResult
            self._diag_srv = rospy.Service(
                "/logdiag/diagnose", LogDiagQuery, self._on_service_request
            )
            self._DiagResult = DiagResult
            self._LogDiagQueryResponse = LogDiagQueryResponse
            rospy.loginfo("LogDiag service registered: /logdiag/diagnose")
        except ImportError:
            rospy.logwarn(
                "LogDiagQuery srv not found (msg not built yet?). "
                "Service interface disabled, topic interface still active."
            )
            self._diag_srv = None
            self._DiagResult = None
            self._LogDiagQueryResponse = None

        rospy.loginfo(
            f"LogDiag node ready. Backend={self._llm_backend}, "
            f"Topics: /logdiag/query (sub), /logdiag/result (pub)"
        )

    def _find_golden_path_file(self) -> str:
        """Locate the golden_paths.yaml file relative to this package."""
        # Try rospack first
        try:
            import rospkg
            rospack = rospkg.RosPack()
            pkg_path = rospack.get_path("loganalysis_agent")
            return os.path.join(pkg_path, "config", "golden_paths.yaml")
        except Exception:
            pass
        # Fallback: relative to this file
        this_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(this_dir, "..", "..", "config", "golden_paths.yaml")

    def _get_engine_kwargs(self) -> dict:
        """Build kwargs for the LLM engine based on the selected backend."""
        if self._llm_backend == "cloud":
            return {
                "api_key": rospy.get_param("logdiag/cloud/api_key", ""),
                "model": rospy.get_param("logdiag/cloud/model", "claude-sonnet-4-20250514"),
                "max_tokens": rospy.get_param("logdiag/cloud/max_tokens", 4096),
            }
        elif self._llm_backend == "local":
            return {
                "base_url": rospy.get_param("logdiag/local/base_url", ""),
                "model": rospy.get_param("logdiag/local/model", "qwen2.5:7b-instruct"),
                "max_tokens": rospy.get_param("logdiag/local/max_tokens", 4096),
            }
        else:
            raise ValueError(f"Unknown llm_backend: {self._llm_backend}")

    def _on_query_received(self, msg: String):
        """Handle incoming query from /logdiag/query topic."""
        query = msg.data.strip()
        if not query:
            return
        rospy.loginfo(f"Received query via topic: {query[:80]}...")

        result = self._conv_manager.diagnose(query)

        # Publish result as JSON string on /logdiag/result
        result_msg = String()
        result_msg.data = json.dumps(result, ensure_ascii=False, indent=2)
        self._result_pub.publish(result_msg)
        rospy.loginfo(f"Published diagnosis result for session {result['session_id']}")

    def _on_service_request(self, req):
        """Handle incoming LogDiagQuery service request."""
        query = req.query.strip()
        session_id = req.session_id.strip()

        rospy.loginfo(f"Received service request: query='{query[:80]}...'")

        result = self._conv_manager.diagnose(query, session_id)
        response = self._LogDiagQueryResponse()

        diag = self._DiagResult()
        diag.session_id = result["session_id"]
        diag.status = result["status"]
        diag.error_message = result.get("error_message", "")

        # Parse structured content from LLM response
        content = result.get("content", "")
        parsed = self._parse_diag_content(content)
        diag.summary = parsed.get("summary", content[:200] if content else "")
        diag.timeline = parsed.get("timeline", "")
        diag.root_cause = parsed.get("root_cause", "")
        diag.suggestions = parsed.get("suggestions", "")
        diag.raw_log_references = parsed.get("raw_log_references", "")

        response.result = diag
        return response

    @staticmethod
    def _parse_diag_content(content: str) -> dict:
        """
        Best-effort parsing of the LLM's structured diagnostic output.

        Extracts sections based on the expected output format markers.
        """
        result = {
            "summary": "",
            "timeline": "",
            "root_cause": "",
            "suggestions": "",
            "raw_log_references": "",
        }
        if not content:
            return result

        section_patterns = [
            ("summary", r"\*\*問題摘要\*\*[:\s：]*(.+?)(?=\n\*\*|\Z)"),
            ("timeline", r"\*\*異常時間線\*\*[:\s：]*(.+?)(?=\n\*\*|\Z)"),
            ("root_cause", r"\*\*根因分析\*\*[:\s：]*(.+?)(?=\n\*\*|\Z)"),
            ("suggestions", r"\*\*建議排查步驟\*\*[:\s：]*(.+?)(?=\n\*\*|\Z)"),
            ("raw_log_references", r"\*\*關鍵 log 引用\*\*[:\s：]*(.+?)(?=\n\*\*|\Z)"),
        ]

        for key, pattern in section_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                result[key] = match.group(1).strip()

        # Fallback: if no sections matched, put full content in summary
        if not any(result.values()):
            result["summary"] = content[:500]

        return result

    def run(self):
        """Spin the ROS node."""
        rospy.spin()
