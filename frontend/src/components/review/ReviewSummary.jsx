import {
  REVIEW_SOURCE_LABELS,
} from '../../utils/constants'
import {
  getReviewSource,
  labelFrom,
  shouldShowReviewMeta,
} from '../../utils/formatters'

export default function ReviewSummary({ task }) {
  const summary = task?.summary
  const reviewSource = getReviewSource(task)
  const reviewModel =
    reviewSource === 'llm' ||
    reviewSource === 'llm_validated' ||
    reviewSource === 'local_fallback' ||
    reviewSource === 'fallback'
      ? task?.review_model || '未返回模型'
      : reviewSource === 'pending'
        ? '待开始'
        : '本地 mock'
  const isLocalFallback =
    reviewSource === 'local_fallback' || reviewSource === 'fallback'

  if (!summary) {
    return null
  }

  return (
    <>
      <div className="summary-strip">
        <div>
          <span>评分</span>
          <strong>{summary.score}</strong>
        </div>
        <div>
          <span>检查项</span>
          <strong>
            {summary.checks_passed}/{summary.checks_total}
          </strong>
        </div>
        <div>
          <span>评审耗时</span>
          <strong>{summary.estimated_review_minutes} 分钟</strong>
        </div>
      </div>

      <p className="verdict">{summary.verdict}</p>

      {shouldShowReviewMeta(task) ? (
        <div className={`review-meta ${reviewSource}`}>
          <span>Review 来源：{labelFrom(REVIEW_SOURCE_LABELS, reviewSource)}</span>
          <span translate="no">模型：{reviewModel}</span>
        </div>
      ) : null}

      {isLocalFallback ? (
        <div className="review-warning fallback-trust" role="status">
          <strong>可信度提示</strong>
          <span>
            LLM 评审失败，本次结果为本地启发式 fallback，仅用于流程演示，不作为正式风险结论。
          </span>
        </div>
      ) : null}

      {task?.review_error ? (
        <div className="review-warning" role="status">
          <strong>LLM 错误详情</strong>
          <span>{task.review_error}</span>
        </div>
      ) : null}
    </>
  )
}
