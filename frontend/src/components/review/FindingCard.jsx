import {
  FILE_TYPE_LABELS,
  REVIEW_STRATEGY_LABELS,
} from '../../utils/constants'
import Badge from '../common/Badge'

export default function FindingCard({
  finding,
  pending = false,
  selected = false,
  onSelect,
}) {
  function handleKeyDown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onSelect?.(finding)
    }
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
        <span>{FILE_TYPE_LABELS[finding.file_type] || finding.file_type}</span>
        <span>
          {REVIEW_STRATEGY_LABELS[finding.review_strategy] ||
            finding.review_strategy}
        </span>
        <span className="finding-path" translate="no">
          {finding.file_path}
          {finding.line ? `:${finding.line}` : '：未定位行'}
        </span>
      </div>
      <h3>{finding.title}</h3>
      {pending ? <span className="pending-badge">待人工确认</span> : null}
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
          <span>LLM 未提供可校验的 Diff 行，需要人工确认。</span>
        )}
      </div>
      <div className="suggestion">
        <strong>修改建议</strong>
        <span>{finding.suggestion}</span>
      </div>
    </article>
  )
}
