export default function Header({ health, loading }) {
  const status = loading ? 'Checking' : health?.status === 'ok' ? 'Online' : 'Offline'
  const apiStatusClass =
    status === 'Online' ? 'online' : status === 'Offline' ? 'offline' : 'checking'

  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">v0.4 Context Pack Review Loop</p>
        <h1>AI PR Review Assistant</h1>
      </div>
      <div className={`api-pill ${apiStatusClass}`}>
        <span>API</span>
        <strong>{status}</strong>
      </div>
    </header>
  )
}
