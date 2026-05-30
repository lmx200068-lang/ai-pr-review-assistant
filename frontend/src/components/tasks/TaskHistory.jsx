import { STATUS_LABELS } from '../../utils/constants'
import { formatDate } from '../../utils/formatters'
import EmptyState from '../common/EmptyState'
import LoadingBlock from '../common/LoadingBlock'

export default function TaskHistory({ tasks, activeTaskId, onSelect, loading }) {
  function taskPrUrl(task) {
    return task?.pr?.html_url || task?.pr_url || 'PR URL not loaded yet'
  }

  return (
    <aside className="tool-panel history-panel">
      <div className="panel-heading">
        <p className="eyebrow">Recent Tasks</p>
        <h2>Task Queue</h2>
      </div>

      {loading ? (
        <LoadingBlock>Loading tasks</LoadingBlock>
      ) : tasks.length ? (
        <div className="task-list">
          {tasks.slice(0, 5).map((task) => (
            <button
              className={activeTaskId === task.id ? 'selected' : ''}
              key={task.id}
              onClick={() => onSelect(task)}
              type="button"
            >
              <span className={`status-dot ${task.status}`} />
              <span>
                <strong>{STATUS_LABELS[task.status]}</strong>
                <small>{formatDate(task.created_at)}</small>
                <small className="task-pr-url" title={taskPrUrl(task)} translate="no">
                  {taskPrUrl(task)}
                </small>
              </span>
            </button>
          ))}
        </div>
      ) : (
        <EmptyState>No tasks yet</EmptyState>
      )}
    </aside>
  )
}
