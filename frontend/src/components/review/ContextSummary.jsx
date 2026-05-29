export default function ContextSummary({ contextSummary }) {
  if (!contextSummary) {
    return null
  }

  const warnings = Array.isArray(contextSummary.warnings)
    ? contextSummary.warnings
    : []
  const truncatedFiles = Array.isArray(contextSummary.truncated_files)
    ? contextSummary.truncated_files
    : []
  const skippedFiles = Array.isArray(contextSummary.skipped_files)
    ? contextSummary.skipped_files
    : []
  const usedChars = contextSummary.used_chars || 0
  const maxChars = contextSummary.max_chars || 0

  return (
    <section className="context-summary">
      <div className="changed-files-header">
        <h3>Context Pack</h3>
        <span>{contextSummary.enabled ? '已开启' : '未开启'}</span>
      </div>
      <div className="context-grid">
        <div>
          <span>变更上下文</span>
          <strong>{contextSummary.changed_context_files || 0}</strong>
        </div>
        <div>
          <span>相关文件</span>
          <strong>{contextSummary.related_files || 0}</strong>
        </div>
        <div>
          <span>仓库结构</span>
          <strong>{contextSummary.repo_tree_loaded ? '已读取' : '未读取'}</strong>
        </div>
        <div>
          <span>上下文预算</span>
          <strong>
            {usedChars} / {maxChars || '未统计'}
          </strong>
        </div>
      </div>
      {truncatedFiles.length ? (
        <p>已截断：{truncatedFiles.join(', ')}</p>
      ) : null}
      {skippedFiles.length ? (
        <p>已跳过：{skippedFiles.join(', ')}</p>
      ) : null}
      {warnings.length ? (
        <ul>
          {warnings.slice(0, 5).map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
