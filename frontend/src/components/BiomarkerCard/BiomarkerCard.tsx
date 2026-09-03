import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import styles from './BiomarkerCard.module.css';

export default function BiomarkerCard({ concept, data }: { concept: string; data: any }) {
  if (!data) return null;

  const isWorsening = (
    (concept === 'eGFR' || concept === 'CGM_Time_in_Range') ? data.direction === 'decreasing' : data.direction === 'increasing'
  );
  
  const isImproving = (
    (concept === 'eGFR' || concept === 'CGM_Time_in_Range') ? data.direction === 'increasing' : data.direction === 'decreasing'
  );

  let borderClass = styles.stable;
  if (isWorsening) borderClass = styles.worsening;
  if (isImproving) borderClass = styles.improving;

  const abs = data.absolute_change ?? 0;
  const pct = data.percent_change ?? data.percentage_change ?? 0;

  return (
    <div className={`${styles.card} ${borderClass}`}>
      <div className={styles.header}>
        <h4>{concept.replace(/_/g, ' ')}</h4>
        <div className={styles.icon}>
          {data.direction === 'increasing' && <TrendingUp size={16} />}
          {data.direction === 'decreasing' && <TrendingDown size={16} />}
          {data.direction === 'stable' && <Minus size={16} />}
        </div>
      </div>
      
      <div className={styles.values}>
        <div className={styles.changeBox}>
          <span className={styles.value}>{data.first ?? '-'}</span>
          <ArrowRight />
          <span className={`${styles.value} ${styles.latest}`}>{data.latest ?? '-'}</span>
        </div>
        
        <div className={styles.stats}>
          <div className={styles.stat}>
            <span className={styles.label}>Δ Abs</span>
            <span className={styles.statValue}>{abs > 0 ? '+' : ''}{typeof abs === 'number' ? abs.toFixed(1) : abs}</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.label}>Δ %</span>
            <span className={styles.statValue}>{pct > 0 ? '+' : ''}{typeof pct === 'number' ? pct.toFixed(1) : pct}%</span>
          </div>
        </div>
      </div>
      
      <div className={styles.footer}>
        <span className={styles.tag}>{(data.direction ?? 'stable').toUpperCase()}</span>
      </div>
    </div>
  );
}

function ArrowRight() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12"></line>
      <polyline points="12 5 19 12 12 19"></polyline>
    </svg>
  );
}
