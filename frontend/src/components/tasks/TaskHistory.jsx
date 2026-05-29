import { STATUS_LABELS } from '../../utils/constants'
import { formatDate } from '../../utils/formatters'
import EmptyState from '../common/EmptyState'
import LoadingBlock from '../common/LoadingBlock'

export default function TaskHistory({ tasks, activeTaskId, onSelect, loading }) {
  return (
    <aside className="tool-panel history-panel">
      <div className="panel-heading">
        <p className="eyebrow">最近任务</p>
        <h2>任务队列</h2>
      </div>

      {loading ? (
        <LoadingBlock>正在加载任务</LoadingBlock>
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
              </span>
            </button>
          ))}
        </div>
      ) : (
        <EmptyState>暂无任务</EmptyState>
      )}
    </aside>
  )
}
