import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export default function RetinopathyPlaceholder({ params }: { params: { id: string } }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ textAlign: 'center', padding: '3rem', backgroundColor: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-lg)' }}>
        <h2 style={{ marginBottom: '1rem', color: 'var(--color-amber)' }}>🚧 Retinopathy Module Coming Soon</h2>
        <p style={{ color: 'var(--color-text-muted)', marginBottom: '2rem' }}>
          The retinopathy risk assessment engine for patient {params.id} is currently under construction.
        </p>
        <Link href={`/patients/${params.id}/kidney`} style={{ color: 'var(--color-cyan)', display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
          <ArrowLeft size={16} /> Back to Kidney Module
        </Link>
      </div>
    </div>
  );
}
