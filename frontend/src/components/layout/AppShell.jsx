export default function AppShell({ header, error, children }) {
  return (
    <main className="app-shell">
      {header}
      {error}
      <section className="workspace" aria-label="PR review workspace">
        {children}
      </section>
    </main>
  )
}
