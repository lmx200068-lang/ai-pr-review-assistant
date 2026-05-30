import {
  DATA_SOURCE_LABELS,
  DEPTH_LABELS,
  REVIEW_SOURCE_LABELS,
  STATUS_LABELS,
} from '../../utils/constants'
import {
  getReviewSource,
  getTaskMessage,
  labelFrom,
} from '../../utils/formatters'
import EmptyState from '../common/EmptyState'

export default function TaskProgress({ task }) {
  const reviewSource = getReviewSource(task)
  const isLocalFallback =
    reviewSource === 'local_fallback' || reviewSource === 'fallback'

  return (
    <section className="tool-panel status-panel">
      <div className="panel-heading">
        <p className="eyebrow">Current Task</p>
        <h2>{task ? STATUS_LABELS[task.status] || task.status : 'No task'}</h2>
      </div>

      {task ? (
        <>
          <div className="progress-row">
            <div className="progress-track" aria-hidden="true">
              <span style={{ width: `${task.progress}%` }} />
            </div>
            <strong>{task.progress}%</strong>
          </div>

          <dl className="task-facts">
            <div>
              <dt>Task ID</dt>
              <dd>{task.id}</dd>
            </div>
            <div>
              <dt>Depth</dt>
              <dd>{labelFrom(DEPTH_LABELS, task.review_depth)}</dd>
            </div>
            <div>
              <dt>Data Source</dt>
              <dd>{labelFrom(DATA_SOURCE_LABELS, task.data_source || 'mock')}</dd>
            </div>
            <div>
              <dt>Review Source</dt>
              <dd>{labelFrom(REVIEW_SOURCE_LABELS, reviewSource)}</dd>
            </div>
          </dl>

          <p className="task-message">{getTaskMessage(task, reviewSource)}</p>

          {isLocalFallback ? (
            <div className="review-warning fallback-trust" role="status">
              <strong>Trust Notice</strong>
              <span>
                LLM review failed. This task only generated pending notes and
                should not be treated as verified risk output.
              </span>
            </div>
          ) : null}

          {task.status === 'failed' && task.review_error ? (
            <div className="review-warning" role="status">
              <strong>Failure Details</strong>
              <span>{task.review_error}</span>
            </div>
          ) : null}
        </>
      ) : (
        <EmptyState>Enter a PR URL to start an AI review.</EmptyState>
      )}
    </section>
  )
}
