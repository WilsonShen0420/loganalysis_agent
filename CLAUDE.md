# CLAUDE.md — AI Assistant Guide for AUMOBO LogDiag

## Project Overview

**AUMOBO Log-Based Diagnostic AI Service (LogDiag)** — a ROS Noetic node that accepts natural language queries, retrieves system logs via the existing `getparserlog` ROS service, compares them against predefined Golden Path baselines, and outputs structured diagnostic reports powered by LLM (cloud: Claude API / OpenAI ChatGPT / Google Gemini; local: Ollama + Qwen2.5-7B-Instruct).

## Repository Structure

```
loganalysis_agent/
├── CLAUDE.md                            # This file
├── package.xml                          # ROS Noetic package definition
├── CMakeLists.txt                       # catkin build configuration
├── setup.py                             # Python module install for catkin
│
├── msg/
│   └── DiagResult.msg                   # Diagnostic result ROS message
│
├── srv/
│   └── LogDiagQuery.srv                 # Diagnostic request ROS service
│
├── config/
│   ├── golden_paths.yaml                # Golden Path knowledge base
│   └── logdiag_params.yaml              # ROS parameters (LLM backend, API key, etc.)
│
├── launch/
│   └── logdiag.launch                   # Launch file
│
├── scripts/
│   └── logdiag_node.py                  # ROS Node entry point (executable)
│
├── src/
│   └── logdiag/
│       ├── __init__.py
│       ├── node.py                      # ROS Node class
│       ├── llm_engine/
│       │   ├── __init__.py
│       │   ├── base.py                  # LLM abstract base class
│       │   ├── cloud_claude.py          # Claude API (Anthropic SDK)
│       │   ├── cloud_openai.py          # OpenAI ChatGPT API
│       │   ├── cloud_gemini.py          # Google Gemini API
│       │   └── local_ollama.py          # Ollama + Qwen2.5-7B-Instruct
│       ├── tools/
│       │   ├── __init__.py
│       │   └── log_fetcher.py           # getparserlog ROS service wrapper
│       ├── diagnosis/
│       │   ├── __init__.py
│       │   ├── golden_path_loader.py    # YAML knowledge base loader
│       │   └── prompt_builder.py        # System/User prompt assembly
│       └── conversation/
│           ├── __init__.py
│           └── manager.py               # Multi-turn tool-use conversation loop
│
├── test/
│   ├── sample_logs/                     # Sample log files for testing
│   │   ├── localization_normal.txt
│   │   └── localization_missing_maploading.txt
│   ├── test_golden_path_loader.py
│   ├── test_prompt_builder.py
│   └── test_conversation_manager.py
│
└── docs/
    ├── AUMOBO_LogDiag_PRD.docx          # Product Requirements Document
    └── log_diagnosis/
        └── golden_path_guide.md         # How to write Golden Paths
```

## Architecture

### Three-Layer Design

| Layer | Responsibility |
|-------|---------------|
| Layer 1: Golden Path Knowledge Base | YAML definitions of expected log sequences, timeouts, error patterns |
| Layer 2: Log Retrieval & Preprocessing | Wraps `getparserlog` ROS service as an LLM tool |
| Layer 3: LLM Diagnostic Engine | Receives natural language queries, orchestrates tool calls, compares against Golden Paths |

### LLM Backends

- **Claude**: Anthropic Claude API (`claude-sonnet-4-20250514`) via `anthropic` Python SDK
- **OpenAI**: OpenAI ChatGPT API (`gpt-4o`) via `openai` Python SDK
- **Gemini**: Google Gemini API (`gemini-2.0-flash`) via REST API
- **Local**: Ollama + `qwen2.5:7b-instruct` via HTTP API (`localhost:11434`)

Selected via ROS param `~llm_backend` (`"claude"`, `"openai"`, `"gemini"`, or `"local"`).

### ROS Interfaces

| Interface | Type | Description |
|-----------|------|-------------|
| `/logdiag/query` | Subscriber (`std_msgs/String`) | Receives natural language input |
| `/logdiag/result` | Publisher (`logdiag/DiagResult`) | Publishes diagnostic results |
| `/logdiag/diagnose` | Service (`logdiag/LogDiagQuery`) | Synchronous request/response |

### Security Constraints

- **Read-only mode**: LLM can ONLY call `query_parser_log` tool (whitelist enforced)
- LLM MUST NOT invoke any write operations or system control commands
- All diagnostic results are suggestions only; final decisions are made by humans

## Development Conventions

### Language & Framework

- Python 3 (rospy) for the LogDiag node
- ROS Noetic (Ubuntu 20.04)
- catkin build system

### Coding Style

- Follow PEP 8
- Use type hints for function signatures
- Use `rospy.loginfo/logwarn/logerr` for logging within ROS context
- Keep modules focused: one responsibility per file

### Golden Path YAML Format

Every diagnosable operation must define:
- `description`: Human-readable description
- `trigger`: The starting log pattern
- `steps[]`: Ordered expected log sequence with `pattern`, `timeout_ms`, `on_missing`, `alternatives`
- `error_patterns[]`: Known error patterns and their meanings

See `config/golden_paths.yaml` for reference.

### Log Format

Standard AUMOBO log format: `YYYY/MM/DD:HHMMSS:mmm - category:content`

Categories: `loc`, `slam`, `tcp`, `error`, `booting`, `sensor`, `maintenance`, `nav`, `network`

### Testing

- Unit tests in `test/` directory
- Sample logs in `test/sample_logs/`
- Run tests: `python -m pytest test/ -v`

### Environment Variables

- `ANTHROPIC_API_KEY`: Required for Claude backend
- `OPENAI_API_KEY`: Required for OpenAI backend
- `GOOGLE_API_KEY`: Required for Gemini backend
- `OLLAMA_HOST`: Override Ollama endpoint (default: `http://localhost:11434`)
