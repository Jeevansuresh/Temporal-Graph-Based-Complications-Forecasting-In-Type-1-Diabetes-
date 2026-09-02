// TypeScript port of Cardio/temporal_engine.py + trajectory_analyzer.py logic

const DIRECTIONALITY: Record<string, string> = {
  Systolic_BP: 'higher_is_worse',
  Diastolic_BP: 'higher_is_worse',
  HbA1c: 'higher_is_worse',
  Fasting_Glucose: 'higher_is_worse',
  Random_Glucose: 'higher_is_worse',
  LDL_Cholesterol: 'higher_is_worse',
  HDL_Cholesterol: 'lower_is_worse',
  Triglycerides: 'higher_is_worse',
  Total_Cholesterol: 'higher_is_worse',
  Serum_Creatinine: 'higher_is_worse',
  UACR: 'higher_is_worse',
  eGFR: 'lower_is_worse',
  BNP_NTproBNP: 'higher_is_worse',
  BMI: 'higher_is_worse',
  Heart_Rate: 'higher_is_worse',
};

const SIGNIFICANT_CHANGE: Record<string, number> = {
  Systolic_BP: 0.05,
  Diastolic_BP: 0.05,
  HbA1c: 0.08,
  Fasting_Glucose: 0.10,
  Random_Glucose: 0.10,
  LDL_Cholesterol: 0.10,
  HDL_Cholesterol: 0.10,
  Triglycerides: 0.15,
  Total_Cholesterol: 0.10,
  Serum_Creatinine: 0.05,
  UACR: 0.20,
  eGFR: 0.05,
  BNP_NTproBNP: 0.20,
  BMI: 0.05,
  Heart_Rate: 0.10,
};

const SKIP_CONCEPTS = new Set([
  'date', 'visit_id', 'visit_date', 'visit_time', 'time', 'age', 'age_years',
  'sex', 't1d_duration', 't1d_duration_years', 'smoking_status', 'hypertension_status',
  'dyslipidemia', 'known_ascvd', 'known_cad', 'ecg_abnormality', 'cardiovascular_symptoms', 'clinical_action',
]);

function calcChange(values: number[]) {
  if (values.length < 2) return 0;
  return values[values.length - 1] - values[0];
}

function calcPctChange(values: number[]) {
  if (values.length < 2 || values[0] === 0) return 0;
  return ((values[values.length - 1] - values[0]) / Math.abs(values[0])) * 100;
}

function calcSlope(values: number[]) {
  if (values.length < 2) return 0;
  const n = values.length;
  const xMean = (n - 1) / 2;
  const yMean = values.reduce((a, b) => a + b, 0) / n;
  let num = 0, den = 0;
  for (let i = 0; i < n; i++) {
    num += (i - xMean) * (values[i] - yMean);
    den += (i - xMean) ** 2;
  }
  return den === 0 ? 0 : num / den;
}

function calcVariability(values: number[]) {
  if (values.length < 2) return 0;
  let sum = 0;
  for (let i = 1; i < values.length; i++) sum += Math.abs(values[i] - values[i - 1]);
  return sum / (values.length - 1);
}

function classifyDirection(concept: string, values: number[]) {
  if (values.length < 2) return 'INSUFFICIENT_DATA';
  const relChange = Math.abs(calcPctChange(values)) / 100;
  const threshold = SIGNIFICANT_CHANGE[concept] ?? 0.05;
  if (relChange < threshold) return 'STABLE';
  const change = calcChange(values);
  if (change > 0) return 'INCREASING';
  if (change < 0) return 'DECREASING';
  return 'STABLE';
}

function classifyMonotonicity(values: number[]) {
  if (values.length < 3) return 'INSUFFICIENT_DATA';
  let pos = 0, neg = 0;
  for (let i = 1; i < values.length; i++) {
    const d = values[i] - values[i - 1];
    if (d > 0) pos++;
    if (d < 0) neg++;
  }
  const total = values.length - 1;
  if (pos === total) return 'MONOTONIC_INCREASE';
  if (neg === total) return 'MONOTONIC_DECREASE';
  if (pos >= total - 1) return 'MOSTLY_INCREASING';
  if (neg >= total - 1) return 'MOSTLY_DECREASING';
  return 'MIXED';
}

function detectPersistence(values: number[], threshold: number, greaterThan = true) {
  const abnormal = values.map(v => greaterThan ? v >= threshold : v <= threshold);
  const count = abnormal.filter(Boolean).length;
  return {
    abnormal_count: count,
    total_count: values.length,
    persistent: count >= 2,
    all_recent_abnormal: values.length >= 2 ? (abnormal[abnormal.length - 1] && abnormal[abnormal.length - 2]) : false,
    latest_abnormal: abnormal.length > 0 ? abnormal[abnormal.length - 1] : false,
  };
}

function analyzeVariable(concept: string, values: number[]) {
  const direction = classifyDirection(concept, values);
  const result: any = {
    concept,
    values,
    first: values[0],
    latest: values[values.length - 1],
    direction,
    directionality: DIRECTIONALITY[concept] ?? 'higher_is_worse',
    monotonicity: classifyMonotonicity(values),
    absolute_change: parseFloat(calcChange(values).toFixed(4)),
    percentage_change: parseFloat(calcPctChange(values).toFixed(2)),
    slope: parseFloat(calcSlope(values).toFixed(4)),
    variability: parseFloat(calcVariability(values).toFixed(4)),
  };

  if (concept === 'UACR') result.persistence = detectPersistence(values, 30.0);
  else if (concept === 'Systolic_BP') result.persistence = detectPersistence(values, 130.0);
  else if (concept === 'Diastolic_BP') result.persistence = detectPersistence(values, 80.0);
  else if (concept === 'BNP_NTproBNP') result.persistence = detectPersistence(values, 100.0);
  else if (concept === 'eGFR') result.persistence = detectPersistence(values, 60.0, false);
  else if (concept === 'LDL_Cholesterol') result.persistence = detectPersistence(values, 100.0);

  return result;
}

export function calculateCardioTrends(timeline: Record<string, Record<string, any>>) {
  const dates = Object.keys(timeline).sort();
  if (!dates.length) return {};

  const conceptsSet = new Set<string>();
  for (const date of dates) {
    for (const key of Object.keys(timeline[date])) {
      if (!SKIP_CONCEPTS.has(key)) conceptsSet.add(key);
    }
  }

  const trends: Record<string, any> = {};
  for (const concept of Array.from(conceptsSet).sort()) {
    const values: number[] = [];
    for (const date of dates) {
      let val = timeline[date][concept];
      if (val !== undefined && val !== null) {
        if (typeof val === 'object' && 'value' in val) val = val.value;
        const f = parseFloat(val);
        if (!isNaN(f)) values.push(f);
      }
    }
    if (values.length > 0) trends[concept] = analyzeVariable(concept, values);
  }
  return trends;
}

export function determineWorseningVariables(trends: Record<string, any>): string[] {
  const worsening: string[] = [];
  for (const [concept, data] of Object.entries(trends)) {
    const dir = data.direction;
    const directionality = data.directionality ?? DIRECTIONALITY[concept] ?? 'higher_is_worse';
    const isWorse = directionality === 'lower_is_worse'
      ? ['DECREASING', 'MOSTLY_DECREASING'].includes(dir)
      : ['INCREASING', 'MOSTLY_INCREASING'].includes(dir);
    if (isWorse) worsening.push(concept);
  }
  return worsening;
}

export function detectCrossVariablePatterns(trends: Record<string, any>): string[] {
  const patterns: string[] = [];
  const sbp = trends['Systolic_BP'];
  const dbp = trends['Diastolic_BP'];
  const hba1c = trends['HbA1c'];
  const ldl = trends['LDL_Cholesterol'];
  const hdl = trends['HDL_Cholesterol'];
  const tg = trends['Triglycerides'];
  const uacr = trends['UACR'];
  const egfr = trends['eGFR'];
  const bnp = trends['BNP_NTproBNP'];

  if (sbp && dbp && ['INCREASING', 'MOSTLY_INCREASING'].includes(sbp.direction) && ['INCREASING', 'MOSTLY_INCREASING'].includes(dbp.direction))
    patterns.push('Concomitant systolic and diastolic blood pressure elevation across visits');

  if (ldl && hdl && ['INCREASING', 'MOSTLY_INCREASING'].includes(ldl.direction) && ['DECREASING', 'MOSTLY_DECREASING'].includes(hdl.direction))
    patterns.push('Atherogenic dyslipidemia progression (rising LDL-C concurrent with falling HDL-C)');
  else if (ldl && tg && ['INCREASING', 'MOSTLY_INCREASING'].includes(ldl.direction) && ['INCREASING', 'MOSTLY_INCREASING'].includes(tg.direction))
    patterns.push('Progressive lipid profile elevation (rising LDL-C and triglycerides)');

  if (hba1c && sbp && ['INCREASING', 'MOSTLY_INCREASING'].includes(hba1c.direction) && ['INCREASING', 'MOSTLY_INCREASING'].includes(sbp.direction))
    patterns.push('Glycemic deterioration accompanied by progressive systolic hypertension');

  if (uacr && egfr && ['INCREASING', 'MOSTLY_INCREASING'].includes(uacr.direction) && ['DECREASING', 'MOSTLY_DECREASING'].includes(egfr.direction))
    patterns.push('Cardiorenal microvascular progression (rising UACR with declining eGFR)');

  if (bnp && (sbp || uacr) && ['INCREASING', 'MOSTLY_INCREASING'].includes(bnp.direction) && bnp.latest > 100)
    patterns.push('Rising natriuretic peptide (BNP/NT-proBNP) signaling accelerating heart failure risk');

  return patterns;
}

export function classifyCardioPatientPattern(
  trends: Record<string, any>,
  crossPatterns: string[],
  baselineContext?: string
): string {
  if (baselineContext) {
    const ctx = baselineContext.toLowerCase();
    const hasNeg = ctx.includes('no ') || ctx.includes('without') || ctx.includes('none');
    const isSecondary = ['established ascvd', 'cad history', 'secondary', 'prior mi', 'documented cad', 'known ascvd/cad'].some(t => ctx.includes(t));
    if (isSecondary && !hasNeg) return 'ESTABLISHED_ASCVD_SECONDARY_PREVENTION_TRAJECTORY';
  }

  const bnp = trends['BNP_NTproBNP'];
  const sbp = trends['Systolic_BP'];
  const ldl = trends['LDL_Cholesterol'];
  const uacr = trends['UACR'];

  if (bnp && bnp.latest >= 100 && sbp && ['INCREASING', 'MOSTLY_INCREASING'].includes(sbp.direction))
    return 'ACCELERATING_CARDIOMETABOLIC_RISK_WITH_EMERGING_HF_CAD_SIGNALS';

  if ((sbp && sbp.latest >= 130) || (uacr && uacr.latest >= 30) || (ldl && ldl.latest >= 160))
    return 'PROGRESSIVE_HYPERTENSION_ALBUMINURIA_DYSLIPIDEMIA';

  const worsening = determineWorseningVariables(trends);
  if (!worsening.length || worsening.length <= 1) return 'STABLE_LOW_MODERATE_CARDIO_TRAJECTORY';

  return 'MULTIFACTORIAL_CARDIOVASCULAR_RISK_PROGRESSION';
}

export function generateClinicalFlags(trends: Record<string, any>, latestVisit: Record<string, any>): string[] {
  const flags: string[] = [];

  const sbp = trends['Systolic_BP'];
  if (sbp) {
    if (sbp.latest >= 130) flags.push(`Latest Systolic BP is hypertensive (>= 130 mmHg: ${sbp.latest} mmHg)`);
    if (['INCREASING', 'MOSTLY_INCREASING'].includes(sbp.direction)) flags.push('Systolic blood pressure is progressively increasing across visits');
  }

  const dbp = trends['Diastolic_BP'];
  if (dbp) {
    if (dbp.latest >= 80) flags.push(`Latest Diastolic BP is elevated (>= 80 mmHg: ${dbp.latest} mmHg)`);
    if (['INCREASING', 'MOSTLY_INCREASING'].includes(dbp.direction)) flags.push('Diastolic blood pressure is progressively increasing across visits');
  }

  const hba1c = trends['HbA1c'];
  if (hba1c) {
    if (hba1c.latest >= 8.0) flags.push(`Significantly elevated glycated hemoglobin (HbA1c ${hba1c.latest}%)`);
    if (['INCREASING', 'MOSTLY_INCREASING'].includes(hba1c.direction)) flags.push('Glycemic control is deteriorating longitudinally');
  }

  const ldl = trends['LDL_Cholesterol'];
  if (ldl) {
    if (ldl.latest >= 160) flags.push(`Markedly elevated LDL cholesterol (>= 160 mg/dL: ${ldl.latest} mg/dL)`);
    else if (ldl.latest >= 100) flags.push(`Elevated LDL cholesterol above optimal diabetes target (${ldl.latest} mg/dL)`);
    if (['INCREASING', 'MOSTLY_INCREASING'].includes(ldl.direction)) flags.push('LDL cholesterol is on an upward trajectory');
  }

  const hdl = trends['HDL_Cholesterol'];
  if (hdl && hdl.latest < 40) flags.push(`Low protective HDL cholesterol (${hdl.latest} mg/dL)`);

  const tg = trends['Triglycerides'];
  if (tg && tg.latest >= 150) flags.push(`Elevated fasting triglycerides (>= 150 mg/dL: ${tg.latest} mg/dL)`);

  const uacr = trends['UACR'];
  if (uacr) {
    if (uacr.latest >= 30) flags.push(`Persistent albuminuria / elevated UACR (${uacr.latest} mg/g)`);
    if (['INCREASING', 'MOSTLY_INCREASING'].includes(uacr.direction)) flags.push('UACR is steadily rising, indicating progressive cardiorenal stress');
  }

  const egfr = trends['eGFR'];
  if (egfr) {
    if (egfr.latest < 60) flags.push(`Reduced estimated GFR (< 60 mL/min/1.73m2: ${egfr.latest})`);
    else if (['DECREASING', 'MOSTLY_DECREASING'].includes(egfr.direction)) flags.push('eGFR shows longitudinal downward slope');
  }

  const bnp = trends['BNP_NTproBNP'];
  if (bnp) {
    if (bnp.latest >= 100) flags.push(`Elevated BNP/NT-proBNP (${bnp.latest} pg/mL) — increased heart failure risk`);
    if (['INCREASING', 'MOSTLY_INCREASING'].includes(bnp.direction)) flags.push('Natriuretic peptide levels are progressively rising');
  }

  const ecg = latestVisit['ecg_abnormality'];
  if (ecg && !['normal', 'none', ''].includes(ecg.toLowerCase()))
    flags.push(`Abnormal electrocardiogram finding: '${ecg}'`);

  const symptoms = latestVisit['cardiovascular_symptoms'];
  if (symptoms && !['no symptoms', 'none', ''].includes(symptoms.toLowerCase()))
    flags.push(`Active cardiovascular symptoms reported: '${symptoms}'`);

  const smoking = latestVisit['smoking_status'];
  if (smoking && ['yes', 'current', 'active'].includes(smoking.toLowerCase()))
    flags.push('Active tobacco smoking status (major independent CVD risk factor)');

  return flags;
}

export function evaluateRules(
  timeline: Record<string, Record<string, any>>,
  patientMeta: Record<string, any>
) {
  const dates = Object.keys(timeline).sort();
  const visits = dates.map(d => timeline[d]);
  const latestVisit = visits[visits.length - 1] ?? {};

  const safeFloat = (v: any) => { const f = parseFloat(v); return isNaN(f) ? null : f; };

  const sbpVals = visits.map(v => safeFloat(v['Systolic_BP'])).filter(v => v !== null) as number[];
  const dbpVals = visits.map(v => safeFloat(v['Diastolic_BP'])).filter(v => v !== null) as number[];
  const uacrVals = visits.map(v => safeFloat(v['UACR'])).filter(v => v !== null) as number[];
  const egfrVals = visits.map(v => safeFloat(v['eGFR'])).filter(v => v !== null) as number[];
  const bnpVals = visits.map(v => safeFloat(v['BNP_NTproBNP'])).filter(v => v !== null) as number[];

  const r001Satisfied = (sbpVals.length > 0 && sbpVals[sbpVals.length - 1] >= 130) ||
    (dbpVals.length > 0 && dbpVals[dbpVals.length - 1] >= 80);
  const r001Elevated = visits.filter((_, i) => (sbpVals[i] ?? 0) >= 130 || (dbpVals[i] ?? 0) >= 80).length;

  const r002Elevated = uacrVals.filter(v => v >= 30).length;
  const r002Satisfied = uacrVals.length >= 2 ? r002Elevated >= 2 : (uacrVals.length > 0 && uacrVals[uacrVals.length - 1] >= 30);

  const r003Reduced = egfrVals.filter(v => v < 60).length;
  const r003Satisfied = egfrVals.length >= 2 ? r003Reduced >= 2 : (egfrVals.length > 0 && egfrVals[egfrVals.length - 1] < 60);

  const r004Elevated = bnpVals.filter(v => v >= 100).length;
  const r004Satisfied = bnpVals.length > 0 && bnpVals[bnpVals.length - 1] >= 100;

  const knownAscvd = ['yes', 'true'].includes((latestVisit['known_ascvd'] ?? '').toString().toLowerCase());
  const knownCad = ['yes', 'true'].includes((latestVisit['known_cad'] ?? '').toString().toLowerCase());
  const ctx = (patientMeta['baseline_cvd_context'] ?? '').toLowerCase();
  const hasNeg = ctx.includes('no ') || ctx.includes('without') || ctx.includes('none');
  const metaAscvd = ['established', 'cad history', 'prior mi', 'documented cad'].some(k => ctx.includes(k)) && !hasNeg;
  const r006Satisfied = knownAscvd || knownCad || metaAscvd;

  const ecg = latestVisit['ecg_abnormality'] ?? '';
  const ecgAbnormal = ecg && !['normal', 'none', ''].includes(ecg.toLowerCase());
  const symptoms = latestVisit['cardiovascular_symptoms'] ?? '';
  const symptomsNeg = ['no symptoms', 'no acute', 'none', 'asymptomatic', 'denies'].some(n => symptoms.toLowerCase().includes(n));
  const r007Satisfied = ecgAbnormal || (symptoms && !symptomsNeg);

  return [
    { rule_id: 'R001', name: 'Hypertension Classification', trigger: 'Systolic_BP >= 130 mmHg OR Diastolic_BP >= 80 mmHg', satisfied: r001Satisfied, reason: `Latest BP: ${sbpVals.at(-1) ?? 'N/A'}/${dbpVals.at(-1) ?? 'N/A'} mmHg; elevated in ${r001Elevated}/${visits.length} visits` },
    { rule_id: 'R002', name: 'Albuminuria / Microvascular Risk', trigger: 'UACR >= 30 mg/g', satisfied: r002Satisfied, reason: `UACR >= 30 in ${r002Elevated}/${uacrVals.length} visits (Latest: ${uacrVals.at(-1) ?? 'N/A'} mg/g)` },
    { rule_id: 'R003', name: 'Chronic Kidney Disease Stage Assessment', trigger: 'eGFR < 60 mL/min/1.73m2', satisfied: r003Satisfied, reason: `eGFR < 60 in ${r003Reduced}/${egfrVals.length} visits (Latest: ${egfrVals.at(-1) ?? 'N/A'})` },
    { rule_id: 'R004', name: 'Heart Failure Biomarker Risk State', trigger: 'BNP_NTproBNP >= 100 pg/mL', satisfied: r004Satisfied, reason: `Latest natriuretic peptide: ${bnpVals.at(-1) ?? 'N/A'} pg/mL` },
    { rule_id: 'R005', name: 'Heart Failure Evaluation Indicated', trigger: 'Abnormal BNP_NTproBNP in diabetes context', satisfied: r004Satisfied, recommendation: 'Echocardiography recommended by ADA Standards of Care', reason: r004Satisfied ? 'Triggered due to elevated natriuretic peptide' : 'Natriuretic peptide within normal limits' },
    { rule_id: 'R006', name: 'Secondary Cardiovascular Prevention Context', trigger: 'T1D AND established_ASCVD = true', satisfied: r006Satisfied, reason: r006Satisfied ? 'Patient has documented established ASCVD / prior MI / CAD history' : 'No prior documented ASCVD event or established CAD' },
    { rule_id: 'R007', name: 'Coronary Investigation Considered', trigger: 'T1D AND (cardiac/vascular symptoms OR ECG_Abnormality)', satisfied: Boolean(r007Satisfied), ecg_finding: ecg || 'Normal', symptoms: symptoms || 'No symptoms', reason: r007Satisfied ? `Clinical findings: ECG='${ecg}', Symptoms='${symptoms}'` : 'Asymptomatic with normal ECG' },
  ];
}

export function calculateTrajectoryScore(trends: Record<string, any>, rules: ReturnType<typeof evaluateRules>): { score: number; level: string } {
  const ruleMap: Record<string, any> = {};
  for (const r of rules) ruleMap[r.rule_id] = r;

  let score = 0;
  if (ruleMap['R006']?.satisfied) score += 6;
  if (ruleMap['R001']?.satisfied) score += 2;
  if (['INCREASING', 'MOSTLY_INCREASING'].includes(trends['Systolic_BP']?.direction)) score += 1;
  if (ruleMap['R002']?.satisfied) score += 2;
  if (['INCREASING', 'MOSTLY_INCREASING'].includes(trends['UACR']?.direction)) score += 1;
  const ldlLatest = trends['LDL_Cholesterol']?.latest ?? 0;
  if (ldlLatest >= 160) score += 2;
  else if (ldlLatest >= 100) score += 1;
  if (['INCREASING', 'MOSTLY_INCREASING'].includes(trends['LDL_Cholesterol']?.direction)) score += 1;
  if ((trends['HbA1c']?.latest ?? 0) >= 8.0) score += 1;
  if (['INCREASING', 'MOSTLY_INCREASING'].includes(trends['HbA1c']?.direction)) score += 1;
  if (ruleMap['R004']?.satisfied) score += 3;
  else if (['INCREASING', 'MOSTLY_INCREASING'].includes(trends['BNP_NTproBNP']?.direction)) score += 1;
  if (ruleMap['R007']?.satisfied) score += 2;

  let level = 'LOW_CARDIOVASCULAR_RISK';
  if (ruleMap['R006']?.satisfied || score >= 9) level = 'VERY_HIGH_CARDIOVASCULAR_RISK';
  else if (score >= 6) level = 'HIGH_CARDIOVASCULAR_RISK';
  else if (score >= 3) level = 'MODERATE_CARDIOVASCULAR_RISK';

  return { score, level };
}
