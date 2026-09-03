'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Eye } from 'lucide-react';
import BiomarkerCard from '@/components/BiomarkerCard/BiomarkerCard';
import AIReasonerPanel from '@/components/AIReasonerPanel/AIReasonerPanel';
import RuleCard from '@/components/RuleCard/RuleCard';
import PatientChatbot from '@/components/PatientChatbot/PatientChatbot';
import styles from './page.module.css';

export default function RetinopathyPage() {
  const params = useParams();
  const id = params.id as string;

  const [data, setData] = useState<any>(null);
  const [reasoning, setReasoning] = useState<string | null>(null);
  const [reasoningLoading, setReasoningLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetch(`/api/retinopathy/patients/${id}`);
        const result = await res.json();
        if (result.error) { setError(result.error); return; }
        setData(result);

        setReasoningLoading(true);
        fetch(`/api/retinopathy/patients/${id}/reason`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ packet: result }),
        })
          .then(r => r.json())
          .then(d => setReasoning(d.result ?? d.error ?? 'No response'))
          .catch(e => setReasoning(`Error: ${e.message}`))
          .finally(() => setReasoningLoading(false));
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [id]);

  if (loading) return <div className={styles.message}>Loading patient {id} — Retinopathy Module...</div>;
  if (error || !data) return <div className={styles.error}>{error ?? 'Patient not found'}</div>;

  const { patient, profile, rules, risk_state, risk_reason } = data;
  const { retinal_trajectory, numeric_features } = profile;

  const riskColors: Record<string, string> = {
    STABLE: 'var(--color-cyan)',
    WATCH: 'var(--color-amber)',
    INCREASING_CONCERN: '#f97316',
    HIGH_CONCERN: 'var(--color-red)',
    INSUFFICIENT_DATA: 'var(--color-text-muted)',
  };
  const riskColor = riskColors[risk_state] ?? 'var(--color-text-muted)';
  const riskLabel = risk_state?.replace(/_/g, ' ').trim();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.moduleTag}>
            <Eye size={16} />
            <span>Retinopathy Module</span>
          </div>
          <h2>{patient.patient_id}</h2>
          <div className={styles.demographics}>
            <span>{patient.age}yo</span> •
            <span>{patient.sex}</span> •
            <span>T1D {patient.t1d_duration}y</span>
            {patient.puberty_status && (
              <><span>•</span><span>Puberty: {patient.puberty_status}</span></>
            )}
          </div>
        </div>
        <div className={styles.riskPill} style={{ borderColor: riskColor, color: riskColor, boxShadow: `0 0 14px ${riskColor}44` }}>
          {riskLabel}
        </div>
      </header>

      <div className={styles.patternBanner}>
        <span>ℹ️</span>
        <span>{risk_reason}</span>
      </div>

      <div className={styles.topRow}>
        <div className={styles.gaugeWrap}>
          <h3>Retinal Trajectory</h3>
          <div className={styles.scoreStats}>
            <div className={styles.scoreStat}>
              <span className={styles.scoreStatLabel}>Exams Recorded</span>
              <span className={styles.scoreStatNum}>{retinal_trajectory.n_observed} / {retinal_trajectory.n_visits_total}</span>
            </div>
            <div className={styles.scoreStat}>
              <span className={styles.scoreStatLabel}>Latest Stage</span>
              <span className={styles.scoreStatNum}>{retinal_trajectory.latest_observed_stage_label ?? 'N/A'}</span>
            </div>
            <div className={styles.scoreStat}>
              <span className={styles.scoreStatLabel}>Overall Trajectory</span>
              <span className={styles.scoreStatNum}>{retinal_trajectory.overall_transition_type.replace(/_/g, ' ')}</span>
            </div>
          </div>
        </div>

        <div className={styles.biomarkersPanel}>
          <h3>Numeric Features</h3>
          <div className={styles.biomarkerGrid}>
            {Object.keys(numeric_features ?? {}).map(concept => (
              <BiomarkerCard key={concept} concept={concept} data={numeric_features[concept]} />
            ))}
          </div>
        </div>
      </div>

      <section>
        <h3 className={styles.sectionTitle}>Rule Evaluation (R001 – R013)</h3>
        <div className={styles.rulesGrid}>
          {(rules ?? []).map((rule: any) => (
            <RuleCard key={rule.rule_id} rule={rule} />
          ))}
        </div>
      </section>

      <section>
        <AIReasonerPanel content={reasoning} loading={reasoningLoading} />
      </section>

      <section>
        <PatientChatbot module="retinopathy" patientId={id} patientData={data} />
      </section>
    </div>
  );
}
