export default function AppShell({ header, error, children }) {
  return (
    <main className="app-shell">
      {header}
      {error}
      <section className="workspace" aria-label="PR 评审工作台">
        {children}
      </section>
    </main>
  )
}
