import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './App.css'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
).replace(/\/$/, '')

const DEFAULT_PR_URL = 'https://github.com/octocat/Hello-World/pull/1'

const DEPTH_OPTIONS = [
  { value: 'quick', label: '快速', caption: '先看风险信号' },
  { value: 'standard', label: '标准', caption: '平衡检查' },
  { value: 'deep', label: '深入', caption: '更多检查点' },
]

const STATUS_LABELS = {
  queued: '排队中',
  running: '评审中',
  completed: '已完成',
  failed: '失败',
}

const FILE_TYPE_LABELS = {
  code: '代码',
  markdown: '文档',
  config: '配置',
  dependency: '依赖',
  other: '其他',
}

const REVIEW_STRATEGY_LABELS = {
  code_reviewer: '代码审查',
  documentation_reviewer: '文档审查',
  config_reviewer: '配置审查',
  dependency_reviewer: '依赖审查',
  context_only: '仅作上下文',
}

const DATA_SOURCE_LABELS = {
  github: 'GitHub',
  mock: '本地 mock',
}

const REVIEW_SOURCE_LABELS = {
  llm: 'LLM',
  mock: '本地 mock',
  fallback: 'LLM 回退',
  pending: '待开始',
  none: '无评审结果',
}

const DEPTH_LABELS = {
  quick: '快速',
  standard: '标准',
  deep: '深入',
}

const FILE_STATUS_LABELS = {
  added: '新增',
  modified: '修改',
  removed: '删除',
  renamed: '重命名',
  copied: '复制',
  changed: '变更',
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail || `Request failed with ${response.status}`)
  }

  return response.json()
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(value))
}

function labelFrom(map, value, fallback = '未知') {
  return map[value] || value || fallback
}

function getReviewSource(task) {
  if (!task) {
    return 'none'
  }

  if (task.review_source) {
    return task.review_source
  }

  if (task.status === 'queued' || task.status === 'running') {
    return 'pending'
  }

  return 'none'
}

function getTaskMessage(task, reviewSource) {
  if (!task) {
    return ''
  }

  if (task.status === 'completed') {
    if (reviewSource === 'llm') {
      return 'LLM 评审已完成'
    }
    if (reviewSource === 'fallback') {
      return 'LLM 调用失败，已回退到本地 mock 评审'
    }
    if (reviewSource === 'mock') {
      return '本地 mock 评审已完成'
    }
    return '评审任务已完成'
  }

  if (task.status === 'failed') {
    return task.message || '评审任务失败'
  }

  return task.message
}

function shouldShowReviewMeta(task) {
  if (!task) {
    return false
  }

  if (task.status === 'completed' || task.status === 'failed') {
    return true
  }

  return Boolean(task.review_source)
}

function getFindingsEmptyMessage(task, isGenerating) {
  if (isGenerating) {
    return '正在生成评审发现'
  }

  if (task?.status === 'completed') {
    return '评审发现已生成'
  }

  return '本次评审没有需要展示的发现。'
}

function parsePatch(patch) {
  if (!patch) {
    return []
  }

  const rows = []
  let oldLine = null
  let newLine = null

  for (const rawLine of patch.split('\n')) {
    const hunk = rawLine.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/)

    if (hunk) {
      oldLine = Number(hunk[1])
      newLine = Number(hunk[2])
      rows.push({
        content: rawLine,
        kind: 'hunk',
        oldLine: '',
        newLine: '',
      })
      continue
    }

    if (rawLine.startsWith('+') && !rawLine.startsWith('+++')) {
      rows.push({
        content: rawLine.slice(1),
        kind: 'added',
        oldLine: '',
        newLine,
      })
      newLine += 1
      continue
    }

    if (rawLine.startsWith('-') && !rawLine.startsWith('---')) {
      rows.push({
        content: rawLine.slice(1),
        kind: 'removed',
        oldLine,
        newLine: '',
      })
      oldLine += 1
      continue
    }

    rows.push({
      content: rawLine.startsWith(' ') ? rawLine.slice(1) : rawLine,
      kind: 'context',
      oldLine,
      newLine,
    })

    if (oldLine !== null) {
      oldLine += 1
    }
    if (newLine !== null) {
      newLine += 1
    }
  }

  return rows
}

function findDiffRowIndex(rows, line) {
  const targetLine = Number(line)
  if (!Number.isFinite(targetLine) || targetLine < 1) {
    return -1
  }

  const exactIndex = rows.findIndex((row) => row.newLine === targetLine)
  if (exactIndex >= 0) {
    return exactIndex
  }

  return rows.findIndex(
    (row) => typeof row.newLine === 'number' && row.newLine >= targetLine,
  )
}

function makeDiffRowKey(filename, index) {
  return `${filename || 'unknown'}:${index}`
}

function normalizeFinding(finding) {
  return {
    ...finding,
    file_type: finding.file_type || 'other',
    review_strategy: finding.review_strategy || 'context_only',
    evidence_lines: Array.isArray(finding.evidence_lines)
      ? finding.evidence_lines.filter(Boolean)
      : [],
  }
}

function normalizeTask(task) {
  return {
    ...task,
    pr: task.pr ?? null,
    changed_files: Array.isArray(task.changed_files)
      ? task.changed_files.map((file) => ({
          ...file,
          file_type: file.file_type || 'other',
          review_strategy: file.review_strategy || 'context_only',
        }))
      : [],
    review_source: task.review_source ?? null,
    review_model: task.review_model ?? null,
    review_error: task.review_error ?? null,
    summary: task.summary ?? null,
    findings: Array.isArray(task.findings)
      ? task.findings.map(normalizeFinding)
      : [],
    pending_findings: Array.isArray(task.pending_findings)
      ? task.pending_findings.map(normalizeFinding)
      : [],
  }
}

function mergeTask(previous, next) {
  if (!previous || previous.id !== next.id) {
    return next
  }

  const nextIsTerminal = next.status === 'completed' || next.status === 'failed'

  return {
    ...previous,
    ...next,
    pr: next.pr ?? previous.pr ?? null,
    review_source: next.review_source ?? previous.review_source ?? null,
    review_model: next.review_model ?? previous.review_model ?? null,
    review_error: next.review_error ?? previous.review_error ?? null,
    changed_files:
      Array.isArray(next.changed_files) && next.changed_files.length > 0
        ? next.changed_files
        : previous.changed_files || [],
    summary: next.summary ?? previous.summary ?? null,
    findings:
      Array.isArray(next.findings) && (next.findings.length > 0 || nextIsTerminal)
        ? next.findings
        : previous.findings || [],
    pending_findings:
      Array.isArray(next.pending_findings) &&
      (next.pending_findings.length > 0 || nextIsTerminal)
        ? next.pending_findings
        : previous.pending_findings || [],
  }
}

function mergeTaskList(current, incoming) {
  const normalizedCurrent = Array.isArray(current) ? current : []
  const normalizedIncoming = Array.isArray(incoming)
    ? incoming.map(normalizeTask)
    : [normalizeTask(incoming)]
  const taskMap = new Map()

  for (const task of normalizedCurrent) {
    taskMap.set(task.id, normalizeTask(task))
  }

  for (const task of normalizedIncoming) {
    taskMap.set(task.id, mergeTask(taskMap.get(task.id), task))
  }

  return Array.from(taskMap.values()).sort(
    (left, right) => new Date(right.created_at) - new Date(left.created_at),
  )
}

function App() {
  const [prUrl, setPrUrl] = useState(DEFAULT_PR_URL)
  const [reviewDepth, setReviewDepth] = useState('standard')
  const [activeTask, setActiveTask] = useState(null)
  const [selectedFileName, setSelectedFileName] = useState('')
  const [taskHistory, setTaskHistory] = useState([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(true)
  const [apiStatus, setApiStatus] = useState('Checking')
  const [githubAccess, setGithubAccess] = useState('read_only')
  const [focusedFinding, setFocusedFinding] = useState(null)
  const [error, setError] = useState('')
  const diffRowRefs = useRef(new Map())
  const sourceReviewRef = useRef(null)

  const normalizedActiveTask = useMemo(
    () => (activeTask ? normalizeTask(activeTask) : null),
    [activeTask],
  )
  const apiStatusClass =
    apiStatus === '在线'
      ? 'online'
      : apiStatus === '离线'
        ? 'offline'
        : apiStatus.toLowerCase()
  const isReviewing =
    normalizedActiveTask?.status === 'queued' ||
    normalizedActiveTask?.status === 'running'
  const isTerminalTask =
    normalizedActiveTask?.status === 'completed' ||
    normalizedActiveTask?.status === 'failed'

  const isPrUrlValid = useMemo(() => {
    return /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/pull\/\d+\/?$/.test(
      prUrl.trim(),
    )
  }, [prUrl])

  const storeTask = useCallback((task) => {
    const normalizedTask = normalizeTask(task)

    setActiveTask((current) => mergeTask(current, normalizedTask))
    setTaskHistory((current) => mergeTaskList(current, normalizedTask))
  }, [])

  const refreshTask = useCallback(
    async (taskId) => {
      const task = await apiRequest(`/api/review-tasks/${taskId}`)
      storeTask(task)
      return task
    },
    [storeTask],
  )

  useEffect(() => {
    let cancelled = false

    async function loadInitialState() {
      try {
        const [health, tasks] = await Promise.all([
          apiRequest('/health'),
          apiRequest('/api/review-tasks'),
        ])

        if (cancelled) {
          return
        }

        const normalizedTasks = tasks.map(normalizeTask)
        setApiStatus(health.status === 'ok' ? '在线' : '未知')
        setGithubAccess(health.github_access || 'read_only')
        setTaskHistory((current) => mergeTaskList(current, normalizedTasks))
        setActiveTask((current) => current || normalizedTasks[0] || null)
      } catch (requestError) {
        if (!cancelled) {
          setApiStatus('离线')
          setError(requestError.message)
        }
      } finally {
        if (!cancelled) {
          setIsLoadingHistory(false)
        }
      }
    }

    loadInitialState()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!activeTask || !isReviewing) {
      return undefined
    }

    const timer = window.setInterval(() => {
      refreshTask(activeTask.id).catch((requestError) => {
        setError(requestError.message)
      })
    }, 900)

    return () => {
      window.clearInterval(timer)
    }
  }, [activeTask, isReviewing, refreshTask])

  async function handleSubmit(event) {
    event.preventDefault()

    if (!isPrUrlValid || isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setError('')

    try {
      const task = await apiRequest('/api/review-tasks', {
        method: 'POST',
        body: JSON.stringify({
          pr_url: prUrl.trim(),
          review_depth: reviewDepth,
        }),
      })
      storeTask(task)
      setApiStatus('在线')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  useEffect(() => {
    if (!normalizedActiveTask || normalizedActiveTask.status !== 'completed') {
      return
    }

    const hasCompleteMockDetails =
      normalizedActiveTask.pr &&
      normalizedActiveTask.changed_files.length > 0 &&
      normalizedActiveTask.summary

    if (!hasCompleteMockDetails) {
      const timer = window.setTimeout(() => {
        refreshTask(normalizedActiveTask.id).catch((requestError) => {
          setError(requestError.message)
        })
      }, 0)

      return () => window.clearTimeout(timer)
    }

    return undefined
  }, [normalizedActiveTask, refreshTask])

  const summary = normalizedActiveTask?.summary
  const pullRequest = normalizedActiveTask?.pr
  const changedFiles = normalizedActiveTask?.changed_files || []
  const findings = normalizedActiveTask?.findings || []
  const pendingFindings = normalizedActiveTask?.pending_findings || []
  const dataSource = normalizedActiveTask?.data_source || 'mock'
  const reviewSource = getReviewSource(normalizedActiveTask)
  const isGeneratingFindings = isReviewing && !isTerminalTask
  const reviewModel =
    reviewSource === 'llm' || reviewSource === 'fallback'
      ? normalizedActiveTask?.review_model || '未返回模型'
      : reviewSource === 'pending'
        ? '待开始'
        : '本地 mock'
  const reviewError = normalizedActiveTask?.review_error || ''
  const taskMessage = getTaskMessage(normalizedActiveTask, reviewSource)
  const githubAccessLabel = githubAccess === 'read_only' ? '只读' : '未知'
  const findingsEmptyMessage = getFindingsEmptyMessage(
    normalizedActiveTask,
    isGeneratingFindings,
  )
  const selectedFile =
    changedFiles.find((file) => file.filename === selectedFileName) ||
    changedFiles[0] ||
    null
  const selectedPatchRows = useMemo(
    () => (selectedFile ? parsePatch(selectedFile.patch) : []),
    [selectedFile],
  )
  const focusedDiffRowIndex = useMemo(() => {
    if (!focusedFinding || !selectedFile) {
      return -1
    }
    if (focusedFinding.file_path !== selectedFile.filename) {
      return -1
    }
    return findDiffRowIndex(selectedPatchRows, focusedFinding.line)
  }, [focusedFinding, selectedFile, selectedPatchRows])

  const handleFindingSelect = useCallback((finding) => {
    setFocusedFinding({
      id: finding.id,
      file_path: finding.file_path,
      line: finding.line,
    })
    setSelectedFileName(finding.file_path)
  }, [])

  const handleFindingKeyDown = useCallback(
    (event, finding) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        handleFindingSelect(finding)
      }
    },
    [handleFindingSelect],
  )

  useEffect(() => {
    if (!selectedFile || focusedDiffRowIndex < 0) {
      return
    }

    const rowKey = makeDiffRowKey(selectedFile.filename, focusedDiffRowIndex)
    const row = diffRowRefs.current.get(rowKey)
    sourceReviewRef.current?.scrollIntoView({
      block: 'start',
      behavior: 'smooth',
    })
    row?.scrollIntoView({
      block: 'center',
      behavior: 'smooth',
    })
  }, [focusedDiffRowIndex, selectedFile])

  function renderFindingCard(finding, isPending = false) {
    const isFocused = focusedFinding?.id === finding.id
    const cardClass = [
      'finding-card',
      isPending ? 'pending' : '',
      isFocused ? 'selected' : '',
    ]
      .filter(Boolean)
      .join(' ')

    return (
      <article
        className={cardClass}
        key={finding.id}
        onClick={() => handleFindingSelect(finding)}
        onKeyDown={(event) => handleFindingKeyDown(event, finding)}
        role="button"
        tabIndex={0}
      >
        <div className="finding-card-header">
          <span className={`severity ${finding.severity}`}>
            {finding.severity}
          </span>
          <span>{FILE_TYPE_LABELS[finding.file_type] || finding.file_type}</span>
          <span>
            {REVIEW_STRATEGY_LABELS[finding.review_strategy] ||
              finding.review_strategy}
          </span>
          <span className="finding-path" translate="no">
            {finding.file_path}:{finding.line}
          </span>
        </div>
        <h3>{finding.title}</h3>
        {isPending ? (
          <span className="pending-badge">待人工确认</span>
        ) : null}
        <div className="finding-section">
          <strong>问题说明</strong>
          <p>{finding.summary}</p>
        </div>
        <div className="evidence-block">
          <strong>证据片段</strong>
          {finding.evidence_lines.length ? (
            <pre translate="no">
              {finding.evidence_lines.map((line, index) => (
                <code key={`${finding.id}-evidence-${index}`}>{line}</code>
              ))}
            </pre>
          ) : (
            <span>LLM 未提供可校验的 diff 行，需要人工确认。</span>
          )}
        </div>
        <div className="suggestion">
          <strong>修改建议</strong>
          <span>{finding.suggestion}</span>
        </div>
      </article>
    )
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">V0.3 LLM 评审循环</p>
          <h1>AI PR Review 助手</h1>
        </div>
        <div className={`api-pill ${apiStatusClass}`}>
          <span>API</span>
          <strong>{apiStatus}</strong>
        </div>
      </header>

      {error ? (
        <div className="error-banner" role="alert">
          {error}
        </div>
      ) : null}

      <section className="workspace" aria-label="PR 评审工作台">
        <form className="tool-panel input-panel" onSubmit={handleSubmit}>
          <div className="panel-heading">
            <p className="eyebrow">评审目标</p>
            <h2>创建任务</h2>
          </div>

          <label className="field">
            <span>GitHub PR URL</span>
            <input
              value={prUrl}
              onChange={(event) => setPrUrl(event.target.value)}
              placeholder={DEFAULT_PR_URL}
              spellCheck="false"
            />
          </label>

          <fieldset className="depth-control">
            <legend>评审深度</legend>
            <div className="segments">
              {DEPTH_OPTIONS.map((option) => (
                <button
                  className={reviewDepth === option.value ? 'active' : ''}
                  key={option.value}
                  onClick={() => setReviewDepth(option.value)}
                  type="button"
                >
                  <span>{option.label}</span>
                  <small>{option.caption}</small>
                </button>
              ))}
            </div>
          </fieldset>

          <button
            className="primary-action"
            disabled={!isPrUrlValid || isSubmitting}
            type="submit"
          >
            {isSubmitting ? '正在创建任务' : '开始 AI 评审'}
          </button>

          <div className="mock-note">
            <strong>GitHub {githubAccessLabel}测试</strong>
            <span>
              只读取 PR 元数据、changed files 和 Diff；不会自动写回 GitHub
              评论，写回评论需要人工审查。
            </span>
          </div>
        </form>

        <section className="tool-panel status-panel">
          <div className="panel-heading">
            <p className="eyebrow">当前任务</p>
            <h2>
              {normalizedActiveTask
                ? STATUS_LABELS[normalizedActiveTask.status] ||
                  normalizedActiveTask.status
                : '暂无任务'}
            </h2>
          </div>

          {normalizedActiveTask ? (
            <>
              <div className="progress-row">
                <div className="progress-track" aria-hidden="true">
                  <span style={{ width: `${normalizedActiveTask.progress}%` }} />
                </div>
                <strong>{normalizedActiveTask.progress}%</strong>
              </div>

              <dl className="task-facts">
                <div>
                  <dt>Task ID</dt>
                  <dd>{normalizedActiveTask.id}</dd>
                </div>
                <div>
                  <dt>深度</dt>
                  <dd>{labelFrom(DEPTH_LABELS, normalizedActiveTask.review_depth)}</dd>
                </div>
                <div>
                  <dt>数据源</dt>
                  <dd>{labelFrom(DATA_SOURCE_LABELS, dataSource)}</dd>
                </div>
                <div>
                  <dt>Review 来源</dt>
                  <dd>{labelFrom(REVIEW_SOURCE_LABELS, reviewSource)}</dd>
                </div>
              </dl>

              <p className="task-message">{taskMessage}</p>

              {pullRequest ? (
                <div className="pr-snapshot">
                  <div>
                    <span className="repo-name">
                      {pullRequest.owner}/{pullRequest.repo}
                    </span>
                    <strong>#{pullRequest.number}</strong>
                  </div>
                  <h3>{pullRequest.title}</h3>
                  <div className="branch-line">
                    <span translate="no">{pullRequest.source_branch}</span>
                    <span aria-hidden="true">到</span>
                    <span translate="no">{pullRequest.target_branch}</span>
                  </div>
                  <div className="diff-stats">
                    <span>+{pullRequest.additions}</span>
                    <span>-{pullRequest.deletions}</span>
                    <span>{pullRequest.changed_files} 个文件</span>
                  </div>
                </div>
              ) : (
                <div className="empty-state">正在同步 GitHub PR 元数据</div>
              )}
            </>
          ) : (
            <div className="empty-state">
              输入 PR URL 后即可开始一次 AI 评审。
            </div>
          )}
        </section>

        <aside className="tool-panel history-panel">
          <div className="panel-heading">
            <p className="eyebrow">最近任务</p>
            <h2>任务队列</h2>
          </div>

          {isLoadingHistory ? (
            <div className="empty-state">正在加载任务</div>
          ) : taskHistory.length ? (
            <div className="task-list">
              {taskHistory.slice(0, 5).map((task) => (
                <button
                  className={
                    normalizedActiveTask?.id === task.id ? 'selected' : ''
                  }
                  key={task.id}
                  onClick={() => storeTask(task)}
                  type="button"
                >
                  <span className={`status-dot ${task.status}`} />
                  <span>
                    <strong>{STATUS_LABELS[task.status]}</strong>
                    <small>{formatDate(task.created_at)}</small>
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <div className="empty-state">暂无任务</div>
          )}
        </aside>

        <section className="tool-panel findings-panel">
          <div className="panel-heading">
            <p className="eyebrow">评审输出</p>
            <h2>
              {findings.length
                ? `${findings.length} 条发现`
                : pendingFindings.length
                  ? '0 条正式发现'
                  : '评审结果'}
            </h2>
          </div>

          {summary ? (
            <div className="summary-strip">
              <div>
                <span>评分</span>
                <strong>{summary.score}</strong>
              </div>
              <div>
                <span>检查项</span>
                <strong>
                  {summary.checks_passed}/{summary.checks_total}
                </strong>
              </div>
              <div>
                <span>评审耗时</span>
                <strong>{summary.estimated_review_minutes} 分钟</strong>
              </div>
            </div>
          ) : null}

          {summary ? <p className="verdict">{summary.verdict}</p> : null}

          {shouldShowReviewMeta(normalizedActiveTask) ? (
            <div className={`review-meta ${reviewSource}`}>
              <span>Review 来源：{labelFrom(REVIEW_SOURCE_LABELS, reviewSource)}</span>
              <span translate="no">模型：{reviewModel}</span>
            </div>
          ) : null}

          {reviewError ? (
            <div className="review-warning" role="status">
              <strong>LLM 回退详情</strong>
              <span>{reviewError}</span>
            </div>
          ) : null}

          {changedFiles.length ? (
            <section
              className="source-review"
              ref={sourceReviewRef}
              aria-label="变更源码"
            >
              <div className="changed-files-header">
                <h3>PR 变更文件</h3>
                <span>已加载 {changedFiles.length} 个文件</span>
              </div>

              <div className="source-layout">
                <div className="changed-file-list" aria-label="变更文件">
                  {changedFiles.map((file) => (
                    <button
                      className={
                        selectedFile?.filename === file.filename
                          ? 'changed-file selected'
                          : 'changed-file'
                      }
                      key={file.filename}
                      onClick={() => setSelectedFileName(file.filename)}
                      type="button"
                    >
                      <span>
                        <strong translate="no">{file.filename}</strong>
                        <small>
                          {labelFrom(FILE_STATUS_LABELS, file.status)} ·{' '}
                          {FILE_TYPE_LABELS[file.file_type] || file.file_type} ·{' '}
                          {REVIEW_STRATEGY_LABELS[file.review_strategy] ||
                            file.review_strategy}
                        </small>
                      </span>
                      <span className="file-stats">
                        <span>+{file.additions}</span>
                        <span>-{file.deletions}</span>
                        <span>{file.changes} 处变更</span>
                      </span>
                    </button>
                  ))}
                </div>

                <div className="diff-viewer">
                  {selectedFile ? (
                    <>
                      <div className="diff-toolbar">
                        <div>
                          <strong translate="no">{selectedFile.filename}</strong>
                          <small>
                            {labelFrom(FILE_STATUS_LABELS, selectedFile.status)} ·{' '}
                            {FILE_TYPE_LABELS[selectedFile.file_type] ||
                              selectedFile.file_type}{' '}
                            ·{' '}
                            {REVIEW_STRATEGY_LABELS[
                              selectedFile.review_strategy
                            ] || selectedFile.review_strategy}
                          </small>
                        </div>
                        <span>
                          +{selectedFile.additions} -{selectedFile.deletions}
                        </span>
                      </div>

                      {selectedPatchRows.length ? (
                        <div className="diff-table" translate="no">
                          {selectedPatchRows.map((row, index) => {
                            const rowKey = makeDiffRowKey(
                              selectedFile.filename,
                              index,
                            )
                            const isFocused = index === focusedDiffRowIndex

                            return (
                              <div
                                className={`diff-row ${row.kind}${
                                  isFocused ? ' focused' : ''
                                }`}
                                key={`${row.kind}-${index}-${row.oldLine}-${row.newLine}`}
                                ref={(node) => {
                                  if (node) {
                                    diffRowRefs.current.set(rowKey, node)
                                  } else {
                                    diffRowRefs.current.delete(rowKey)
                                  }
                                }}
                              >
                                <span className="line-number">{row.oldLine}</span>
                                <span className="line-number">{row.newLine}</span>
                                <code>{row.content || ' '}</code>
                              </div>
                            )
                          })}
                        </div>
                      ) : (
                        <div className="empty-state">
                          GitHub 没有返回这个文件的文本 diff。
                        </div>
                      )}

                      {selectedFile.patch_truncated ? (
                        <p className="patch-note">
                          diff 预览在评审前已截断。
                        </p>
                      ) : null}
                    </>
                  ) : (
                    <div className="empty-state">未选择变更文件。</div>
                  )}
                </div>
              </div>
            </section>
          ) : null}

          {findings.length ? (
            <div className="finding-list">
              {findings.map((finding) => renderFindingCard(finding))}
            </div>
          ) : (
            <div className="empty-state">
              {findingsEmptyMessage}
            </div>
          )}

          {pendingFindings.length ? (
            <section className="confirmation-section">
              <div className="changed-files-header">
                <h3>待人工确认</h3>
                <span>{pendingFindings.length} 条需要复核</span>
              </div>
              <p>
                这些项没有可校验的 Diff 证据，不作为正式 finding，需要人工查看后再决定是否处理。
              </p>
              <div className="finding-list pending-list">
                {pendingFindings.map((finding) =>
                  renderFindingCard(finding, true),
                )}
              </div>
            </section>
          ) : null}
        </section>
      </section>
    </main>
  )
}

export default App
