import {
  getFindingsEmptyMessage,
  isReviewingTask,
  isTerminalTask,
} from '../../utils/formatters'
import EmptyState from '../common/EmptyState'
import FindingCard from './FindingCard'

export default function FindingsList({
  findings,
  task,
  focusedFinding,
  onSelectFinding,
}) {
  if (!findings.length) {
    return (
      <EmptyState>
        {getFindingsEmptyMessage(task, isReviewingTask(task) && !isTerminalTask(task))}
      </EmptyState>
    )
  }

  return (
    <section className="formal-findings-section">
      <div className="changed-files-header">
        <h3>正式风险 Findings</h3>
        <span>{findings.length} 条证据已校验</span>
      </div>
      <div className="finding-list">
        {findings.map((finding) => (
          <FindingCard
            finding={finding}
            key={finding.id}
            onSelect={onSelectFinding}
            selected={focusedFinding?.id === finding.id}
          />
        ))}
      </div>
    </section>
  )
}
