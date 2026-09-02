import styles from './RuleCard.module.css';

export default function RuleCard({ rule }: { rule: any }) {
  return (
    <div className={`${styles.card} ${rule.satisfied ? styles.satisfied : styles.unsatisfied}`}>
      <div className={styles.header}>
        <span className={styles.id}>{rule.rule_id}</span>
        <span className={`${styles.badge} ${rule.satisfied ? styles.badgeOn : styles.badgeOff}`}>
          {rule.satisfied ? 'TRIGGERED' : 'NOT MET'}
        </span>
      </div>
      <p className={styles.name}>{rule.name}</p>
      <p className={styles.trigger}><span>Condition:</span> {rule.trigger}</p>
      <p className={styles.reason}>{rule.reason}</p>
      {rule.recommendation && (
        <p className={styles.recommendation}>📋 {rule.recommendation}</p>
      )}
    </div>
  );
}
