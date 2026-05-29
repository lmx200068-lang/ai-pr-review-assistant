export const DEFAULT_PR_URL = 'https://github.com/octocat/Hello-World/pull/1'

export const DEPTH_OPTIONS = [
  { value: 'quick', label: '快速', caption: '先看风险信号' },
  { value: 'standard', label: '标准', caption: '平衡检查' },
  { value: 'deep', label: '深入', caption: '更多检查点' },
]

export const STATUS_LABELS = {
  queued: '排队中',
  running: '评审中',
  completed: '已完成',
  failed: '失败',
}

export const FILE_TYPE_LABELS = {
  code: '代码',
  markdown: '文档',
  config: '配置',
  dependency: '依赖',
  other: '其他',
}

export const REVIEW_STRATEGY_LABELS = {
  code_reviewer: '代码审查',
  documentation_reviewer: '文档审查',
  config_reviewer: '配置审查',
  dependency_reviewer: '依赖审查',
  context_only: '仅作上下文',
}

export const DATA_SOURCE_LABELS = {
  github: 'GitHub',
  mock: '本地 mock',
}

export const REVIEW_SOURCE_LABELS = {
  llm: 'LLM 评审',
  llm_validated: 'LLM 评审，已通过证据校验',
  mock: 'Mock 演示',
  fallback: 'LLM 回退',
  local_fallback: '本地启发式 fallback',
  pending: '待开始',
  none: '无评审结果',
}

export const DEPTH_LABELS = {
  quick: '快速',
  standard: '标准',
  deep: '深入',
}

export const FILE_STATUS_LABELS = {
  added: '新增',
  modified: '修改',
  removed: '删除',
  renamed: '重命名',
  copied: '复制',
  changed: '变更',
}
