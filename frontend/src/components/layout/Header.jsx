export default function Header({ health, loading }) {
  const status = loading ? '检查中' : health?.status === 'ok' ? '在线' : '离线'
  const apiStatusClass =
    status === '在线' ? 'online' : status === '离线' ? 'offline' : 'checking'

  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">V0.4 Context Pack 评审循环</p>
        <h1>AI PR Review 助手</h1>
      </div>
      <div className={`api-pill ${apiStatusClass}`}>
        <span>API</span>
        <strong>{status}</strong>
      </div>
    </header>
  )
}
