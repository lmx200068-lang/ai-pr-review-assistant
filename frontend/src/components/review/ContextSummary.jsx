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
        <span>{contextSummary.enabled ? 'Enabled' : 'Disabled'}</span>
      </div>
      <div className="context-grid">
        <div>
          <span>Changed Context</span>
          <strong>{contextSummary.changed_context_files || 0}</strong>
        </div>
        <div>
          <span>Related Files</span>
          <strong>{contextSummary.related_files || 0}</strong>
        </div>
        <div>
          <span>Repository Tree</span>
          <strong>{contextSummary.repo_tree_loaded ? 'Loaded' : 'Not loaded'}</strong>
        </div>
        <div>
          <span>Context Budget</span>
          <strong>
            {usedChars} / {maxChars || 'Not counted'}
          </strong>
        </div>
      </div>
      {truncatedFiles.length ? (
        <p>Truncated Context: {truncatedFiles.join(', ')}</p>
      ) : null}
      {skippedFiles.length ? (
        <p>Skipped Context: {skippedFiles.join(', ')}</p>
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
