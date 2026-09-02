import { NextResponse } from 'next/server';
import { getNeo4jDriver, DEFAULT_DATABASE } from '@/lib/neo4j';
import { analyzePatientTrends } from '@/lib/temporalEngine';

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id: patientId } = await params;
  
  if (!patientId) {
    return NextResponse.json({ error: 'Patient ID is required' }, { status: 400 });
  }

  const driver = getNeo4jDriver();
  const session = driver.session(DEFAULT_DATABASE ? { database: DEFAULT_DATABASE } : undefined);
  
  try {
    const patientResult = await session.run(`
      MATCH (p:Patient {patient_id: $patientId})
      RETURN p.patient_id AS patient_id, p.age AS age, p.sex AS sex, p.t1d_duration AS t1d_duration
    `, { patientId });
    
    if (patientResult.records.length === 0) {
      return NextResponse.json({ error: 'Patient not found' }, { status: 404 });
    }
    
    const pAge = patientResult.records[0].get('age');
    const pT1d = patientResult.records[0].get('t1d_duration');
    
    const patient = {
      patient_id: patientResult.records[0].get('patient_id'),
      age: pAge?.toNumber ? pAge.toNumber() : pAge,
      sex: patientResult.records[0].get('sex'),
      t1d_duration: pT1d?.toNumber ? pT1d.toNumber() : pT1d,
    };

    const timelineResult = await session.run(`
      MATCH (p:Patient {patient_id: $patientId})-[:HAS_VISIT]->(v:Visit)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept)
      RETURN v.date AS date, c.name AS concept, m.value AS value, m.unit AS unit
      ORDER BY date
    `, { patientId });
    
    const timelineRaw: Record<string, Record<string, number>> = {};
    const timelineWithUnits: Record<string, Record<string, { value: number, unit: string }>> = {};
    
    for (const record of timelineResult.records) {
      // In neo4j js driver, dates might be objects depending on config, so we cast to string
      const dateObj = record.get('date');
      const date = dateObj.toString(); 
      const concept = record.get('concept');
      const rawValue = record.get('value');
      const value = rawValue?.toNumber ? rawValue.toNumber() : rawValue;
      const unit = record.get('unit');
      
      if (!timelineRaw[date]) {
        timelineRaw[date] = {};
        timelineWithUnits[date] = {};
      }
      
      timelineRaw[date][concept] = value;
      timelineWithUnits[date][concept] = { value, unit };
    }
    
    const { trends, patterns, patient_pattern } = analyzePatientTrends(timelineRaw);
    
    return NextResponse.json({
      patient,
      timeline: timelineWithUnits,
      trends,
      patterns,
      patient_pattern
    });
    
  } catch (error: any) {
    console.error('Error fetching patient timeline:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  } finally {
    await session.close();
  }
}
