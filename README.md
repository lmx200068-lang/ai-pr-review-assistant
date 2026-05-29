# AI PR Review 助手

## 项目简介

AI PR Review 助手是一个基于 React + FastAPI + LLM 的 Pull Request 智能评审工作台。

它支持输入 GitHub PR URL，读取 PR 元数据、changed files 和 Diff，并通过 Context Pack 补充 hunk 附近上下文、head/base 文件内容、related files 和仓库结构摘要，再交给 LLM 生成评审摘要、正式 Findings 和待人工确认项。

本项目的重点不是简单调用 LLM，而是围绕真实 PR Review 场景实现一个更可靠的闭环：Context Pack、Evidence Validation、正式 Findings / Pending Findings 分流、GitHub 只读安全模式和前端任务化展示。

## 项目亮点

- **Context Pack Review**：不只看 Diff，而是补充 PR metadata、hunk context、head/base context、related files 和 repo tree summary。
- **Evidence Validation**：正式 Findings 必须能在 Diff 或上下文中找到证据，避免 LLM 编造结论。
- **Pending Findings 分流**：证据不足、上下文不足或 fallback 产生的启发式建议不会被展示为正式风险。
- **GitHub 只读安全模式**：当前只读取 PR 信息，不自动写回 GitHub 评论，避免制造垃圾评论。
- **文件类型审查策略**：code、markdown、config、dependency 使用不同 reviewer 策略，README/docs 不按代码逻辑审查。
- **LLM 容错与 fallback**：对 LLM JSON 输出做 normalize 和 schema validation；LLM 失败时只生成本地待确认建议。
- **前端任务化工作台**：支持任务创建、进度展示、历史任务、PR 信息、Diff、Context Summary、Findings 和 Pending Findings 展示。

## 运行效果示例

一次典型评审流程：

1. 用户输入 GitHub PR URL。
2. 后端读取 PR metadata 和 changed files。
3. Context Collector 构建 Context Pack。
4. Prompt Builder 将结构化上下文交给 LLM。
5. Evidence Validator 校验 LLM 输出中的证据。
6. 前端展示 PR 概览、Context Pack 摘要、Diff、正式 Findings 和待确认建议。

页面上可以看到：

- PR 标题、分支、文件数、增删行数
- PR 变更文件和文本 Diff
- Context Pack 是否开启、预算使用量、截断/跳过文件和 warnings
- Review 来源：LLM / Mock 演示 / 本地启发式 fallback
- 正式发现数量与待确认建议数量
- 每条 Finding 的严重程度、文件类型、审查策略、文件路径、证据片段和修改建议

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

## 核心实现闭环

```text
Create Review Task
  ↓
Parse GitHub PR URL
  ↓
Fetch PR metadata and changed files
  ↓
Classify file_type and review_strategy
  ↓
Build Context Pack
  ↓
Run LLM Review
  ↓
Normalize and validate LLM JSON
  ↓
Evidence validation
  ↓
Split findings / pending_findings
  ↓
Render review workbench
```

核心原则：

- 可以失败的外部调用不应直接拖垮任务。
- LLM 输出必须经过结构化校验。
- 没有证据的问题不能进入正式 Findings。
- GitHub 写回必须留给未来的人审确认流程。

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

Context Pack 还会记录：

- `used_chars`
- `max_chars`
- `truncated_files`
- `skipped_files`
- `warnings`

这样前端可以解释为什么某些文件没有被完整送入模型。

## Review 结果结构

当前任务结果保留前端可直接展示的轻量结构：

```json
{
  "status": "completed",
  "progress": 100,
  "review_source": "llm",
  "pr": {},
  "changed_files": [],
  "context_summary": {
    "enabled": true,
    "changed_context_files": 2,
    "related_files": 1,
    "repo_tree_loaded": true,
    "used_chars": 58231,
    "max_chars": 100000,
    "truncated_files": [],
    "skipped_files": [],
    "warnings": []
  },
  "summary": {},
  "findings": [],
  "pending_findings": []
}
```

`findings` 表示已经通过证据校验的正式风险；`pending_findings` 表示证据不足、上下文不足或 local fallback 产生的待人工确认建议。

## 误报控制

- 正式 Findings 必须有可校验证据。
- 证据不足的项进入 `pending_findings`，不作为正式风险。
- Finding 的 `file_path` 必须来自 changed files 或 related files。
- LLM 不允许编造不存在的文件、函数、调用链或业务背景。
- 文档类变更默认不会被评为高风险，除非涉及 token/API key/security 等安全敏感说明错误。
- LLM 失败时返回 `local_fallback`，只生成 pending suggestions，不生成正式 Findings。

## 响应速度控制

- review depth 分为 `quick`、`standard`、`deep`。
- Context Pack 有总字符预算，默认 `CONTEXT_MAX_TOTAL_CHARS=100000`。
- hunk context 优先级高于完整 head/base 文件上下文。
- 单文件、hunk context、related file 都有独立截断限制。
- lock 文件跳过或降权，避免 token 爆炸。
- related files 只做少量规则召回，不做无限递归。
- GitHub contents/tree API 失败时回退到 diff-only review，不让任务崩溃。

## 模型选择说明

当前后端通过 OpenAI-compatible Chat Completions API 调用 LLM，因此可以接入支持该协议的模型服务。

建议优先选择：

- 支持较长上下文窗口的模型，因为 Context Pack 会包含 Diff、hunk context 和 related files。
- JSON 输出稳定的模型，因为后端需要对 `summary`、`findings`、`pending_findings` 做结构化校验。
- 中文表达能力较好的模型，因为前端展示以中文为主。

工程上保留了以下保护：

- `USE_MOCK_LLM=true` 可用于离线演示和前端联调。
- `LLM_FALLBACK_TO_MOCK=true` 可避免 LLM API 异常直接中断任务。
- local fallback 只进入 `pending_findings`，不会被当成正式 AI Review 结果。

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
cd /d path\to\agent_work
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

也可以进入后端目录启动：

```bat
cd /d path\to\agent_work\backend
python -m uvicorn main:app --reload
```

前端：

```bat
cd /d path\to\agent_work\frontend
npm install
npm run dev -- --host 127.0.0.1
```

## 关键环境变量

请从示例文件复制本地配置，并不要提交真实密钥。

```env
GITHUB_TOKEN=your_github_token_here
USE_MOCK_GITHUB=false

LLM_API_KEY=your_llm_api_key_here
LLM_MODEL=your_model_name_here
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

## 安全说明

- 当前 GitHub 集成为只读模式，只读取 PR metadata、changed files、Diff、contents 和 repo tree。
- 系统不会自动向 GitHub 写 PR comment、inline comment 或 review。
- README 和示例配置中只使用占位符，不包含真实 API Key 或 token。
- `.env` 文件应只保存在本地，不应提交到 Git。
- LLM 输出不会直接被当成事实，必须经过 schema validation 和 evidence validation。
- local fallback 只用于流程演示和人工复核提示，不作为正式风险结论。

## 当前版本：v0.4 Context Pack Review Loop

v0.4 的核心目标是从 diff-only review 升级为 Context Pack review。

当前版本已经实现：

- GitHub PR 只读获取
- 文件类型与 review strategy 分类
- Context Pack 构建
- repo tree summary
- hunk context 截取
- related files 规则召回
- LLM JSON normalize
- Evidence Validation
- 正式 Findings / Pending Findings 分流
- local fallback pending suggestions
- 前端任务化 Review Workbench

## 当前限制

- 当前任务存储仍是进程内存，重启会丢失任务历史。
- GitHub 集成只读，不自动写回 PR 评论。
- related files 召回是规则版，没有向量检索。
- Context Pack 使用文本截断，不做 AST 级函数提取。
- LLM 输出仍需要结构化校验和回退保护。
- 目前没有数据库、Redis/Celery 或后台任务队列。

## 设计取舍

- **先做只读，不做写回**：优先保证安全和可解释，避免自动生成低质量 PR 评论。
- **先做规则召回，不接向量库**：用更少依赖验证 Context Pack 闭环，降低项目复杂度。
- **先做证据校验，不追求全自动结论**：宁可把不确定项放入 Pending Findings，也不把猜测当正式风险。
- **保留 mock 模式**：方便前端联调、离线演示和回归测试。
- **前端展示上下文预算**：让用户知道模型到底看到了多少内容，而不是黑盒评审。

## 未来扩展

- GitHub App 安装模式
- PR inline comment，但必须经过人工审查确认
- 向量检索仓库上下文
- AST 级函数提取
- 单元测试生成
- 多模型路由
- Redis/Celery 任务队列
- SQLite/PostgreSQL 持久化任务
