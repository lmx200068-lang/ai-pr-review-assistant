import FindingCard from './FindingCard'

export default function PendingFindings({
  pendingFindings,
  focusedFinding,
  onSelectFinding,
}) {
  if (!pendingFindings.length) {
    return null
  }

  return (
    <section className="confirmation-section">
      <div className="changed-files-header">
        <h3>待人工确认</h3>
        <span>{pendingFindings.length} 条需要复核</span>
      </div>
      <p>以下问题由于证据不足或上下文不足，暂不作为正式风险，需要人工确认。</p>
      <div className="finding-list pending-list">
        {pendingFindings.map((finding) => (
          <FindingCard
            finding={finding}
            key={finding.id}
            onSelect={onSelectFinding}
            pending
            selected={focusedFinding?.id === finding.id}
          />
        ))}
      </div>
    </section>
  )
}
