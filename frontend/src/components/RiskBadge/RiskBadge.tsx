export default function RiskBadge({ level, score }: { level: string; score?: number }) {
  let colorVar = 'var(--color-text-muted)';
  let bgVar = 'var(--color-bg-surface)';
  let borderColor = 'var(--color-border-strong)';
  let glowColor = 'transparent';

  if (level === 'HIGH') {
    colorVar = 'var(--color-red)';
    bgVar = 'rgba(239, 68, 68, 0.1)';
    borderColor = 'var(--color-red)';
    glowColor = 'var(--color-red-glow)';
  } else if (level === 'MODERATE') {
    colorVar = 'var(--color-amber)';
    bgVar = 'rgba(245, 158, 11, 0.1)';
    borderColor = 'var(--color-amber)';
    glowColor = 'var(--color-amber-glow)';
  } else if (level === 'LOW') {
    colorVar = 'var(--color-cyan)';
    bgVar = 'rgba(0, 212, 255, 0.1)';
    borderColor = 'var(--color-cyan)';
    glowColor = 'var(--color-cyan-glow)';
  }

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '8px',
      padding: '4px 10px',
      borderRadius: '20px',
      backgroundColor: bgVar,
      border: `1px solid ${borderColor}`,
      color: colorVar,
      fontSize: '0.8rem',
      fontWeight: 600,
      letterSpacing: '0.05em',
      boxShadow: `0 0 10px ${glowColor}`,
    }}>
      {score !== undefined && <span style={{ opacity: 0.8 }}>SCORE {score}</span>}
      {score !== undefined && <span style={{ width: '1px', height: '10px', backgroundColor: borderColor, opacity: 0.5 }}></span>}
      <span>{level}</span>
    </div>
  );
}
