export function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(value))
}

export function labelFrom(map, value, fallback = '未知') {
  return map[value] || value || fallback
}

export function isTerminalTask(task) {
  return task?.status === 'completed' || task?.status === 'failed'
}

export function isReviewingTask(task) {
  return task?.status === 'queued' || task?.status === 'running'
}

export function getReviewSource(task) {
  if (!task) {
    return 'none'
  }
  if (task.review_source) {
    return task.review_source
  }
  if (isReviewingTask(task)) {
    return 'pending'
  }
  return 'none'
}

export function getTaskMessage(task, reviewSource) {
  if (!task) {
    return ''
  }
  if (task.status === 'completed') {
    if (reviewSource === 'llm' || reviewSource === 'llm_validated') {
      return 'LLM 评审已完成'
    }
    if (reviewSource === 'local_fallback' || reviewSource === 'fallback') {
      return 'LLM 评审失败，已生成本地启发式待确认建议'
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

export function shouldShowReviewMeta(task) {
  if (!task) {
    return false
  }
  return isTerminalTask(task) || Boolean(task.review_source)
}

export function getFindingsEmptyMessage(task, isGenerating) {
  if (isGenerating) {
    return '正在生成评审发现'
  }
  if (task?.status === 'completed') {
    return '评审发现已生成'
  }
  return '本次评审没有需要展示的发现。'
}

export function normalizeFinding(finding) {
  return {
    ...finding,
    file_type: finding.file_type || 'other',
    review_strategy: finding.review_strategy || 'context_only',
    line: finding.line || null,
    evidence_lines: Array.isArray(finding.evidence_lines)
      ? finding.evidence_lines.filter(Boolean)
      : [],
  }
}

export function normalizeTask(task) {
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
    context_summary: task.context_summary ?? null,
    summary: task.summary ?? null,
    findings: Array.isArray(task.findings)
      ? task.findings.map(normalizeFinding)
      : [],
    pending_findings: Array.isArray(task.pending_findings)
      ? task.pending_findings.map(normalizeFinding)
      : [],
  }
}

export function mergeTask(previous, next) {
  if (!previous || previous.id !== next.id) {
    return next
  }

  const nextIsTerminal = isTerminalTask(next)
  return {
    ...previous,
    ...next,
    pr: next.pr ?? previous.pr ?? null,
    review_source: next.review_source ?? previous.review_source ?? null,
    review_model: next.review_model ?? previous.review_model ?? null,
    review_error: next.review_error ?? previous.review_error ?? null,
    context_summary: next.context_summary ?? previous.context_summary ?? null,
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

export function mergeTaskList(current, incoming) {
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

export function parsePatch(patch) {
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
      rows.push({ content: rawLine, kind: 'hunk', oldLine: '', newLine: '' })
      continue
    }
    if (rawLine.startsWith('+') && !rawLine.startsWith('+++')) {
      rows.push({ content: rawLine.slice(1), kind: 'added', oldLine: '', newLine })
      newLine += 1
      continue
    }
    if (rawLine.startsWith('-') && !rawLine.startsWith('---')) {
      rows.push({ content: rawLine.slice(1), kind: 'removed', oldLine, newLine: '' })
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

export function findDiffRowIndex(rows, line) {
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

export function makeDiffRowKey(filename, index) {
  return `${filename || 'unknown'}:${index}`
}
