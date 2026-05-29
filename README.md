# AI PR Review 助手

AI PR Review 助手是一个基于 React + FastAPI + LLM 的 Pull Request 智能评审工具。

系统支持输入 GitHub PR URL，读取 PR 元数据、changed files、Diff，并通过 Context Pack 补充文件上下文、相关文件和仓库结构摘要，再交给 LLM 生成评审摘要、正式 findings 和待人工确认项。当前 GitHub 集成保持只读模式，不会自动写回 PR 评论。

## 系统架构

```text
Frontend React
  ↓
FastAPI Review Task API
  ↓
GitHub Client
  ↓
Context Collector
  ↓
Prompt Builder
  ↓
LLM Client
  ↓
Evidence Validator
  ↓
Result UI
```

## Context Pack v1 设计

系统不是只把 Diff 扔给模型，而是构建结构化 `ReviewContextPack`：

- PR metadata
- changed files diff
- changed file hunk context
- head/base file context
- related files
- repo tree summary
- context warnings

`quick` 模式主要使用 Diff 和仓库摘要；`standard` 会补充高优先级变更文件的上下文和少量 related files；`deep` 会补充更多 head/base 内容和相关文件。

## 误报控制

- 正式 findings 必须有可校验证据。
- 证据不足的项进入 `pending_findings`，不作为正式风险。
- finding 的 `file_path` 必须来自 changed files 或 related files。
- LLM 不允许编造不存在的文件、函数、调用链或业务背景。
- 文档类变更默认不会被评为高风险，除非涉及 token/API key/security 等安全敏感说明错误。

## 响应速度控制

- review depth 分为 `quick`、`standard`、`deep`。
- Context Pack 有总字符预算，默认 `CONTEXT_MAX_TOTAL_CHARS=100000`。
- 单文件、related file 都有独立截断限制。
- lock 文件跳过或降权，避免 token 爆炸。
- related files 只做少量规则召回，不做无限递归。
- GitHub contents/tree API 失败时回退到 diff-only review，不让任务崩溃。

## 前端结构

```text
frontend/src/
  api/
    client.js
  hooks/
    useHealth.js
    useReviewTasks.js
    useReviewTaskPolling.js
  components/
    common/
    layout/
    pr/
    review/
    tasks/
  utils/
    constants.js
    formatters.js
  App.jsx
  App.css
```

`App.jsx` 只负责组合页面和少量状态衔接；API 请求集中在 `api/client.js` 和 hooks 中；展示逻辑拆到 components。

## 后端结构

```text
backend/
  main.py
  config.py
  schemas.py
  store.py
  clients/
    github.py
    llm.py
  routes/
    health.py
    review_tasks.py
  services/
    context_budgeter.py
    context_collector.py
    context_ranker.py
    diff_context.py
    file_classifier.py
    llm_review.py
    mock_data.py
    prompt_builder.py
    related_file_finder.py
    repo_tree_summarizer.py
    review_engine.py
    task_runner.py
```

## 本地运行

后端：

```bat
cd /d D:\ZhangWenchuan\agent_work
"C:\Users\ZhangWenchuan\.conda\envs\agent_env\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

前端：

```bat
cd /d D:\ZhangWenchuan\agent_work\frontend
npm install
npm run dev -- --host 127.0.0.1
```

## 关键环境变量

```env
USE_MOCK_GITHUB=false
USE_MOCK_LLM=false
LLM_FALLBACK_TO_MOCK=true

CONTEXT_ENABLE=true
CONTEXT_MAX_TOTAL_CHARS=100000
CONTEXT_MAX_FILE_CHARS=12000
CONTEXT_MAX_HUNK_CONTEXT_CHARS=16000
CONTEXT_MAX_RELATED_FILE_CHARS=6000
CONTEXT_MAX_CHANGED_FILES_DETAILED=8
CONTEXT_MAX_RELATED_FILES=6
```

## 当前限制

- 当前任务存储仍是进程内存，重启会丢失任务历史。
- GitHub 集成只读，不自动写回 PR 评论。
- related files 召回是规则版，没有向量检索。
- Context Pack 使用文本截断，不做 AST 级函数提取。
- LLM 输出仍需要结构化校验和回退保护。

## 未来扩展

- GitHub App 安装模式
- PR inline comment，但必须经过人工审查确认
- 向量检索仓库上下文
- AST 级函数提取
- 单元测试生成
- 多模型路由
- Redis/Celery 任务队列
- SQLite/PostgreSQL 持久化任务
