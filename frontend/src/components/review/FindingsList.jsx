import {
  getFindingsEmptyMessage,
  isReviewingTask,
  isTerminalTask,
} from '../../utils/formatters'
import { groupFindings } from '../../utils/reviewFormatters'
import EmptyState from '../common/EmptyState'
import FindingGroupCard from './FindingGroupCard'

export default function FindingsList({
  findings,
  task,
  focusedFinding,
  onSelectFinding,
}) {
  const groups = groupFindings(findings)

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
        <h3>Verified Findings</h3>
        <span>
          {findings.length} verified finding{findings.length === 1 ? '' : 's'},
          grouped into {groups.length} issue type{groups.length === 1 ? '' : 's'}
        </span>
      </div>
      <div className="finding-list">
        {groups.map((group) => (
          <FindingGroupCard
            focusedFinding={focusedFinding}
            group={group}
            key={group.groupKey}
            onSelectFinding={onSelectFinding}
          />
        ))}
      </div>
    </section>
  )
}
