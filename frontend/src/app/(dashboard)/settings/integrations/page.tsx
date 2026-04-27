const integrations = [
  ['Gmail', 'Receives customer inquiries and sends replies'],
  ['Google Sheets', 'Stores execution rows from n8n'],
  ['Google Drive', 'Provides the knowledge base for Researcher'],
  ['WhatsApp', 'Optional second customer channel'],
]

export default function IntegrationsPage() {
  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Layer 6.5 placeholder</p>
          <h1>Integrations</h1>
          <p>The status bar already reads integration state from FastAPI. Management actions come next.</p>
        </div>
      </header>

      <section className="grid">
        {integrations.map(([name, description]) => (
          <article className="panel" key={name}>
            <h2>{name}</h2>
            <p className="muted">{description}</p>
            <button className="button secondary" disabled>Verify</button>
          </article>
        ))}
      </section>
    </>
  )
}
