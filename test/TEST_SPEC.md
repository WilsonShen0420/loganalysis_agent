# LogDiag 單元測試說明

## 執行方式

```bash
cd loganalysis_agent
PYTHONPATH=src:$PYTHONPATH python -m pytest test/ -v
```

## 測試總覽

共 30 個測試，分佈於 4 個測試檔案。所有測試皆為離線測試，不需要 ROS 環境、LLM API key 或網路連線。

---

## 1. test_golden_path_loader.py（6 個測試）

測試 Golden Path YAML 知識庫的載入與格式化功能。

| # | 測試名稱 | 目的 | 預期結果 |
|---|---------|------|---------|
| 1 | `test_load_path_ids` | 驗證 YAML 載入後能取得所有 P0 流程 ID | 回傳的 ID 列表包含 `localization_start`, `slam_build`, `sensor_health`, `system_boot` |
| 2 | `test_get_path_localization` | 驗證單一 Golden Path 的結構完整性 | `localization_start` 的 trigger 為 `loc:mobile_setting_finish`，包含 6 個 steps 和 2 個 error_patterns |
| 3 | `test_get_path_steps_have_required_fields` | 驗證所有流程的每個 step 都有必要欄位 | 每個 step 都包含 `pattern` 和 `timeout_ms` 欄位 |
| 4 | `test_get_nonexistent_path` | 驗證查詢不存在的流程 ID 不會報錯 | 回傳 `None` |
| 5 | `test_format_for_prompt_contains_all_paths` | 驗證格式化後的 prompt 文字包含所有流程 | 輸出字串中包含每一個 path_id |
| 6 | `test_format_for_prompt_contains_on_missing` | 驗證 prompt 文字包含缺失原因說明 | 輸出字串中包含「地圖載入逾時」、「LiDAR brand 配置」等 on_missing 文字 |

---

## 2. test_prompt_builder.py（5 個測試）

測試 System Prompt 組裝邏輯，確保送給 LLM 的 prompt 包含所有必要元素。

| # | 測試名稱 | 目的 | 預期結果 |
|---|---------|------|---------|
| 1 | `test_system_prompt_contains_role` | 驗證 prompt 包含角色定義 | 字串中包含「AUMOBO」、「log 診斷助手」 |
| 2 | `test_system_prompt_contains_safety_constraints` | 驗證 prompt 包含安全約束（唯讀限制） | 字串中包含「只能讀取 log」、「query_parser_log」 |
| 3 | `test_system_prompt_contains_golden_paths` | 驗證 prompt 包含 Golden Path 知識 | 字串中包含「localization_start」、「slam_build」 |
| 4 | `test_system_prompt_contains_output_format` | 驗證 prompt 包含結構化輸出格式要求 | 字串中包含「問題摘要」、「異常時間線」、「根因分析」 |
| 5 | `test_build_user_message` | 驗證 user message 格式正確 | 回傳 `{"role": "user", "content": "SLAM 建圖失敗了"}` |

---

## 3. test_conversation_manager.py（4 個測試）

測試 Tool-Use 對話迴圈的核心邏輯。使用 MockLLMEngine（模擬 LLM 回應）和 MockLogFetcher（回傳 sample log 檔案）進行離線測試。

| # | 測試名稱 | 目的 | 預期結果 |
|---|---------|------|---------|
| 1 | `test_diagnose_with_tool_call_then_response` | 驗證完整的 tool-use 流程：LLM 先發出 tool_call → 執行 tool → 回傳 log 資料 → LLM 產出最終診斷 | `status=0`，`session_id` 非空，`content` 包含「未發現異常」 |
| 2 | `test_diagnose_blocked_tool` | 驗證安全白名單：LLM 嘗試調用未授權的 tool（`reboot_system`）會被攔截 | 不會拋出例外，`status=0`，非法 tool 回傳 `[SECURITY]` 錯誤訊息給 LLM |
| 3 | `test_session_continuity` | 驗證多輪對話：使用相同 session_id 追問時，對話歷史被保留 | 第二次查詢回傳的 `session_id` 與第一次相同 |
| 4 | `test_max_tool_calls_limit` | 驗證無限迴圈防護：設定 `max_tool_calls=3`，LLM 持續發出 tool_call | 達到上限後強制 LLM 回傳文字回應，`status=0`，不會無限迴圈 |

### 測試用 Sample Log 檔案

| 檔案 | 內容 | 用途 |
|------|------|------|
| `test/sample_logs/localization_normal.txt` | 完整的定位載圖流程 log（6 步全部出現） | 正常流程測試 |
| `test/sample_logs/localization_missing_maploading.txt` | 缺少 `maploading_finish` 步驟，出現 `error:maploading_timeout` | 異常流程測試 |

---

## 4. test_llm_engines.py（15 個測試）

測試 4 種 LLM 引擎的訊息格式轉換與回應正規化，確保各引擎的 API 格式差異被正確處理。

### 4.1 Factory 測試（2 個）

| # | 測試名稱 | 目的 | 預期結果 |
|---|---------|------|---------|
| 1 | `test_factory_supported_backends` | 驗證 factory 註冊了所有 4 種引擎 | `_ENGINE_MAP` 包含 `claude`, `openai`, `gemini`, `local` |
| 2 | `test_factory_unknown_backend` | 驗證不支援的 backend 會報錯 | 拋出 `ValueError`，訊息包含 "Unknown LLM backend" |

### 4.2 Claude 格式轉換（2 個）

| # | 測試名稱 | 目的 | 預期結果 |
|---|---------|------|---------|
| 3 | `test_claude_tool_format` | 驗證 tool 定義轉為 Anthropic 格式 | 輸出包含 `name` 和 `input_schema` |
| 4 | `test_claude_message_format` | 驗證對話訊息轉為 Anthropic 格式（tool_use / tool_result content blocks） | assistant 訊息包含 `tool_use` block，tool result 包裝為 `tool_result` block |

### 4.3 OpenAI 格式轉換（2 個）

| # | 測試名稱 | 目的 | 預期結果 |
|---|---------|------|---------|
| 5 | `test_openai_tool_format` | 驗證 tool 定義轉為 OpenAI function-calling 格式 | 輸出為 `{"type": "function", "function": {...}}` |
| 6 | `test_openai_message_format` | 驗證對話訊息轉為 OpenAI 格式（含 system prompt 插入） | system prompt 為第一條訊息，tool_calls 包含 `id` 和 `function`，tool result 使用 `tool_call_id` |

### 4.4 Gemini 格式轉換（5 個）

| # | 測試名稱 | 目的 | 預期結果 |
|---|---------|------|---------|
| 7 | `test_gemini_tool_format` | 驗證 tool 定義轉為 Gemini `function_declarations` 格式 | 輸出為 `[{"function_declarations": [...]}]` |
| 8 | `test_gemini_message_format` | 驗證對話訊息轉為 Gemini contents 格式 | role 使用 `model`（非 `assistant`），tool call 為 `functionCall`，tool result 為 `functionResponse` |
| 9 | `test_gemini_normalize_response` | 驗證純文字回應的正規化 | 正確提取 `text` 部分，`tool_calls` 為 `None` |
| 10 | `test_gemini_normalize_response_with_tool_call` | 驗證含 `functionCall` 回應的正規化 | 正確提取 tool name 和 arguments，自動產生 `id` |
| 11 | `test_gemini_normalize_empty_response` | 驗證空回應（無 candidates）的處理 | 回傳包含 "No response" 的 content，不會拋出例外 |

### 4.5 Ollama 格式轉換（4 個）

| # | 測試名稱 | 目的 | 預期結果 |
|---|---------|------|---------|
| 12 | `test_ollama_tool_format` | 驗證 tool 定義轉為 Ollama 格式 | 輸出為 `{"type": "function", "function": {...}}`（與 OpenAI 相似） |
| 13 | `test_ollama_message_format` | 驗證對話訊息轉為 Ollama chat 格式 | role 保持 `user`, `assistant`, `tool` |
| 14 | `test_ollama_normalize_response` | 驗證純文字回應的正規化 | 正確提取 `content`，`tool_calls` 為 `None` |
| 15 | `test_ollama_normalize_response_with_tool_call` | 驗證含 tool_call 回應的正規化 | 正確提取 function name 和 arguments，自動產生 UUID 作為 `id` |
