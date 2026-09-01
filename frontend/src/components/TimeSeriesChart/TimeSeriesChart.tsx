'use client';
import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import styles from './TimeSeriesChart.module.css';

const COLORS: Record<string, string> = {
  HbA1c: '#F59E0B',
  UACR: '#EF4444',
  eGFR: '#10B981',
  Systolic_BP: '#00D4FF',
  Diastolic_BP: '#8b949e',
  CGM_Time_in_Range: '#a78bfa',
  Serum_Creatinine: '#f472b6',
};

export default function TimeSeriesChart({ timeline, trends }: { timeline: any; trends: any }) {
  const [visibleLines, setVisibleLines] = useState<Record<string, boolean>>({
    HbA1c: true,
    UACR: true,
    eGFR: true,
    Systolic_BP: true,
    CGM_Time_in_Range: true,
  });

  const toggleLine = (key: string) => {
    setVisibleLines(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const dates = Object.keys(timeline || {}).sort();
  if (dates.length === 0) return <div>No data</div>;

  const data = dates.map(date => {
    const point: any = { name: date };
    for (const key of Object.keys(timeline[date])) {
      point[key] = timeline[date][key].value;
    }
    return point;
  });

  const lines = Object.keys(timeline[dates[0]]);

  return (
    <div className={styles.container}>
      <div className={styles.controls}>
        {lines.map(key => (
          <button 
            key={key} 
            className={`${styles.toggleBtn} ${visibleLines[key] ? styles.active : ''}`}
            onClick={() => toggleLine(key)}
            style={{ borderColor: visibleLines[key] ? COLORS[key] : 'var(--color-border-subtle)' }}
          >
            <span className={styles.dot} style={{ backgroundColor: COLORS[key] }}></span>
            {key.replace(/_/g, ' ')}
          </button>
        ))}
      </div>
      
      <div className={styles.chartWrapper}>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-subtle)" vertical={false} />
            <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={12} tickMargin={10} />
            <YAxis stroke="var(--color-text-muted)" fontSize={12} />
            <Tooltip 
              contentStyle={{ backgroundColor: 'var(--color-bg-surface-elevated)', borderColor: 'var(--color-border-strong)', borderRadius: '8px', color: 'var(--color-text-primary)' }}
              itemStyle={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}
            />
            
            {visibleLines['UACR'] && <ReferenceLine y={30} stroke="var(--color-amber)" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Albuminuria Threshold (30)', fill: 'var(--color-amber)', fontSize: 12 }} />}
            {visibleLines['HbA1c'] && <ReferenceLine y={7.0} stroke="var(--color-text-muted)" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'HbA1c Target (7.0%)', fill: 'var(--color-text-muted)', fontSize: 12 }} />}
            
            {lines.map(key => visibleLines[key] && (
              <Line 
                key={key}
                type="monotone" 
                dataKey={key} 
                stroke={COLORS[key] || '#fff'} 
                strokeWidth={2}
                dot={{ r: 4, strokeWidth: 2 }}
                activeDot={{ r: 6 }}
                isAnimationActive={true}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
