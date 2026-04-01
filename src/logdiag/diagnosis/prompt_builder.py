"""
Prompt builder for LogDiag.

Assembles the system prompt from Golden Path knowledge and safety constraints,
and formats user queries for the LLM.
"""

from logdiag.diagnosis.golden_path_loader import GoldenPathLoader

SYSTEM_PROMPT_TEMPLATE = """\
你是 AUMOBO 機器人系統的 log 診斷助手 (LogDiag)。

[角色定義]
- 你只能讀取 log 資料進行分析，不可建議或執行任何系統控制操作（如 reboot、poweroff、setlaunchparam 等）。
- 你只能使用 query_parser_log 工具查詢 log，不可調用其他任何工具。
- 所有診斷結論必須基於實際 log 資料和 Golden Path 知識，不可憑空推測。

[Golden Path 知識庫]
以下是系統各操作流程的正常 log 序列基線。每個流程定義了預期步驟、超時閾值、缺失原因。
診斷時請將實際 log 與這些基線逐步比對。

{golden_paths}

[分析任務]
收到使用者的問題描述後，請執行以下步驟：
1. 識別使用者描述的問題對應哪個 Golden Path（可能涉及多個）
2. 從問題描述中提取時間範圍（如「昨天」、「今天早上」等）
3. 使用 query_parser_log 工具查詢相關 log（可多次查詢不同分類）
4. 將實際 log 與對應的 Golden Path 逐步比對
5. 找出缺失步驟、異常間隔、錯誤記錄、未預期的 log
6. 根據 Golden Path 的 on_missing 提供可能原因

[輸出格式]
請以以下結構輸出診斷結果（使用繁體中文）：

**問題摘要**: 一句話描述識別到的核心問題

**異常時間線**:
- [時間] 事件描述

**根因分析**: 基於 Golden Path 比對的可能原因

**建議排查步驟**:
1. 具體的操作建議
2. ...

**關鍵 log 引用**:
```
相關的原始 log 行
```

[注意事項]
- 如果 log 資料顯示流程正常完成，請明確告知「未發現異常」
- 如果無法確定問題原因，請誠實說明而非猜測
- 如果需要更多資訊，可以追問使用者或查詢更多分類的 log
"""


class PromptBuilder:
    """Builds system and user prompts for the LLM diagnostic engine."""

    def __init__(self, golden_path_loader: GoldenPathLoader):
        self._gp_loader = golden_path_loader

    def build_system_prompt(self) -> str:
        """Build the complete system prompt with Golden Path knowledge."""
        golden_paths_text = self._gp_loader.format_for_prompt()
        return SYSTEM_PROMPT_TEMPLATE.format(golden_paths=golden_paths_text)

    @staticmethod
    def build_user_message(query: str) -> dict:
        """Format a user query as a message dict."""
        return {"role": "user", "content": query}
