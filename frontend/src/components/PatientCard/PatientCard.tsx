import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import RiskBadge from '../RiskBadge/RiskBadge';
import TrendSparkline from '../TrendSparkline/TrendSparkline';
import styles from './PatientCard.module.css';

export default function PatientCard({ patient, timeline, trends, patientPattern }: any) {
  // Convert timeline dict to array for sparklines
  const dates = Object.keys(timeline || {}).sort();
  const sparkData = dates.map(date => {
    return {
      date,
      hba1c: timeline[date]['HbA1c']?.value,
      uacr: timeline[date]['UACR']?.value,
      egfr: timeline[date]['eGFR']?.value,
    };
  });

  const getRiskLevel = (pattern: string) => {
    if (pattern === 'PROGRESSIVE_RENAL_TRAJECTORY') return 'HIGH';
    if (pattern === 'TRANSIENT_UACR_ABNORMALITY' || pattern === 'EMERGING_RENAL_SIGNAL' || pattern === 'WORSENING_METABOLIC_BP_WITH_STABLE_KIDNEY_MARKERS') return 'MODERATE';
    if (pattern === 'STABLE_TRAJECTORY') return 'LOW';
    return 'NO_SIGNAL';
  };

  const riskLevel = getRiskLevel(patientPattern);

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.idBox}>
          <h3>{patient.patient_id}</h3>
        </div>
        <RiskBadge level={riskLevel} />
      </div>

      <div className={styles.demographics}>
        <div>
          <span className={styles.label}>Age</span>
          <span className={styles.value}>{patient.age}</span>
        </div>
        <div>
          <span className={styles.label}>Sex</span>
          <span className={styles.value}>{patient.sex}</span>
        </div>
        <div>
          <span className={styles.label}>T1D</span>
          <span className={styles.value}>{patient.t1d_duration}y</span>
        </div>
      </div>

      <div className={styles.metrics}>
        <div className={styles.metricRow}>
          <span className={styles.metricLabel}>HbA1c</span>
          <TrendSparkline data={sparkData} dataKey="hba1c" color={trends?.['HbA1c']?.direction === 'increasing' ? 'var(--color-amber)' : 'var(--color-cyan)'} />
          <span className={styles.metricValue}>{trends?.['HbA1c']?.latest || '--'}%</span>
        </div>
        <div className={styles.metricRow}>
          <span className={styles.metricLabel}>UACR</span>
          <TrendSparkline data={sparkData} dataKey="uacr" color={trends?.['UACR']?.direction === 'increasing' ? 'var(--color-red)' : 'var(--color-cyan)'} />
          <span className={styles.metricValue}>{trends?.['UACR']?.latest || '--'} <span className={styles.unit}>mg/g</span></span>
        </div>
        <div className={styles.metricRow}>
          <span className={styles.metricLabel}>eGFR</span>
          <TrendSparkline data={sparkData} dataKey="egfr" color={trends?.['eGFR']?.direction === 'decreasing' ? 'var(--color-red)' : 'var(--color-cyan)'} />
          <span className={styles.metricValue}>{trends?.['eGFR']?.latest || '--'}</span>
        </div>
      </div>

      <div className={styles.footer}>
        <Link href={`/patients/${patient.patient_id}/kidney`} className={styles.cta}>
          Kidney <ArrowRight size={14} />
        </Link>
        <Link href={`/patients/${patient.patient_id}/cardio`} className={styles.ctaAlt}>
          Cardio <ArrowRight size={14} />
        </Link>
        <Link href={`/patients/${patient.patient_id}/retinopathy`} className={styles.ctaAlt}>
          Retinal <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
}
