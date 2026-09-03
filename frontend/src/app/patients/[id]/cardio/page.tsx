'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Heart } from 'lucide-react';
import TimeSeriesChart from '@/components/TimeSeriesChart/TimeSeriesChart';
import BiomarkerCard from '@/components/BiomarkerCard/BiomarkerCard';
import AIReasonerPanel from '@/components/AIReasonerPanel/AIReasonerPanel';
import RuleCard from '@/components/RuleCard/RuleCard';
import TrajectoryScoreGauge from '@/components/TrajectoryScoreGauge/TrajectoryScoreGauge';
import PatientChatbot from '@/components/PatientChatbot/PatientChatbot';
import styles from './page.module.css';

export default function CardioPage() {
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
        const res = await fetch(`/api/cardio/patients/${id}`);
        const result = await res.json();
        if (result.error) { setError(result.error); return; }
        setData(result);

        // Fetch reasoning asynchronously
        setReasoningLoading(true);
        fetch(`/api/cardio/patients/${id}/reason`, {
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

  if (loading) return <div className={styles.message}>Loading patient {id} — Cardio Module...</div>;
  if (error || !data) return <div className={styles.error}>{error ?? 'Patient not found'}</div>;

  const {
    patient, timeline, trends, worsening, cross_patterns,
    patient_pattern, rules, trajectory_score, risk_level, clinical_flags,
  } = data;

  const riskColors: Record<string, string> = {
    LOW_CARDIOVASCULAR_RISK: 'var(--color-cyan)',
    MODERATE_CARDIOVASCULAR_RISK: 'var(--color-amber)',
    HIGH_CARDIOVASCULAR_RISK: '#f97316',
    VERY_HIGH_CARDIOVASCULAR_RISK: 'var(--color-red)',
  };
  const riskColor = riskColors[risk_level] ?? 'var(--color-text-muted)';
  const riskLabel = risk_level?.replace(/_/g, ' ').replace('CARDIOVASCULAR RISK', '').trim();

  const triggeredRules = (rules ?? []).filter((r: any) => r.satisfied).length;

  return (
    <div className={styles.page}>
      {/* ── HEADER ── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.moduleTag}>
            <Heart size={16} />
            <span>Cardio Module</span>
          </div>
          <h2>{patient.patient_id}</h2>
          <div className={styles.demographics}>
            <span>{patient.age}yo</span> •
            <span>{patient.sex}</span> •
            <span>T1D {patient.t1d_duration}y</span>
            {patient.baseline_cvd_context && (
              <><span>•</span><span className={styles.ctx}>{patient.baseline_cvd_context}</span></>
            )}
          </div>
        </div>
        <div className={styles.riskPill} style={{ borderColor: riskColor, color: riskColor, boxShadow: `0 0 14px ${riskColor}44` }}>
          {riskLabel}
        </div>
      </header>

      {/* ── PATTERN BANNER ── */}
      <div className={styles.patternBanner}>
        <span>⚡</span>
        <span>{patient_pattern?.replace(/_/g, ' ')}</span>
      </div>

      {/* ── TOP PANELS: Score + Stats ── */}
      <div className={styles.topRow}>
        {/* Trajectory Score */}
        <div className={styles.gaugeWrap}>
          <h3>Trajectory Score</h3>
          <TrajectoryScoreGauge score={trajectory_score} level={risk_level} />
          <div className={styles.scoreStats}>
            <div className={styles.scoreStat}>
              <span className={styles.scoreStatNum}>{triggeredRules}</span>
              <span className={styles.scoreStatLabel}>Rules Triggered</span>
            </div>
            <div className={styles.scoreStat}>
              <span className={styles.scoreStatNum}>{worsening?.length ?? 0}</span>
              <span className={styles.scoreStatLabel}>Worsening Variables</span>
            </div>
            <div className={styles.scoreStat}>
              <span className={styles.scoreStatNum}>{clinical_flags?.length ?? 0}</span>
              <span className={styles.scoreStatLabel}>Clinical Flags</span>
            </div>
          </div>
        </div>

        {/* Biomarker Cards */}
        <div className={styles.biomarkersPanel}>
          <h3>Biomarker Trends</h3>
          <div className={styles.biomarkerGrid}>
            {Object.keys(trends ?? {}).map(concept => (
              <BiomarkerCard key={concept} concept={concept} data={trends[concept]} />
            ))}
          </div>
        </div>
      </div>

      {/* ── TIME SERIES CHART ── */}
      <section>
        <h3 className={styles.sectionTitle}>Longitudinal Trajectory</h3>
        <TimeSeriesChart timeline={timeline} trends={trends} />
      </section>

      {/* ── CROSS-VARIABLE PATTERNS ── */}
      {cross_patterns?.length > 0 && (
        <section>
          <h3 className={styles.sectionTitle}>Cross-Variable Interaction Patterns</h3>
          <ul className={styles.patternList}>
            {cross_patterns.map((p: string, i: number) => (
              <li key={i} className={styles.patternItem}>
                <span className={styles.patternDot}></span>
                {p}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── CLINICAL FLAGS ── */}
      {clinical_flags?.length > 0 && (
        <section>
          <h3 className={styles.sectionTitle}>Clinical Risk Flags</h3>
          <ul className={styles.flagList}>
            {clinical_flags.map((f: string, i: number) => (
              <li key={i} className={styles.flagItem}>
                <span className={styles.flagIcon}>⚠</span>
                {f}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── RULE EVALUATION ── */}
      <section>
        <h3 className={styles.sectionTitle}>Clinical Rule Evaluation (R001 – R007)</h3>
        <div className={styles.rulesGrid}>
          {(rules ?? []).map((rule: any) => (
            <RuleCard key={rule.rule_id} rule={rule} />
          ))}
        </div>
      </section>

      {/* ── AI REASONER ── */}
      <section>
        <AIReasonerPanel content={reasoning} loading={reasoningLoading} />
      </section>

      {/* ── CLINICAL CHATBOT ── */}
      <section>
        <PatientChatbot module="cardio" patientId={id} patientData={data} />
      </section>
    </div>
  );
}
