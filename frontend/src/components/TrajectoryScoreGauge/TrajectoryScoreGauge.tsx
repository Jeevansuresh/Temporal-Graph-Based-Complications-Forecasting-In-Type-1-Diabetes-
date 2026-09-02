import styles from './TrajectoryScoreGauge.module.css';

const MAX_SCORE = 20; // approx max possible

export default function TrajectoryScoreGauge({ score, level }: { score: number; level: string }) {
  const percent = Math.min(100, (score / MAX_SCORE) * 100);

  const levelColors: Record<string, string> = {
    LOW_CARDIOVASCULAR_RISK: 'var(--color-cyan)',
    MODERATE_CARDIOVASCULAR_RISK: 'var(--color-amber)',
    HIGH_CARDIOVASCULAR_RISK: '#f97316',
    VERY_HIGH_CARDIOVASCULAR_RISK: 'var(--color-red)',
  };

  const color = levelColors[level] ?? 'var(--color-text-muted)';
  const labelMap: Record<string, string> = {
    LOW_CARDIOVASCULAR_RISK: 'Low',
    MODERATE_CARDIOVASCULAR_RISK: 'Moderate',
    HIGH_CARDIOVASCULAR_RISK: 'High',
    VERY_HIGH_CARDIOVASCULAR_RISK: 'Very High',
  };

  return (
    <div className={styles.container}>
      <div className={styles.scoreBox} style={{ color }}>
        <span className={styles.scoreNumber}>{score}</span>
        <span className={styles.scoreLabel}>/ {MAX_SCORE}</span>
      </div>
      <div className={styles.barTrack}>
        <div
          className={styles.barFill}
          style={{ width: `${percent}%`, backgroundColor: color, boxShadow: `0 0 10px ${color}` }}
        />
      </div>
      <div className={styles.level} style={{ color }}>
        {labelMap[level] ?? level.replace(/_/g, ' ')} Risk
      </div>
    </div>
  );
}
