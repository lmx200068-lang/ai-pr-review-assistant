import { useState } from 'react'
import {
  FILE_TYPE_LABELS,
  REVIEW_STRATEGY_LABELS,
} from '../../utils/constants'
import {
  copyTextToClipboard,
  findingDisplaySummary,
  findingDisplaySuggestion,
  findingDisplayTitle,
  formatFindingAsGithubComment,
  formatPendingFindingAsGithubComment,
} from '../../utils/reviewFormatters'
import Badge from '../common/Badge'

export default function FindingCard({
  finding,
  pending = false,
  reviewSource = '',
  selected = false,
  onSelect,
}) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const evidenceLines = finding.evidence_lines || []
  const visibleEvidence = expanded ? evidenceLines : evidenceLines.slice(0, 3)
  const fileTypeLabel =
    FILE_TYPE_LABELS[finding.file_type] || finding.file_type || 'Unclassified'
  const reviewStrategyLabel =
    REVIEW_STRATEGY_LABELS[finding.review_strategy] ||
    finding.review_strategy ||
    'No review strategy'

  function handleKeyDown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect?.(finding)
    }
  }

  async function handleCopy(event) {
    event.stopPropagation()
    const text = pending
      ? formatPendingFindingAsGithubComment(finding, reviewSource)
      : formatFindingAsGithubComment(finding)
    await copyTextToClipboard(text)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  function handleToggleEvidence(event) {
    event.stopPropagation()
    setExpanded((current) => !current)
  }

  function handleSelectLocation(event) {
    event.stopPropagation()
    onSelect?.(finding)
  }

  const cardClass = [
    'finding-card',
    pending ? 'pending' : '',
    selected ? 'selected' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <article
      className={cardClass}
      onClick={() => onSelect?.(finding)}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
    >
      <div className="finding-card-header">
        <Badge type={finding.severity}>{finding.severity}</Badge>
        <span className="finding-meta-chip" title="File type">
          {fileTypeLabel}
        </span>
        <span className="finding-meta-chip" title="Review strategy">
          {reviewStrategyLabel}
        </span>
        <button
          className="finding-path"
          onClick={handleSelectLocation}
          title="Jump to PR Diff"
          type="button"
          translate="no"
        >
          {finding.file_path}
          {finding.line ? `:${finding.line}` : ':line unavailable'}
        </button>
      </div>
      <div className="finding-title-row">
        <h3>{findingDisplayTitle(finding)}</h3>
        <button className="copy-action" onClick={handleCopy} type="button">
          {copied ? 'Copied' : pending ? 'Copy Pending Note' : 'Copy Comment'}
        </button>
      </div>
      {pending ? <span className="pending-badge">Pending Confirmation</span> : null}
      <div className="finding-section">
        <strong>Details</strong>
        <p>{findingDisplaySummary(finding)}</p>
      </div>
      <div className="evidence-block">
        <div className="evidence-heading">
          <strong>{pending ? 'Evidence Status' : 'Evidence'}</strong>
          {evidenceLines.length > 3 ? (
            <button onClick={handleToggleEvidence} type="button">
              {expanded ? 'Collapse Evidence' : 'Expand Evidence'}
            </button>
          ) : null}
        </div>
        {visibleEvidence.length ? (
          <pre translate="no">
            {visibleEvidence.map((line, index) => (
              <code key={`${finding.id}-evidence-${index}`}>{line}</code>
            ))}
          </pre>
        ) : (
          <span>
            No validated diff line was found for this pending note. Manual
            confirmation is required.
          </span>
        )}
      </div>
      <div className="suggestion">
        <strong>{pending ? 'Manual Confirmation Suggested' : 'Suggestion'}</strong>
        <span>{findingDisplaySuggestion(finding)}</span>
      </div>
    </article>
  )
}
