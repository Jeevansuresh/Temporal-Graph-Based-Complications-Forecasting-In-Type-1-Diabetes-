'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Activity } from 'lucide-react';
import styles from './page.module.css';

export default function KidneyIndexPage() {
  const [patients, setPatients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetch('/api/patients')
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
        <div className={styles.moduleTag}>
          <Activity size={18} />
          <span>Kidney Module</span>
        </div>
        <h2>Select a Patient</h2>
        <p className={styles.subtitle}>Choose a patient from the cohort to view their Kidney (Nephropathy) analysis.</p>
      </header>

      {loading ? (
        <div className={styles.loading}>Loading patients from Neo4j...</div>
      ) : error ? (
        <div className={styles.error}><h3>Connection Error</h3><p>{error}</p></div>
      ) : patients.length === 0 ? (
        <div className={styles.empty}>No patients found in the Kidney database.</div>
      ) : (
        <div className={styles.grid}>
          {patients.map(p => (
            <button
              key={p.patient_id}
              className={styles.patientBtn}
              onClick={() => router.push(`/patients/${p.patient_id}/kidney`)}
            >
              <div className={styles.pid}>{p.patient_id}</div>
              <div className={styles.meta}>
                <span>{p.age}yo</span>
                <span>{p.sex}</span>
                <span>T1D {p.t1d_duration}y</span>
              </div>
              <div className={styles.arrow}>→</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
