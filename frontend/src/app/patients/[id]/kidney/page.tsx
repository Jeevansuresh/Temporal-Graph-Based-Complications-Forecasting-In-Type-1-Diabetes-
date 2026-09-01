'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import RiskBadge from '@/components/RiskBadge/RiskBadge';
import TimeSeriesChart from '@/components/TimeSeriesChart/TimeSeriesChart';
import BiomarkerCard from '@/components/BiomarkerCard/BiomarkerCard';
import AIReasonerPanel from '@/components/AIReasonerPanel/AIReasonerPanel';
import styles from './page.module.css';

export default function KidneyPage() {
  const params = useParams();
  const id = params.id as string;
  
  const [data, setData] = useState<any>(null);
  const [reasoning, setReasoning] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetch(`/api/patients/${id}`);
        const result = await res.json();
        setData(result);
        
        // Fetch reasoning in background
        fetch(`/api/patients/${id}/reason`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ packet: result })
        })
        .then(r => r.json())
        .then(d => setReasoning(d.result))
        .catch(console.error);

      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [id]);

  if (loading) return <div className={styles.loading}>Loading patient {id}...</div>;
  if (!data || data.error) return <div className={styles.error}>Patient not found</div>;

  const { patient, timeline, trends, patterns, patient_pattern } = data;

  const getRiskLevel = (pattern: string) => {
    if (pattern === 'PROGRESSIVE_RENAL_TRAJECTORY') return 'HIGH';
    if (pattern === 'TRANSIENT_UACR_ABNORMALITY' || pattern === 'EMERGING_RENAL_SIGNAL' || pattern === 'WORSENING_METABOLIC_BP_WITH_STABLE_KIDNEY_MARKERS') return 'MODERATE';
    if (pattern === 'STABLE_TRAJECTORY') return 'LOW';
    return 'NO_SIGNAL';
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerTitle}>
          <h2>Kidney Module: {patient.patient_id}</h2>
          <div className={styles.demographics}>
            <span>{patient.age}yo</span> • <span>{patient.sex}</span> • <span>T1D {patient.t1d_duration}y</span>
          </div>
        </div>
        <div className={styles.badgeContainer}>
          <div className={styles.badgeLabel}>Temporal Renal-Risk Signal</div>
          <RiskBadge level={getRiskLevel(patient_pattern)} />
        </div>
      </header>
      
      <div className={styles.patternBox}>
        <span className={styles.patternIcon}>⚡</span>
        <span className={styles.patternText}>{patient_pattern.replace(/_/g, ' ')}</span>
      </div>

      <section className={styles.chartSection}>
        <h3>Temporal Trajectory</h3>
        <TimeSeriesChart timeline={timeline} trends={trends} />
      </section>

      <section className={styles.cardsSection}>
        {Object.keys(trends || {}).map(concept => (
          <BiomarkerCard key={concept} concept={concept} data={trends[concept]} />
        ))}
      </section>

      <section className={styles.flagsSection}>
        <h3>Clinical Flags</h3>
        <ul className={styles.flagList}>
          {patterns?.map((pattern: string, i: number) => (
            <li key={i} className={styles.flag}>
              <span className={styles.flagDot}></span>
              {pattern}
            </li>
          ))}
          {patterns?.length === 0 && <li className={styles.emptyFlag}>No significant cross-variable worsening patterns detected.</li>}
        </ul>
      </section>

      <section className={styles.reasonerSection}>
        <AIReasonerPanel content={reasoning} loading={!reasoning} />
      </section>
    </div>
  );
}
