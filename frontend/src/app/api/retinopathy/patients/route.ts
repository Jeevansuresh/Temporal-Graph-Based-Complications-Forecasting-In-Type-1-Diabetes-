import { NextResponse } from 'next/server';
import { getRetinopathyDriver, RETINOPATHY_DATABASE } from '@/lib/neo4jRetinopathy';
import path from 'path';
import fs from 'fs';

export async function GET() {
  try {
    const driver = getRetinopathyDriver();
    const session = driver.session(RETINOPATHY_DATABASE ? { database: RETINOPATHY_DATABASE } : undefined);

    try {
      const result = await session.run(`
        MATCH (p:Patient)
        RETURN p.patient_id AS patient_id, p.age AS age, p.sex AS sex,
               p.t1d_duration AS t1d_duration, p.puberty_status AS puberty_status
        ORDER BY patient_id
      `);

      if (result.records.length > 0) {
        const patients = result.records.map((r: any) => {
          const age = r.get('age');
          const t1d = r.get('t1d_duration');
          return {
            patient_id: r.get('patient_id'),
            age: age?.toNumber ? age.toNumber() : age,
            sex: r.get('sex'),
            t1d_duration: t1d?.toNumber ? t1d.toNumber() : t1d,
            puberty_status: r.get('puberty_status'),
          };
        });

        return NextResponse.json(patients);
      }
    } finally {
      await session.close();
    }
  } catch (error: any) {
    console.warn('Retinopathy Neo4j connection failed, falling back to synthetic_cases.json:', error.message);
  }

  // Fallback to Retinopathy/synthetic_cases.json
  const jsonPath = path.resolve(process.cwd(), '../Retinopathy/synthetic_cases.json');
  if (fs.existsSync(jsonPath)) {
    const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
    const nowYear = new Date().getFullYear();
    const patients = data.cases.map((c: any) => {
      const diagYear = parseInt((c.t1d_diagnosis || '').substring(0, 4), 10);
      return {
        patient_id: c.id,
        age: c.age,
        sex: c.sex,
        t1d_duration: isNaN(diagYear) ? null : nowYear - diagYear,
        puberty_status: c.puberty_status,
        description: c.description,
      };
    });
    return NextResponse.json(patients);
  }

  return NextResponse.json({ error: 'Retinopathy database unavailable and synthetic_cases.json not found' }, { status: 500 });
}
