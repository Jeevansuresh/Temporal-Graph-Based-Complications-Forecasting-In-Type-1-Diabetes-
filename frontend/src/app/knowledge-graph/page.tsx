'use client';
import { useState, useEffect } from 'react';
import KGExplorer from '@/components/KGExplorer/KGExplorer';
import styles from './page.module.css';

const TABS = [
  { id: 'kidney', label: 'Kidney Module' },
  { id: 'cardio', label: 'Cardio Module' },
  { id: 'retinopathy', label: 'Retinopathy Module' },
];

export default function KnowledgeGraphPage() {
  const [activeTab, setActiveTab] = useState('kidney');
  const [graphData, setGraphData] = useState<{ nodes: any[], links: any[] }>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadKG() {
      setLoading(true);
      setError(null);
      try {
        // Here we could pass the tab as a parameter, e.g. /api/kg?module=kidney
        // Since we only have one KG in neo4j now, this will fetch the main one for all tabs,
        // but it sets up the structure requested by the user.
        const res = await fetch(`/api/kg/${activeTab}`);
        const data = await res.json();
        
        if (data.error) {
          setError(data.error);
        } else {
          setGraphData(data);
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    
    loadKG();
  }, [activeTab]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h2>Clinical Knowledge Graphs</h2>
        <div className={styles.tabs}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`${styles.tabBtn} ${activeTab === tab.id ? styles.active : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>
      
      <div className={styles.content}>
        {loading ? (
          <div className={styles.message}>Loading graph data...</div>
        ) : error ? (
          <div className={styles.error}>Error: {error}</div>
        ) : graphData.nodes.length === 0 ? (
          <div className={styles.message}>No graph data found for this module.</div>
        ) : (
          <KGExplorer nodes={graphData.nodes} links={graphData.links} />
        )}
      </div>
    </div>
  );
}
