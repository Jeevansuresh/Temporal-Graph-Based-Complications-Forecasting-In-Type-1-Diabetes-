import { NextResponse } from 'next/server';
import { getRetinopathyDriver, RETINOPATHY_DATABASE } from '@/lib/neo4jRetinopathy';
import {
  analyzeRetinalTrajectory,
  analyzeNumericSeries,
  evaluateRetinopathyRules,
  aggregateRiskState
} from '@/lib/retinopathyTemporalEngine';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: patientId } = await params;
  const driver = getRetinopathyDriver();
  const session = driver.session({ database: RETINOPATHY_DATABASE });

  try {
    const metaResult = await session.run(
      `MATCH (p:Patient {patient_id: $patientId})
       RETURN p.patient_id AS patient_id, p.age AS age, p.sex AS sex,
              p.t1d_duration AS t1d_duration, p.puberty_status AS puberty_status`,
      { patientId }
    );

    if (!metaResult.records.length) {
      return NextResponse.json({ error: 'Patient not found' }, { status: 404 });
    }

    const pr = metaResult.records[0];
    const pAge = pr.get('age');
    const pT1d = pr.get('t1d_duration');
    const patientMeta = {
      patient_id: pr.get('patient_id'),
      age: pAge?.toNumber ? pAge.toNumber() : pAge,
      sex: pr.get('sex'),
      t1d_duration: pT1d?.toNumber ? pT1d.toNumber() : pT1d,
      puberty_status: pr.get('puberty_status'),
    };

    const visitResult = await session.run(
      `MATCH (p:Patient {patient_id: $patientId})-[:HAS_VISIT]->(v:Visit)
       OPTIONAL MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept)
       RETURN v.date AS date, c.name AS concept, m.value AS value
       ORDER BY v.date, c.name`,
      { patientId }
    );

    const datesSet = new Set<string>();
    const observations: { date: string; stage_index: number }[] = [];
    const timelineRaw: Record<string, Record<string, number>> = {};

    for (const record of visitResult.records) {
      const date = record.get('date')?.toString();
      if (!date) continue;
      datesSet.add(date);

      const concept = record.get('concept');
      if (!concept) continue;

      const rawVal = record.get('value');
      const value = rawVal?.toNumber ? rawVal.toNumber() : rawVal;

      if (!timelineRaw[date]) timelineRaw[date] = {};
      timelineRaw[date][concept] = value;

      if (concept === 'retinal_stage_index') {
        observations.push({ date, stage_index: value });
      }
    }

    const allDates = Array.from(datesSet).sort();
    const retinalTrajectory = analyzeRetinalTrajectory(allDates, observations);

    const numericFeatures: Record<string, any> = {};
    for (const concept of ['HbA1c', 'Systolic_BP', 'Diastolic_BP', 'LDL', 'UACR', 'eGFR', 'T1D_Duration']) {
      const vals: number[] = [];
      for (const d of allDates) {
        if (timelineRaw[d] && typeof timelineRaw[d][concept] === 'number') {
          vals.push(timelineRaw[d][concept]);
        }
      }
      if (vals.length > 0) {
        numericFeatures[concept] = analyzeNumericSeries(concept, vals);
      }
    }

    const profile = {
      context: patientMeta,
      retinal_trajectory: retinalTrajectory,
      numeric_features: numericFeatures,
    };

    const rules = evaluateRetinopathyRules(profile);
    const { state: riskState, reason: riskReason } = aggregateRiskState(rules, retinalTrajectory.n_observed);

    return NextResponse.json({
      patient: patientMeta,
      profile,
      rules: Object.values(rules),
      risk_state: riskState,
      risk_reason: riskReason,
    });
  } catch (error: any) {
    console.error('Retinopathy patient detail error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  } finally {
    await session.close();
  }
}
