import { useState } from 'react'
import { DEFAULT_PR_URL, DEPTH_OPTIONS } from '../../utils/constants'

export default function ReviewForm({
  onSubmit,
  loading,
  defaultUrl = DEFAULT_PR_URL,
  defaultDepth = 'standard',
  githubAccess = 'read_only',
}) {
  const [prUrl, setPrUrl] = useState(defaultUrl)
  const [reviewDepth, setReviewDepth] = useState(defaultDepth)
  const isPrUrlValid = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/pull\/\d+\/?$/.test(
    prUrl.trim(),
  )
  const githubAccessLabel = githubAccess === 'read_only' ? 'Read-only' : 'Unknown'

  function handleSubmit(event) {
    event.preventDefault()
    if (!isPrUrlValid || loading) {
      return
    }
    onSubmit({
      pr_url: prUrl.trim(),
      review_depth: reviewDepth,
    })
  }

  return (
    <form className="tool-panel input-panel" onSubmit={handleSubmit}>
      <div className="panel-heading">
        <p className="eyebrow">Review Target</p>
        <h2>Create Review Task</h2>
      </div>

      <label className="field">
        <span>GitHub PR URL</span>
        <input
          value={prUrl}
          onChange={(event) => setPrUrl(event.target.value)}
          placeholder={DEFAULT_PR_URL}
          spellCheck="false"
        />
      </label>

      <fieldset className="depth-control">
        <legend>Review Depth</legend>
        <div className="segments">
          {DEPTH_OPTIONS.map((option) => (
            <button
              className={reviewDepth === option.value ? 'active' : ''}
              key={option.value}
              onClick={() => setReviewDepth(option.value)}
              type="button"
            >
              <span>{option.label}</span>
              <small>{option.caption}</small>
            </button>
          ))}
        </div>
      </fieldset>

      <button
        className="primary-action"
        disabled={!isPrUrlValid || loading}
        type="submit"
      >
        {loading ? 'Creating task' : 'Start AI Review'}
      </button>

      <div className="mock-note">
        <strong>GitHub {githubAccessLabel} Mode</strong>
        <span>
          The system only reads PR metadata, changed files, and diff. It does not
          automatically write comments back to GitHub. Any PR comment should be
          manually reviewed before posting.
        </span>
      </div>
    </form>
  )
}
