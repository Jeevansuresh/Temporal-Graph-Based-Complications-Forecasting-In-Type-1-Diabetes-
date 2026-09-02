'use client';
import { useEffect, useState } from 'react';
import PatientCard from '@/components/PatientCard/PatientCard';
import styles from './page.module.css';

export default function PatientsPage() {
  const [patients, setPatients] = useState<any[]>([]);
  const [patientData, setPatientData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetch('/api/patients');
        const list = await res.json();
        
        if (list.error) {
          setError(list.error);
          setPatients([]);
          return;
        }
        
        setPatients(list);

        // Fetch details for each to get trends/sparklines
        const details: Record<string, any> = {};
        for (const p of list) {
          const detailRes = await fetch(`/api/patients/${p.patient_id}`);
          details[p.patient_id] = await detailRes.json();
        }
        setPatientData(details);
      } catch (err: any) {
        console.error(err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h2>Patient Cohort</h2>
        <div className={styles.filters}>
          <button className={styles.filterBtn}>All Patients</button>
          <button className={styles.filterBtn}>High Risk</button>
          <button className={styles.filterBtn}>Stable</button>
        </div>
      </header>
      
      {loading ? (
        <div className={styles.loading}>Loading cohort data from Neo4j...</div>
      ) : error ? (
        <div className={styles.error} style={{ color: 'var(--color-red)', padding: '2rem', textAlign: 'center', backgroundColor: 'rgba(239, 68, 68, 0.05)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-red)', marginTop: '2rem' }}>
          <h3>Error loading patients</h3>
          <p>{error}</p>
        </div>
      ) : patients.length === 0 ? (
        <div className={styles.message} style={{ padding: '2rem', textAlign: 'center', color: 'var(--color-text-muted)' }}>No patients found.</div>
      ) : (
        <div className={styles.grid}>
          {patients.map(p => (
            <div key={p.patient_id} className={styles.fadeItem}>
              <PatientCard 
                patient={p} 
                timeline={patientData[p.patient_id]?.timeline}
                trends={patientData[p.patient_id]?.trends}
                patientPattern={patientData[p.patient_id]?.patient_pattern}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
