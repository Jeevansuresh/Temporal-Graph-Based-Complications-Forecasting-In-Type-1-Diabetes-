import { NextResponse } from 'next/server';
import { getCardioDriver, CARDIO_DATABASE } from '@/lib/neo4jCardio';
import {
  calculateCardioTrends,
  determineWorseningVariables,
  detectCrossVariablePatterns,
  classifyCardioPatientPattern,
  generateClinicalFlags,
  evaluateRules,
  calculateTrajectoryScore,
} from '@/lib/cardioTemporalEngine';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: patientId } = await params;
  const driver = getCardioDriver();
  const session = driver.session({ database: CARDIO_DATABASE });

  try {
    // Patient metadata
    const metaResult = await session.run(
      `MATCH (p:Patient {patient_id: $patientId})
       RETURN p.patient_id AS patient_id, p.age AS age, p.sex AS sex,
              p.t1d_duration AS t1d_duration,
              p.baseline_cvd_context AS baseline_cvd_context,
              p.temporal_pattern AS temporal_pattern`,
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
      baseline_cvd_context: pr.get('baseline_cvd_context'),
      temporal_pattern: pr.get('temporal_pattern'),
    };

    // Timeline
    const visitResult = await session.run(
      `MATCH (p:Patient {patient_id: $patientId})-[:HAS_VISIT]->(v:Visit)
       OPTIONAL MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept)
       RETURN
         v.visit_id AS visit_id,
         v.date AS date,
         v.smoking_status AS smoking_status,
         v.hypertension_status AS hypertension_status,
         v.dyslipidemia AS dyslipidemia,
         v.known_ascvd AS known_ascvd,
         v.known_cad AS known_cad,
         v.ecg_abnormality AS ecg_abnormality,
         v.cardiovascular_symptoms AS cardiovascular_symptoms,
         v.clinical_action AS clinical_action,
         c.name AS concept,
         m.value AS value,
         m.unit AS unit
       ORDER BY v.date, c.name`,
      { patientId }
    );

    // Build timeline dict keyed by date string
    const timeline: Record<string, Record<string, any>> = {};
    for (const record of visitResult.records) {
      const dateObj = record.get('date');
      const date = dateObj?.toString() ?? 'unknown';

      if (!timeline[date]) {
        timeline[date] = {
          date,
          visit_id: record.get('visit_id'),
          smoking_status: record.get('smoking_status'),
          hypertension_status: record.get('hypertension_status'),
          dyslipidemia: record.get('dyslipidemia'),
          known_ascvd: record.get('known_ascvd'),
          known_cad: record.get('known_cad'),
          ecg_abnormality: record.get('ecg_abnormality'),
          cardiovascular_symptoms: record.get('cardiovascular_symptoms'),
          clinical_action: record.get('clinical_action'),
        };
      }

      const concept = record.get('concept');
      if (concept) {
        const rawVal = record.get('value');
        const value = rawVal?.toNumber ? rawVal.toNumber() : rawVal;
        const unit = record.get('unit');
        timeline[date][concept] = { value, unit };
      }
    }

    // Analysis
    const trends = calculateCardioTrends(timeline);
    const worsening = determineWorseningVariables(trends);
    const crossPatterns = detectCrossVariablePatterns(trends);
    const patientPattern = classifyCardioPatientPattern(trends, crossPatterns, patientMeta.baseline_cvd_context ?? undefined);
    const rules = evaluateRules(timeline, patientMeta);
    const { score, level: riskLevel } = calculateTrajectoryScore(trends, rules);

    const dates = Object.keys(timeline).sort();
    const latestVisit = timeline[dates[dates.length - 1]] ?? {};
    const flags = generateClinicalFlags(trends, latestVisit);

    return NextResponse.json({
      patient: patientMeta,
      timeline,
      trends,
      worsening,
      cross_patterns: crossPatterns,
      patient_pattern: patientPattern,
      rules,
      trajectory_score: score,
      risk_level: riskLevel,
      clinical_flags: flags,
    });
  } catch (error: any) {
    console.error('Cardio patient detail error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  } finally {
    await session.close();
  }
}
