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
  const session = driver.session(RETINOPATHY_DATABASE ? { database: RETINOPATHY_DATABASE } : undefined);

  try {
    // Patient meta — Retinopathy model stores t1d_diagnosis (date), not t1d_duration
    const metaResult = await session.run(
      `MATCH (p:Patient {patient_id: $patientId})
       RETURN p.patient_id AS patient_id, p.age AS age, p.sex AS sex,
              p.t1d_diagnosis AS t1d_diagnosis, p.puberty_status AS puberty_status`,
      { patientId }
    );

    if (!metaResult.records.length) {
      return NextResponse.json({ error: 'Patient not found' }, { status: 404 });
    }

    const pr = metaResult.records[0];
    const pAge = pr.get('age');
    const pT1dDiagnosis = pr.get('t1d_diagnosis'); // Neo4j Date object or string

    // Calculate t1d_duration in years from diagnosis date
    let t1dDurationYears: number | null = null;
    if (pT1dDiagnosis) {
      const diagStr = pT1dDiagnosis.toString(); // "YYYY-MM-DD"
      const diagYear = parseInt(diagStr.substring(0, 4), 10);
      const nowYear = new Date().getFullYear();
      t1dDurationYears = isNaN(diagYear) ? null : nowYear - diagYear;
    }

    const patientMeta = {
      patient_id: pr.get('patient_id'),
      age: pAge?.toNumber ? pAge.toNumber() : pAge,
      sex: pr.get('sex'),
      t1d_diagnosis: pT1dDiagnosis?.toString() ?? null,
      t1d_duration: t1dDurationYears,
      puberty_status: pr.get('puberty_status'),
    };

    // Fetch numeric measurements (all non-retinal concepts)
    const numericResult = await session.run(
      `MATCH (p:Patient {patient_id: $patientId})-[:HAS_VISIT]->(v:Visit)
       OPTIONAL MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept)
       WHERE c.name <> 'Retinopathy_Stage'
       RETURN v.date AS date, c.name AS concept, m.value AS value
       ORDER BY v.date, c.name`,
      { patientId }
    );

    // Fetch retinal measurements separately (stage_index stored on Measurement node)
    const retinalResult = await session.run(
      `MATCH (p:Patient {patient_id: $patientId})-[:HAS_VISIT]->(v:Visit)
       MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept {name: 'Retinopathy_Stage'})
       RETURN v.date AS date, m.stage_index AS stage_index
       ORDER BY v.date`,
      { patientId }
    );

    // All visit dates
    const datesSet = new Set<string>();
    const timelineRaw: Record<string, Record<string, number>> = {};

    for (const record of numericResult.records) {
      const date = record.get('date')?.toString();
      if (!date) continue;
      datesSet.add(date);

      const concept = record.get('concept');
      if (!concept) continue;

      const rawVal = record.get('value');
      const value = rawVal?.toNumber ? rawVal.toNumber() : rawVal;

      if (!timelineRaw[date]) timelineRaw[date] = {};
      if (value !== null && value !== undefined) {
        timelineRaw[date][concept] = value;
      }
    }

    // Collect retinal observations and add their visit dates
    const observations: { date: string; stage_index: number }[] = [];
    for (const record of retinalResult.records) {
      const date = record.get('date')?.toString();
      if (!date) continue;
      datesSet.add(date);

      const rawIdx = record.get('stage_index');
      const stageIndex = rawIdx?.toNumber ? rawIdx.toNumber() : rawIdx;
      if (stageIndex !== null && stageIndex !== undefined) {
        observations.push({ date, stage_index: stageIndex });
      }
    }

    const allDates = Array.from(datesSet).sort();
    const retinalTrajectory = analyzeRetinalTrajectory(allDates, observations);

    const numericFeatures: Record<string, any> = {};
    for (const concept of ['HbA1c', 'Systolic_BP', 'Diastolic_BP', 'LDL', 'UACR', 'eGFR']) {
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
