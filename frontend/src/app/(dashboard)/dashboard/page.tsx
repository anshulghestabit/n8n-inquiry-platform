export default function DashboardPage() {
  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Demo control room</p>
          <h1>Customer Inquiry Handler</h1>
          <p>Build workflows, run the 5-agent chain, and inspect reply quality from one dashboard.</p>
        </div>
      </header>

      <section className="grid">
        <article className="panel">
          <h2>Current sprint</h2>
          <div className="metric">Day 5</div>
          <p className="muted">Frontend auth shell is now the active implementation layer.</p>
        </article>
        <article className="panel">
          <h2>Agent chain</h2>
          <div className="metric">5</div>
          <p className="muted">Classifier, Researcher, Qualifier, Responder, and Executor.</p>
        </article>
        <article className="panel">
          <h2>Blocked item</h2>
          <div className="metric">Sheets</div>
          <p className="muted">Day 4 live matrix needs Google Sheets ID and n8n credential configuration.</p>
        </article>
      </section>

      <section className="panel" style={{ marginTop: '1rem' }}>
        <h2>Next demo path</h2>
        <p className="muted">
          Signup, login, open dashboard, create workflow, trigger execution, inspect trace, then review analytics and exports.
        </p>
      </section>
    </>
  )
}
