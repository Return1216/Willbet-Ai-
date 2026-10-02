# RAG_AGENT

本机可运行的 WillBet AI 助手原型：DeepSeek 负责意图路由和流式回答，Markdown/TXT 进入 Chroma 做知识检索，首版实时数据由确定性的 Mock 适配器提供。

## 启动

在 PowerShell 中执行：

```powershell
cd C:\Users\Lyy\Desktop\RAG_AGENT
# 全新环境执行一次；已有 .venv 时跳过
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

PowerShell 如果禁止执行 `Activate.ps1`，不影响运行；直接使用 `.venv\Scripts\python.exe` 即可。

在 `.env` 中填写 `DEEPSEEK_API_KEY` 和 `EMBEDDING_API_KEY`。Embedding 配置已按当前服务预填：

```text
EMBEDDING_BASE_URL=https://maas.qianwenaiapi.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIMENSION=1024
```

`.env.example` 默认使用官方 DeepSeek 地址和 `deepseek-flash`。如果使用阿里云 MaaS，请同时把 `DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL` 改成工作空间支持的值；可通过兼容接口的 `/models` 查询可用模型。

把业务知识放入 `documents/`，支持 `.md` 和 `.txt`，然后手动重建索引：

```powershell
.\.venv\Scripts\python.exe -m app.ingest
```

启动服务：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

打开 `http://127.0.0.1:8000/docs` 可以查看接口文档。

打开 `http://127.0.0.1:8000/` 可以直接使用右下角的 WillBet AI 聊天浮窗；`/docs` 仍然保留为 API 调试页面。浮窗与 API 使用同一个服务和同一个端口。

临时给外部人员体验时，可以在另一个终端建立带密码的 ngrok HTTPS 链接：

```powershell
ngrok http 8000 --basic-auth "demo:replace-with-a-strong-password"
```

把 ngrok 输出的 HTTPS 地址发给体验者即可。浏览器会先要求输入 Basic Auth 用户名和密码；电脑、uvicorn 和 ngrok 停止后链接失效。

## 接口

`POST /api/assistant/chat` 默认返回 SSE：

```powershell
curl.exe -N http://127.0.0.1:8000/api/assistant/chat `
  -H "Content-Type: application/json" `
  -d '{"question":"为什么不能提现？","session_id":"demo-001","page_context":{"page":"wallet"},"user_context":{"user_id":"demo-user-001"}}'
```

事件顺序通常是 `intent`、多个 `token`、`done`、`[DONE]`。`done` 会携带 `references`、`data_source` 和 `actions`。调试时传 `"stream":false`，直接得到最终 JSON。

知识问题的 `data_source` 是 `chroma`，实时问题首版是 `mock_platform`。未来接入真实平台时，只需替换 `app/mock_platform.py` 的适配器，接口契约保持不变。

## 测试环境部署与索引

`storage/chroma/` 是自动生成的持久化向量索引，默认不提交 Git。测试环境第一次部署时，需要先把知识库文档复制到 `documents/`，再执行一次：

下面的 `C:\path\to\RAG_AGENT` 需要替换成测试环境中的实际项目目录：

```powershell
cd C:\path\to\RAG_AGENT
python -m venv .venv
.\.venv\Scripts\python.exe -m app.ingest
```

该命令会自动扫描 `.md` 和 `.txt` 文件、切分文本、调用 Embedding API，并把结果写入 `storage/chroma/`，不需要手动切分文档。索引构建需要 `.env` 中的 `EMBEDDING_API_KEY` 和网络访问权限。

索引生成后，普通重启不需要重新构建；以下情况需要再次执行 `app.ingest`：

- 第一次部署到新的测试环境
- 新增或修改知识库文档
- 更新文档切分或平台/行业规则识别逻辑
- 修改 Embedding 服务地址、模型名或向量维度
- 删除 `storage/chroma/` 或清空测试环境持久化卷

仓库会提交 `documents/` 下的 Markdown/TXT 知识文件；`.env`、虚拟环境和自动生成的向量索引仍然不会提交。新增或修改知识文件后，在测试环境重新执行 `app.ingest` 即可。

测试环境的推荐顺序：

```powershell
git clone git@github.com:Return1216/Willbet-Ai-.git RAG_AGENT
cd RAG_AGENT
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# 编辑 .env，填写 DeepSeek、Embedding Key 和对应的 Base URL/Model
.\.venv\Scripts\python.exe -m app.ingest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 目录

```text
app/                 服务代码
frontend/            聊天浮窗页面（原生 HTML/CSS/JavaScript）
catalog/             127 个意图目录
documents/           本地 Markdown/TXT 知识
storage/chroma/      持久化索引（自动生成，不提交 Git）
tests/               单元、接口和冒烟测试
```

密钥只放在本地 `.env`，不会写入接口响应或前端代码。
