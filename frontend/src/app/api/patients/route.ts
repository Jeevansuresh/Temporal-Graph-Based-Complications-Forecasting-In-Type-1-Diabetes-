import { NextResponse } from 'next/server';
import { getNeo4jDriver, DEFAULT_DATABASE } from '@/lib/neo4j';

export async function GET() {
  const driver = getNeo4jDriver();
  const session = driver.session(DEFAULT_DATABASE ? { database: DEFAULT_DATABASE } : undefined);
  
  try {
    const result = await session.run(`
      MATCH (p:Patient)
      RETURN p.patient_id AS patient_id, p.age AS age, p.sex AS sex, p.t1d_duration AS t1d_duration
      ORDER BY patient_id
    `);
    
    const patients = result.records.map((record: any) => {
      const age = record.get('age');
      const t1d_duration = record.get('t1d_duration');
      
      return {
        patient_id: record.get('patient_id'),
        age: age?.toNumber ? age.toNumber() : age,
        sex: record.get('sex'),
        t1d_duration: t1d_duration?.toNumber ? t1d_duration.toNumber() : t1d_duration,
      };
    });
    
    return NextResponse.json(patients);
  } catch (error: any) {
    console.error('Error fetching patients:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  } finally {
    await session.close();
  }
}
