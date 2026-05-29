import EmptyState from '../common/EmptyState'

export default function PrOverview({ pr }) {
  if (!pr) {
    return <EmptyState>正在同步 GitHub PR 元数据</EmptyState>
  }

  return (
    <div className="pr-snapshot">
      <div>
        <span className="repo-name">
          {pr.owner}/{pr.repo}
        </span>
        <strong>#{pr.number}</strong>
      </div>
      <h3>{pr.title}</h3>
      <div className="branch-line">
        <span translate="no">{pr.source_branch}</span>
        <span aria-hidden="true">到</span>
        <span translate="no">{pr.target_branch}</span>
      </div>
      <div className="diff-stats">
        <span>+{pr.additions}</span>
        <span>-{pr.deletions}</span>
        <span>{pr.changed_files} 个文件</span>
      </div>
    </div>
  )
}
