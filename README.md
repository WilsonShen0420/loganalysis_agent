# AUMOBO LogDiag — Log-Based Diagnostic AI Service

LogDiag 是 AUMOBO 系統的 log 診斷 AI 服務，以 ROS Noetic node 實作。使用者透過自然語言描述問題，系統自動查詢 log、比對 Golden Path 基線、輸出結構化診斷報告。

## 快速開始

### 前置需求

- ROS Noetic (Ubuntu 20.04)
- Python 3.8+
- 雲端模式需擇一設定: `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GOOGLE_API_KEY`
- 地端模式: Ollama + Qwen2.5-7B-Instruct

### 安裝

```bash
# 1. 將此 package 放入 catkin workspace
cd ~/catkin_ws/src
ln -s /path/to/loganalysis_agent .

# 2. 安裝 Python 依賴
pip install -r loganalysis_agent/requirements.txt

# 3. Build
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

### 啟動

```bash
# Claude API
export ANTHROPIC_API_KEY="your-api-key"
roslaunch loganalysis_agent logdiag.launch llm_backend:=claude

# OpenAI ChatGPT
export OPENAI_API_KEY="your-api-key"
roslaunch loganalysis_agent logdiag.launch llm_backend:=openai

# Google Gemini
export GOOGLE_API_KEY="your-api-key"
roslaunch loganalysis_agent logdiag.launch llm_backend:=gemini

# 地端模式 (Ollama)
roslaunch loganalysis_agent logdiag.launch llm_backend:=local
```

## 使用方式

### 方式 1: Topic

```bash
# 發送查詢
rostopic pub /logdiag/query std_msgs/String "data: '昨天下午 SLAM 建圖失敗了，幫我看看'"

# 監聽結果
rostopic echo /logdiag/result
```

### 方式 2: Service

```bash
rosservice call /logdiag/diagnose "{query: '定位載圖一直失敗', session_id: ''}"
```

### 方式 3: 多輪對話

Service 模式支援多輪對話，首次呼叫取得 `session_id`，後續使用同一 ID 追問：

```bash
# 第一次
rosservice call /logdiag/diagnose "{query: '系統不正常', session_id: ''}"
# 回傳 session_id: "abc-123-..."

# 追問
rosservice call /logdiag/diagnose "{query: '幫我再看看 sensor 的 log', session_id: 'abc-123-...'}"
```

## 地端 LLM 部署 (Ollama + Qwen2.5-7B-Instruct)

### 安裝 Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 拉取模型

```bash
# 標準版 (~4.7GB)
ollama pull qwen2.5:7b-instruct

# 4-bit 量化版 (VRAM 不足時, ~4.4GB)
ollama pull qwen2.5:7b-instruct-q4_K_M
```

### 驗證

```bash
ollama run qwen2.5:7b-instruct "Hello, 你好嗎?"
```

### 硬體需求

| 配置 | 最低 | 建議 |
|------|------|------|
| GPU | 無 (CPU 可跑，較慢) | NVIDIA ≥8GB VRAM |
| RAM | 16GB | 32GB |
| 磁碟 | 10GB | SSD |

## 參數設定

參數定義在 `config/logdiag_params.yaml`，可透過 launch 檔覆蓋：

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `logdiag/llm_backend` | `claude` | LLM 後端: `claude` / `openai` / `gemini` / `local` |
| `logdiag/claude/model` | `claude-sonnet-4-20250514` | Claude 模型 |
| `logdiag/openai/model` | `gpt-4o` | OpenAI 模型 |
| `logdiag/gemini/model` | `gemini-2.0-flash` | Gemini 模型 |
| `logdiag/local/model` | `qwen2.5:7b-instruct` | 地端模型 |
| `logdiag/max_tool_calls` | `10` | 單次診斷最大 tool 調用次數 |

## 測試

```bash
cd loganalysis_agent
PYTHONPATH=src:$PYTHONPATH python -m pytest test/ -v
```

## 文件

- [Golden Path 撰寫指南](docs/log_diagnosis/golden_path_guide.md)
- [產品需求規格書 (PRD)](docs/AUMOBO_LogDiag_PRD.docx)
