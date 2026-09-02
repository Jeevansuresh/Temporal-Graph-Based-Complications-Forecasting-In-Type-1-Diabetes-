'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Heart } from 'lucide-react';
import styles from '../kidney/page.module.css';

export default function CardioIndexPage() {
  const [patients, setPatients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetch('/api/cardio/patients')
      .then(r => r.json())
      .then(data => {
        if (data.error) { setError(data.error); return; }
        setPatients(Array.isArray(data) ? data : []);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.moduleTag} style={{ color: 'var(--color-amber)' }}>
          <Heart size={18} />
          <span>Cardio Module</span>
        </div>
        <h2>Select a Patient</h2>
        <p className={styles.subtitle}>Choose a patient to view their Cardiovascular Disease risk analysis.</p>
      </header>

      {loading ? (
        <div className={styles.loading}>Loading patients from Neo4j...</div>
      ) : error ? (
        <div className={styles.error}><h3>Connection Error</h3><p>{error}</p></div>
      ) : patients.length === 0 ? (
        <div className={styles.empty}>No patients found in the Cardio database.</div>
      ) : (
        <div className={styles.grid}>
          {patients.map(p => (
            <button
              key={p.patient_id}
              className={styles.patientBtn}
              onClick={() => router.push(`/patients/${p.patient_id}/cardio`)}
            >
              <div className={styles.pid}>{p.patient_id}</div>
              <div className={styles.meta}>
                <span>{p.age}yo</span>
                <span>{p.sex}</span>
                <span>T1D {p.t1d_duration}y</span>
                {p.baseline_cvd_context && <span className={styles.ctx}>{p.baseline_cvd_context}</span>}
              </div>
              <div className={styles.arrow}>→</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
