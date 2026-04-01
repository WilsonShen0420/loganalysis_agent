# Golden Path 撰寫指南

## 什麼是 Golden Path

Golden Path 是一個操作流程的「預期正常 log 序列」。它定義了：

- 該流程應該產生哪些 log（按順序）
- 每個步驟之間的最大容許時間
- 某個步驟缺失時，最可能的原因是什麼
- 該流程中已知的錯誤 pattern

## YAML 格式

每個 Golden Path 定義在 `config/golden_paths.yaml` 中，格式如下：

```yaml
flow_id:                          # 流程唯一識別碼 (snake_case)
  description: "流程描述"          # 繁體中文描述
  trigger: "category:pattern"      # 觸發此流程的起始 log pattern
  steps:
    - pattern: "category:content"  # 預期的 log 內容 (支援 * 萬用字元)
      timeout_ms: 5000             # 距前一步驟的最大容許時間 (ms)，null = 不限
      on_missing: "缺失原因說明"    # 此步驟未出現時的可能原因
      alternatives:                # (選填) 替代 pattern，出現任一即通過
        - "category:alt_pattern"
  error_patterns:
    - pattern: "category:error"    # 已知的錯誤 log pattern
      meaning: "此錯誤的含義說明"
```

## 撰寫步驟

1. **確認流程邊界**：此流程從哪個 log 開始，到哪個 log 結束？
2. **列出正常步驟**：在正常情況下，依序會出現哪些 log？
3. **測定時間閾值**：每個步驟之間通常需要多久？設定 `timeout_ms` 為正常值的 2-3 倍
4. **撰寫 on_missing**：每個步驟缺失時，最可能的根因是什麼？
5. **收集錯誤 pattern**：此流程中，有哪些已知的錯誤 log？

## 範例

參考 `localization_start` (定位載圖流程)：

```yaml
localization_start:
  description: "定位載圖流程：從 map switch 命令到完成定位"
  trigger: "loc:mobile_setting_finish"
  steps:
    - pattern: "loc:mobile_setting_finish"
      timeout_ms: null
    - pattern: "loc:map_loading_set-*"
      timeout_ms: 2000
      on_missing: "地圖路徑無效或 mobilesetting 服務未回應"
    # ... 其他步驟
```

## 注意事項

- `pattern` 中的 `*` 代表任意字元匹配（如 `loc:map_loading_set-*` 匹配任意地圖路徑）
- `timeout_ms` 設為 `null` 表示此步驟不檢查超時（通常只用於第一步）
- `on_missing` 應盡量具體，包含可操作的排查方向
- 每個流程至少準備一組正常 sample log 和一組異常 sample log 用於測試
