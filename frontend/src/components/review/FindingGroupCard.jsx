import { useMemo, useState } from 'react'
import { FILE_TYPE_LABELS, REVIEW_STRATEGY_LABELS } from '../../utils/constants'
import {
  copyTextToClipboard,
  findingGroupDisplaySuggestion,
  findingGroupDisplaySummary,
  findingGroupDisplayTitle,
  formatFindingGroupAsGithubComment,
  formatLocation,
} from '../../utils/reviewFormatters'
import Badge from '../common/Badge'

export default function FindingGroupCard({
  group,
  focusedFinding,
  onSelectFinding,
}) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const firstFinding = group.items[0]?.original
  const fileTypeLabel =
    FILE_TYPE_LABELS[firstFinding?.file_type] ||
    firstFinding?.file_type ||
    'Unclassified'
  const reviewStrategyLabel =
    REVIEW_STRATEGY_LABELS[firstFinding?.review_strategy] ||
    firstFinding?.review_strategy ||
    'No review strategy'
  const isSelected = group.items.some(
    (item) => focusedFinding?.id === item.original.id,
  )
  const evidenceItems = useMemo(
    () =>
      group.items.filter(
        (item) => item.original.evidence_lines?.filter(Boolean).length,
      ),
    [group.items],
  )
  const visibleEvidence = expanded ? evidenceItems : evidenceItems.slice(0, 1)

  async function handleCopy(event) {
    event.stopPropagation()
    await copyTextToClipboard(formatFindingGroupAsGithubComment(group))
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  function handleToggleEvidence(event) {
    event.stopPropagation()
    setExpanded((current) => !current)
  }

  const cardClass = ['finding-card', 'finding-group-card', isSelected ? 'selected' : '']
    .filter(Boolean)
    .join(' ')

  return (
    <article className={cardClass}>
      <div className="finding-card-header">
        <Badge type={group.severity}>{group.severity}</Badge>
        <span className="finding-meta-chip" title="File type">
          {fileTypeLabel}
        </span>
        <span className="finding-meta-chip" title="Review strategy">
          {reviewStrategyLabel}
        </span>
        <span className="finding-meta-chip" title="Affected location count">
          {group.items.length} affected location{group.items.length === 1 ? '' : 's'}
        </span>
      </div>

      <div className="finding-title-row">
        <h3>{findingGroupDisplayTitle(group)}</h3>
        <button className="copy-action" onClick={handleCopy} type="button">
          {copied ? 'Copied' : 'Copy Comment'}
        </button>
      </div>

      <div className="finding-section">
        <strong>
          Affected Location{group.items.length === 1 ? '' : 's'}
        </strong>
        <ul className="impact-list">
          {group.items.map((item) => (
            <li key={`${item.file_path}-${item.line || 'no-line'}`}>
              <button
                onClick={() => onSelectFinding?.(item.original)}
                type="button"
              >
                <span translate="no">{formatLocation(item.file_path, item.line)}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="finding-section">
        <strong>Details</strong>
        <p>{findingGroupDisplaySummary(group)}</p>
      </div>

      <div className="evidence-block">
        <div className="evidence-heading">
          <strong>Evidence</strong>
          {evidenceItems.length > 1 ? (
            <button onClick={handleToggleEvidence} type="button">
              {expanded ? 'Collapse Evidence' : 'Expand Evidence'}
            </button>
          ) : null}
        </div>

        {visibleEvidence.length ? (
          visibleEvidence.map((item) => (
            <div
              className="group-evidence-item"
              key={`${item.file_path}-${item.line || 'no-line'}-evidence`}
            >
              <span translate="no">{formatLocation(item.file_path, item.line)}</span>
              <pre translate="no">
                {item.original.evidence_lines.map((line, index) => (
                  <code key={`${item.original.id}-group-evidence-${index}`}>
                    {line}
                  </code>
                ))}
              </pre>
            </div>
          ))
        ) : (
          <span>
            No validated diff line was found for this finding. Manual
            confirmation is required.
          </span>
        )}
      </div>

      <div className="suggestion">
        <strong>Suggestion</strong>
        <span>{findingGroupDisplaySuggestion(group)}</span>
      </div>
    </article>
  )
}
