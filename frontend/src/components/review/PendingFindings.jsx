import FindingCard from './FindingCard'

export default function PendingFindings({
  pendingFindings,
  focusedFinding,
  onSelectFinding,
  reviewSource,
}) {
  if (!pendingFindings.length) {
    return null
  }

  return (
    <section className="confirmation-section">
      <div className="changed-files-header">
        <h3>Pending Review Notes</h3>
        <span>
          {pendingFindings.length} pending note{pendingFindings.length === 1 ? '' : 's'}
        </span>
      </div>
      <p>
        The following notes are not treated as verified risks because the evidence
        or context is insufficient. Manual confirmation is required.
      </p>
      <div className="finding-list pending-list">
        {pendingFindings.map((finding) => (
          <FindingCard
            finding={finding}
            key={finding.id}
            onSelect={onSelectFinding}
            pending
            reviewSource={reviewSource}
            selected={focusedFinding?.id === finding.id}
          />
        ))}
      </div>
    </section>
  )
}
