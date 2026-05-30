import EmptyState from '../common/EmptyState'

export default function PrOverview({ pr }) {
  if (!pr) {
    return <EmptyState>Syncing GitHub PR metadata</EmptyState>
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
        <span aria-hidden="true">to</span>
        <span translate="no">{pr.target_branch}</span>
      </div>
      <div className="diff-stats">
        <span>+{pr.additions}</span>
        <span>-{pr.deletions}</span>
        <span>
          {pr.changed_files} file{pr.changed_files === 1 ? '' : 's'}
        </span>
      </div>
    </div>
  )
}
