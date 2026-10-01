# RAG_AGENT 设计说明

日期：2026-10-01
状态：已确认，流式输出版

## 目标

在 Windows 本机创建一个独立的 Python RAG 服务，替代当前 RAGFlow 的基础问答能力。首版面向 WillBet AI 原型，支持本地 Markdown/TXT 文档检索、意图路由、平台实时数据 Mock，以及供前端调用的 FastAPI 接口。

首版不依赖 RAGFlow，也不实现真实平台业务接口；真实平台接口将在后续替换 Mock 适配器时接入。

## 已确认约束

- 首版运行方式：本机运行。
- 知识来源：`documents/` 下的 Markdown/TXT 文件。
- 文档索引：手动执行命令重建。
- 生成模型：DeepSeek API。
- Embedding：OpenAI 兼容接口。
  - Base URL：`https://maas.qianwenaiapi.com/compatible-mode/v1`
  - Model：`text-embedding-v3`
  - Dimension：`1024`
- 向量库：本地持久化 Chroma。
- 意图目录：现有 WillBet AI Intent Tree V1，共 127 个意图。
- 实时数据：首版为全意图 Mock 适配器，后续替换为平台 API。
- 前端接口：新建 `POST /api/assistant/chat`，不兼容 RAGFlow 原接口。
- Rerank：首版暂不调用，保留独立接口和配置位置。
- 首版响应：SSE 流式输出，最终事件携带完整元数据。

## 系统流程

```text
前端
  -> POST /api/assistant/chat
  -> 读取会话、页面上下文和用户上下文
  -> DeepSeek 输出结构化意图
  -> 校验 intent_id 和置信度
  -> 实时意图：调用 Mock Platform Adapter
  -> 知识意图：Embedding 查询 + Chroma Top-K
  -> DeepSeek 根据验证数据或检索片段生成答案
  -> 通过 SSE 逐段返回答案，结束事件返回来源、意图和操作入口
```

## API 契约

请求：

```json
{
  "question": "为什么不能提现？",
  "session_id": "session-demo-001",
  "page_context": {
    "page": "wallet",
    "module": "withdrawal"
  },
  "user_context": {
    "user_id": "demo-user-001"
  }
}
```

响应：

```json
{
  "session_id": "session-demo-001",
  "intent": {
    "id": "wallet.withdrawal.requirements.01",
    "confidence": 0.94,
    "need_realtime_data": true
  },
  "answer": "你还需要完成 45 USDT 的有效流水。",
  "references": [],
  "data_source": "mock_platform",
  "actions": [
    {
      "label": "查看流水详情",
      "type": "navigate",
      "target": "/turnover"
    }
  ]
}
```

## 流式输出

`POST /api/assistant/chat` 默认返回 `text/event-stream`。每个事件使用 SSE 的 `data:` 行承载 JSON：

```text
data: {"type":"intent","intent":{"id":"wallet.withdrawal.status.01","confidence":0.92}}

data: {"type":"token","content":"你的提现"}

data: {"type":"token","content":"正在处理中。"}

data: {"type":"done","session_id":"session-demo-001","references":[],"data_source":"mock_platform","actions":[]}

data: [DONE]
```

事件类型固定为：

- `intent`：路由完成后发送一次；置信度过低时发送 `clarification` 并结束。
- `token`：答案生成过程中的增量文本。
- `done`：发送完整元数据，包括 `session_id`、`references`、`data_source` 和 `actions`。
- `error`：发送可展示的错误信息，然后关闭连接。

客户端必须支持断开连接；服务端在客户端断开时停止后续模型生成，避免无效调用。非流式调试可通过请求参数 `stream=false` 返回同一套最终 JSON。
## 意图路由

路由器读取 `intent-tree-v1.json` 中的意图 ID、名称、示例和实时数据标记。DeepSeek 只允许返回目录中存在的 ID，并使用 JSON 输出模式。

- `confidence >= 0.75`：继续处理。
- `confidence < 0.75`：返回澄清响应，不调用实时数据。
- 不存在的 ID：视为路由错误，进入 `global.fallback`。

## RAG 检索

1. 扫描 `documents/` 下的 `.md` 和 `.txt` 文件。
2. 按标题、段落和固定长度切分，保留文件名和段落序号。
3. 调用 Embedding API 生成 1024 维向量。
4. 写入 Chroma 持久化集合。
5. 查询时生成问题向量，召回 Top 20。
6. 首版直接按向量相似度取前 5 条上下文。
7. 后续将 Top 20 交给 Rerank，再取 Top 5。

## 实时数据 Mock

`Mock Platform Adapter` 根据意图 ID 返回稳定、可重复的测试数据。首版覆盖意图树全部意图；数据源字段始终标记为 `mock_platform`，避免把测试数据误认为生产数据。

后续接入真实平台时，只替换适配器实现，保持意图路由、API 契约和答案生成流程不变。

## 配置和安全

密钥只放在本地 `.env`，不写入前端、JSON 意图目录或 Git：

```text
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://maas.qianwenaiapi.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIMENSION=1024
```

## 首版目录

```text
RAG_AGENT/
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ chat.py
│  ├─ router.py
│  ├─ rag.py
│  ├─ ingest.py
│  └─ mock_platform.py
├─ catalog/
│  └─ intent-tree-v1.json
├─ documents/
├─ storage/
│  └─ chroma/
├─ tests/
├─ .env.example
├─ requirements.txt
└─ README.md
```

## 验证标准

- 能通过命令完成 Markdown/TXT 索引构建。
- Chroma 索引重启后仍可复用。
- `/api/assistant/chat` 默认能返回合法 SSE 事件流；`stream=false` 能返回合法 JSON。
- 意图 ID 始终来自意图目录。
- 低置信度问题不会触发 Mock 实时数据。
- 知识问题返回至少一个文件来源或明确说明未找到依据。
- 实时问题明确标记 `mock_platform`。
- 不把 API Key 返回给前端。

## 暂不实现

- Rerank 实际调用。

- 真实平台业务 API。
- 自动监听文档目录。
- PDF、Word、图片和 OCR 解析。
- 多用户鉴权和生产部署。
