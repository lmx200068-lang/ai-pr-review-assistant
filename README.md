# AI PR Review 助手

AI PR Review 助手是一个基于 React + FastAPI + LLM 的 Pull Request 智能评审工具。  
系统支持输入 GitHub PR URL，自动读取 PR 元数据、changed files 和 Diff，并结合文件类型识别与 LLM 分析生成评审摘要、风险发现和修改建议。

## 核心功能

- 输入 GitHub PR URL，读取真实 PR 信息
- 展示 PR 标题、分支、文件数、增删行数
- 展示 changed files 和文本 Diff
- 根据文件类型区分审查策略：
  - 代码文件：关注逻辑、异常处理、兼容性、测试覆盖
  - 文档文件：关注说明完整性、格式规范、文档一致性
  - 依赖文件：关注版本约束、兼容性和潜在风险
- 调用 LLM 生成评审摘要和问题卡片
- 当前保持 GitHub 只读模式，不自动写回 PR 评论

## 技术栈

### Frontend

- React
- Vite
- JavaScript
- CSS

### Backend

- FastAPI
- Python
- GitHub REST API
- SiliconFlow / OpenAI-compatible LLM API

## 项目结构

```text
agent_work/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── store.py
│   ├── clients/
│   │   ├── github.py
│   │   └── llm.py
│   ├── routes/
│   │   ├── health.py
│   │   └── review_tasks.py
│   └── services/
│       ├── file_classifier.py
│       ├── github_url.py
│       ├── llm_review.py
│       ├── prompt_builder.py
│       ├── review_engine.py
│       └── task_runner.py
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
├── backend/.env.example
├── frontend/.env.example
└── README.md