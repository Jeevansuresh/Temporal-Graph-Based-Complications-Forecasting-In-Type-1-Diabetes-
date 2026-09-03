import { NextResponse } from 'next/server';
import { getRetinopathyDriver, RETINOPATHY_DATABASE } from '@/lib/neo4jRetinopathy';
import {
  analyzeRetinalTrajectory,
  analyzeNumericSeries,
  evaluateRetinopathyRules,
  aggregateRiskState
} from '@/lib/retinopathyTemporalEngine';
import path from 'path';
import fs from 'fs';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: patientId } = await params;

  try {
    const driver = getRetinopathyDriver();
    const session = driver.session(RETINOPATHY_DATABASE ? { database: RETINOPATHY_DATABASE } : undefined);

    try {
      const metaResult = await session.run(
        `MATCH (p:Patient {patient_id: $patientId})
         RETURN p.patient_id AS patient_id, p.age AS age, p.sex AS sex,
                p.t1d_diagnosis AS t1d_diagnosis, p.puberty_status AS puberty_status`,
        { patientId }
      );

      if (metaResult.records.length > 0) {
        const pr = metaResult.records[0];
        const pAge = pr.get('age');
        const pT1dDiagnosis = pr.get('t1d_diagnosis');

        let t1dDurationYears: number | null = null;
        if (pT1dDiagnosis) {
          const diagStr = pT1dDiagnosis.toString();
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

        const numericResult = await session.run(
          `MATCH (p:Patient {patient_id: $patientId})-[:HAS_VISIT]->(v:Visit)
           OPTIONAL MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept)
           WHERE c.name <> 'Retinopathy_Stage'
           RETURN v.date AS date, c.name AS concept, m.value AS value
           ORDER BY v.date, c.name`,
          { patientId }
        );

        const retinalResult = await session.run(
          `MATCH (p:Patient {patient_id: $patientId})-[:HAS_VISIT]->(v:Visit)
           MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept {name: 'Retinopathy_Stage'})
           RETURN v.date AS date, m.stage_index AS stage_index
           ORDER BY v.date`,
          { patientId }
        );

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
      }
    } finally {
      await session.close();
    }
  } catch (error: any) {
    console.warn('Retinopathy Neo4j detail fetch failed, falling back to synthetic_cases.json:', error.message);
  }

  // Fallback to Retinopathy/synthetic_cases.json
  const jsonPath = path.resolve(process.cwd(), '../Retinopathy/synthetic_cases.json');
  if (fs.existsSync(jsonPath)) {
    const fileData = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
    const caseData = fileData.cases.find((c: any) => c.id === patientId);
    if (!caseData) {
      return NextResponse.json({ error: 'Patient not found' }, { status: 404 });
    }

    const nowYear = new Date().getFullYear();
    const diagYear = parseInt((caseData.t1d_diagnosis || '').substring(0, 4), 10);
    const t1dDurationYears = isNaN(diagYear) ? null : nowYear - diagYear;

    const patientMeta = {
      patient_id: caseData.id,
      age: caseData.age,
      sex: caseData.sex,
      t1d_diagnosis: caseData.t1d_diagnosis,
      t1d_duration: t1dDurationYears,
      puberty_status: caseData.puberty_status,
      description: caseData.description,
    };

    const timelineRaw: Record<string, Record<string, number>> = {};
    const observations: { date: string; stage_index: number }[] = [];
    const datesSet = new Set<string>();

    for (const visit of caseData.timeline || []) {
      const date = visit.date;
      if (!date) continue;
      datesSet.add(date);
      if (!timelineRaw[date]) timelineRaw[date] = {};

      if (visit.hba1c !== undefined && visit.hba1c !== null) timelineRaw[date]['HbA1c'] = visit.hba1c;
      if (visit.sbp !== undefined && visit.sbp !== null) timelineRaw[date]['Systolic_BP'] = visit.sbp;
      if (visit.dbp !== undefined && visit.dbp !== null) timelineRaw[date]['Diastolic_BP'] = visit.dbp;
      if (visit.ldl !== undefined && visit.ldl !== null) timelineRaw[date]['LDL'] = visit.ldl;
      if (visit.uacr !== undefined && visit.uacr !== null) timelineRaw[date]['UACR'] = visit.uacr;
      if (visit.egfr !== undefined && visit.egfr !== null) timelineRaw[date]['eGFR'] = visit.egfr;

      if (visit.retinal_stage !== undefined && visit.retinal_stage !== null) {
        observations.push({ date, stage_index: visit.retinal_stage });
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
  }

  return NextResponse.json({ error: 'Patient data unavailable' }, { status: 500 });
}
