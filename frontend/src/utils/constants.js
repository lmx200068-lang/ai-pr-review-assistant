export const DEFAULT_PR_URL = 'https://github.com/octocat/Hello-World/pull/1'

export const DEPTH_OPTIONS = [
  { value: 'quick', label: 'Quick', caption: 'Risk scan' },
  { value: 'standard', label: 'Standard', caption: 'Balanced review' },
  { value: 'deep', label: 'Deep', caption: 'More context' },
]

export const STATUS_LABELS = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
}

export const FILE_TYPE_LABELS = {
  code: 'Code',
  markdown: 'Docs',
  config: 'Config',
  dependency: 'Dependency',
  other: 'Other',
}

export const REVIEW_STRATEGY_LABELS = {
  code_reviewer: 'Code review',
  documentation_reviewer: 'Documentation review',
  config_reviewer: 'Config review',
  dependency_reviewer: 'Dependency review',
  context_only: 'Context only',
}

export const DATA_SOURCE_LABELS = {
  github: 'GitHub',
  mock: 'Local mock',
}

export const REVIEW_SOURCE_LABELS = {
  llm: 'LLM Review',
  llm_validated: 'LLM Review, evidence validated',
  mock: 'Mock Demo',
  fallback: 'Local Fallback',
  local_fallback: 'Local Fallback',
  pending: 'Pending',
  none: 'No review result',
}

export const DEPTH_LABELS = {
  quick: 'Quick',
  standard: 'Standard',
  deep: 'Deep',
}

export const FILE_STATUS_LABELS = {
  added: 'Added',
  modified: 'Modified',
  removed: 'Removed',
  renamed: 'Renamed',
  copied: 'Copied',
  changed: 'Changed',
}
