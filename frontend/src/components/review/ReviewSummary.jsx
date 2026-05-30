import {
  REVIEW_SOURCE_LABELS,
} from '../../utils/constants'
import {
  getReviewSource,
  labelFrom,
  shouldShowReviewMeta,
} from '../../utils/formatters'
import { displayEnglishOrFallback } from '../../utils/reviewFormatters'

export default function ReviewSummary({ task }) {
  const summary = task?.summary
  const reviewSource = getReviewSource(task)
  const reviewModel =
    reviewSource === 'llm' ||
    reviewSource === 'llm_validated' ||
    reviewSource === 'local_fallback' ||
    reviewSource === 'fallback'
      ? task?.review_model || 'Model not returned'
      : reviewSource === 'pending'
        ? 'Pending'
        : 'Local mock'
  const isLocalFallback =
    reviewSource === 'local_fallback' || reviewSource === 'fallback'

  if (!summary) {
    return null
  }

  return (
    <>
      <div className="summary-strip">
        <div>
          <span>Score</span>
          <strong>{summary.score}</strong>
        </div>
        <div>
          <span>Checks</span>
          <strong>
            Verified: {task?.findings?.length || 0} / Total:{' '}
            {(task?.findings?.length || 0) + (task?.pending_findings?.length || 0)}
          </strong>
        </div>
        <div>
          <span>Review Time</span>
          <strong>{summary.estimated_review_minutes} min</strong>
        </div>
      </div>

      <p className="verdict">
        {displayEnglishOrFallback(
          summary.verdict,
          'Review completed. See verified findings and pending notes below.',
        )}
      </p>

      {shouldShowReviewMeta(task) ? (
        <div className={`review-meta ${reviewSource}`}>
          <span>Review Source: {labelFrom(REVIEW_SOURCE_LABELS, reviewSource)}</span>
          <span translate="no">Model: {reviewModel}</span>
        </div>
      ) : null}

      {isLocalFallback ? (
        <div className="review-warning fallback-trust" role="status">
          <strong>Trust Notice</strong>
          <span>
            LLM review failed. This task fell back to local heuristic review and
            should not be treated as verified risk output.
          </span>
        </div>
      ) : null}

      {task?.review_error ? (
        <div className="review-warning" role="status">
          <strong>LLM Error Details</strong>
          <span>{task.review_error}</span>
        </div>
      ) : null}
    </>
  )
}
