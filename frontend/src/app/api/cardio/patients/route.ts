import { NextResponse } from 'next/server';
import { getCardioDriver, CARDIO_DATABASE } from '@/lib/neo4jCardio';

export async function GET() {
  const driver = getCardioDriver();
  const session = driver.session(CARDIO_DATABASE ? { database: CARDIO_DATABASE } : undefined);

  try {
    const result = await session.run(`
      MATCH (p:Patient)
      RETURN p.patient_id AS patient_id, p.age AS age, p.sex AS sex,
             p.t1d_duration AS t1d_duration,
             p.baseline_cvd_context AS baseline_cvd_context,
             p.temporal_pattern AS temporal_pattern
      ORDER BY patient_id
    `);

    const patients = result.records.map((r: any) => {
      const age = r.get('age');
      const t1d = r.get('t1d_duration');
      return {
        patient_id: r.get('patient_id'),
        age: age?.toNumber ? age.toNumber() : age,
        sex: r.get('sex'),
        t1d_duration: t1d?.toNumber ? t1d.toNumber() : t1d,
        baseline_cvd_context: r.get('baseline_cvd_context'),
        temporal_pattern: r.get('temporal_pattern'),
      };
    });

    return NextResponse.json(patients);
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  } finally {
    await session.close();
  }
}
