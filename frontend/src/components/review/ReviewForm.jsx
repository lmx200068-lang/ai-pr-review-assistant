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
  const githubAccessLabel = githubAccess === 'read_only' ? '只读' : '未知'

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
        <p className="eyebrow">评审目标</p>
        <h2>创建任务</h2>
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
        <legend>评审深度</legend>
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
        {loading ? '正在创建任务' : '开始 AI 评审'}
      </button>

      <div className="mock-note">
        <strong>GitHub {githubAccessLabel}测试</strong>
        <span>
          只读取 PR 元数据、changed files 和 Diff；不会自动写回 GitHub 评论，写回评论需要人工审查。
        </span>
      </div>
    </form>
  )
}
