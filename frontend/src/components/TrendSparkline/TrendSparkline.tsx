'use client';
import { LineChart, Line, YAxis, ResponsiveContainer } from 'recharts';

export default function TrendSparkline({ data, dataKey, color }: { data: any[]; dataKey: string; color: string }) {
  if (!data || data.length === 0) return <div style={{ height: '30px', width: '60px' }} />;
  
  return (
    <div style={{ height: '30px', width: '60px' }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <YAxis domain={['dataMin - 1', 'dataMax + 1']} hide />
          <Line 
            type="monotone" 
            dataKey={dataKey} 
            stroke={color} 
            strokeWidth={2} 
            dot={false}
            isAnimationActive={true}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
