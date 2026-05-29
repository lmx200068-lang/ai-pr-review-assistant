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
        <p className="eyebrow">当前任务</p>
        <h2>{task ? STATUS_LABELS[task.status] || task.status : '暂无任务'}</h2>
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
              <dt>深度</dt>
              <dd>{labelFrom(DEPTH_LABELS, task.review_depth)}</dd>
            </div>
            <div>
              <dt>数据源</dt>
              <dd>{labelFrom(DATA_SOURCE_LABELS, task.data_source || 'mock')}</dd>
            </div>
            <div>
              <dt>Review 来源</dt>
              <dd>{labelFrom(REVIEW_SOURCE_LABELS, reviewSource)}</dd>
            </div>
          </dl>

          <p className="task-message">{getTaskMessage(task, reviewSource)}</p>

          {isLocalFallback ? (
            <div className="review-warning fallback-trust" role="status">
              <strong>可信度提示</strong>
              <span>
                LLM 评审失败，本次只生成待确认建议，不作为正式风险结论。
              </span>
            </div>
          ) : null}

          {task.status === 'failed' && task.review_error ? (
            <div className="review-warning" role="status">
              <strong>失败详情</strong>
              <span>{task.review_error}</span>
            </div>
          ) : null}
        </>
      ) : (
        <EmptyState>输入 PR URL 后即可开始一次 AI 评审。</EmptyState>
      )}
    </section>
  )
}
