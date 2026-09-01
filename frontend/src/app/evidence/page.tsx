export default function EvidencePage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center', padding: '3rem', backgroundColor: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-lg)' }}>
        <h2 style={{ marginBottom: '1rem', color: 'var(--color-amber)' }}>🚧 Evidence Library Coming Soon</h2>
        <p style={{ color: 'var(--color-text-muted)', marginBottom: '2rem' }}>
          A searchable index of clinical guidelines and cohort evidence will be available here.
        </p>
      </div>
    </div>
  );
}
