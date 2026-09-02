export const STAGE_INDEX_TO_CONCEPT: Record<number, string> = {
  0: 'No_DR',
  1: 'Mild_NPDR',
  2: 'Moderate_NPDR',
  3: 'Severe_NPDR',
  4: 'PDR',
};

const STABLE = 'STABLE';
const PROGRESSION = 'PROGRESSION';
const INCIDENT_PROGRESSION = 'INCIDENT_PROGRESSION';
const IMPROVEMENT = 'IMPROVEMENT';
const INSUFFICIENT_DATA = 'INSUFFICIENT_DATA';

// Constants
const ADA_ELEVATED_UACR_MG_PER_G = 30;
const ADA_PEDIATRIC_T1D_LDL_GOAL_MG_DL = 100;
const PEDIATRIC_ADULT_BP_CATEGORY_AGE_YEARS = 13;
const ELEVATED_SBP_MMHG = 120;
const ELEVATED_DBP_MMHG = 80;

export function classifyTransition(prevIdx: number, currIdx: number) {
  if (currIdx === prevIdx) return STABLE;
  if (currIdx > prevIdx) return prevIdx === 0 ? INCIDENT_PROGRESSION : PROGRESSION;
  return IMPROVEMENT;
}

export function analyzeRetinalTrajectory(allDates: string[], observed: { date: string; stage_index: number }[]) {
  const allVisitDates = [...allDates].sort();
  const sortedObs = [...observed].sort((a, b) => a.date.localeCompare(b.date));
  const obsDates = sortedObs.map((o) => o.date);
  const missingDates = allVisitDates.filter((d) => !obsDates.includes(d));

  const transitions = [];
  for (let i = 0; i < sortedObs.length - 1; i++) {
    const prev = sortedObs[i];
    const curr = sortedObs[i + 1];
    transitions.push({
      from_date: prev.date,
      to_date: curr.date,
      from_stage_index: prev.stage_index,
      to_stage_index: curr.stage_index,
      transition_type: classifyTransition(prev.stage_index, curr.stage_index),
      observation_gap: missingDates.some((d) => d > prev.date && d < curr.date),
    });
  }

  const latestVisitDate = allVisitDates.length > 0 ? allVisitDates[allVisitDates.length - 1] : null;
  const latestVisitHasObservation = obsDates.length > 0 && obsDates[obsDates.length - 1] === latestVisitDate;
  const visitsSinceLastObs = obsDates.length > 0
    ? allVisitDates.filter((d) => d > obsDates[obsDates.length - 1]).length
    : null;

  const overallTransitionType = transitions.length > 0 ? transitions[transitions.length - 1].transition_type : INSUFFICIENT_DATA;

  return {
    n_visits_total: allVisitDates.length,
    n_observed: sortedObs.length,
    missing_visit_dates: missingDates,
    observed_dates: obsDates,
    observed_stage_indices: sortedObs.map((o) => o.stage_index),
    transitions,
    latest_observed_date: obsDates.length > 0 ? obsDates[obsDates.length - 1] : null,
    latest_observed_stage_index: sortedObs.length > 0 ? sortedObs[sortedObs.length - 1].stage_index : null,
    latest_observed_stage_label: sortedObs.length > 0 ? STAGE_INDEX_TO_CONCEPT[sortedObs[sortedObs.length - 1].stage_index] : null,
    latest_visit_date: latestVisitDate,
    latest_visit_has_observation: latestVisitHasObservation,
    visits_since_last_observation: visitsSinceLastObs,
    overall_transition_type: overallTransitionType,
    any_progression_observed: transitions.some((t) => [PROGRESSION, INCIDENT_PROGRESSION].includes(t.transition_type)),
    any_improvement_observed: transitions.some((t) => t.transition_type === IMPROVEMENT),
  };
}

export function analyzeNumericSeries(concept: string, values: number[]) {
  const calculateAbsoluteChange = (v: number[]) => (v.length < 2 ? null : v[v.length - 1] - v[0]);
  const calculatePercentChange = (v: number[]) => (v.length < 2 || v[0] === 0 ? null : ((v[v.length - 1] - v[0]) / Math.abs(v[0])) * 100);
  const calculateVariability = (v: number[]) => {
    if (v.length < 2) return null;
    let sum = 0;
    for (let i = 1; i < v.length; i++) sum += Math.abs(v[i] - v[i - 1]);
    return sum / (v.length - 1);
  };
  const classifyDirection = (v: number[]) => {
    const change = calculateAbsoluteChange(v);
    if (change === null) return 'insufficient_data';
    if (change > 0) return 'increasing';
    if (change < 0) return 'decreasing';
    return 'stable';
  };
  const classifyMonotonicity = (v: number[]) => {
    if (v.length < 3) return 'insufficient_data';
    let pos = 0, neg = 0;
    for (let i = 1; i < v.length; i++) {
      const d = v[i] - v[i - 1];
      if (d > 0) pos++;
      if (d < 0) neg++;
    }
    const total = v.length - 1;
    if (pos === total) return 'monotonic_increase';
    if (neg === total) return 'monotonic_decrease';
    if (pos >= total - 1) return 'mostly_increasing';
    if (neg >= total - 1) return 'mostly_decreasing';
    return 'mixed';
  };

  const isPct = ['HbA1c', 'LDL', 'UACR', 'eGFR'].includes(concept);

  return {
    concept,
    n_observations: values.length,
    first_value: values.length > 0 ? values[0] : null,
    latest_value: values.length > 0 ? values[values.length - 1] : null,
    absolute_change: calculateAbsoluteChange(values),
    percent_change: isPct ? calculatePercentChange(values) : null,
    variability: calculateVariability(values),
    direction: classifyDirection(values),
    monotonicity: classifyMonotonicity(values),
    values
  };
}

export function evaluateRetinopathyRules(profile: any) {
  const trajectory = profile.retinal_trajectory;
  const evaluations: Record<string, any> = {};

  const make = (id: string, name: string, trigger: string, satisfied: boolean, reason: string) => {
    evaluations[id] = { rule_id: id, name, trigger, satisfied, reason };
  };

  const duration = profile.context.t1d_duration;
  const age = profile.context.age;
  const puberty = profile.context.puberty_status;
  const durationVal: number | null = typeof duration === 'number' ? duration : null;
  const durationOk = durationVal !== null && durationVal >= 3;
  const ageOrPubertyOk = (age !== null && age >= 11) || puberty === 'started';
  const initialNotCompleted = trajectory.n_observed === 0;

  make('R001', 'Screening Eligible', 'duration >= 3 and (age >= 11 or puberty)', durationOk && ageOrPubertyOk && initialNotCompleted, `Duration: ${durationVal}, age/puberty ok: ${ageOrPubertyOk}, no prior exam: ${initialNotCompleted}`);
  
  const due = trajectory.n_observed >= 1 && !trajectory.latest_visit_has_observation && (trajectory.visits_since_last_observation ?? 0) >= 1;
  make('R002', 'Screening Due', 'prior exam exists and gap >= 1', due, `Visits since last obs: ${trajectory.visits_since_last_observation}`);

  const r003 = trajectory.overall_transition_type === INCIDENT_PROGRESSION;
  make('R003', 'Incident Retinopathy', 'No_DR -> DR', r003, `Transition: ${trajectory.overall_transition_type}`);

  const r004 = [PROGRESSION, INCIDENT_PROGRESSION].includes(trajectory.overall_transition_type);
  make('R004', 'Retinopathy Progression', 'stage increases', r004, `Transition: ${trajectory.overall_transition_type}`);

  const r005 = trajectory.overall_transition_type === STABLE;
  make('R005', 'Stable Retinal State', 'stage unchanged', r005, `Transition: ${trajectory.overall_transition_type}`);

  // Systemic
  const hba1c = profile.numeric_features['HbA1c'];
  const glycOk = hba1c && hba1c.n_observations >= 2 && hba1c.direction === 'increasing';
  make('R006', 'Glycemic Risk Signal', 'HbA1c increasing', !!glycOk, glycOk ? `Increasing to ${hba1c.latest_value}` : 'Not increasing');

  const sbp = profile.numeric_features['Systolic_BP'];
  const dbp = profile.numeric_features['Diastolic_BP'];
  let bpOk = false, bpReason = '';
  if (age === null || age < PEDIATRIC_ADULT_BP_CATEGORY_AGE_YEARS) {
    bpReason = 'Age below pediatric cutover';
  } else if (!sbp || !dbp || sbp.n_observations === 0) {
    bpReason = 'No BP obs';
  } else {
    let elevCount = 0;
    for (let i = 0; i < sbp.values.length; i++) {
      if (sbp.values[i] >= ELEVATED_SBP_MMHG || dbp.values[i] >= ELEVATED_DBP_MMHG) elevCount++;
    }
    bpOk = elevCount >= 2;
    bpReason = `${elevCount} elevated readings`;
  }
  make('R007', 'BP Risk Signal', 'Repeated elevated BP', bpOk, bpReason);

  const ldl = profile.numeric_features['LDL'];
  const lipidOk = ldl && ldl.latest_value !== null && ldl.latest_value >= ADA_PEDIATRIC_T1D_LDL_GOAL_MG_DL;
  make('R008', 'Lipid Risk Signal', `LDL >= ${ADA_PEDIATRIC_T1D_LDL_GOAL_MG_DL}`, !!lipidOk, lipidOk ? `Latest LDL: ${ldl.latest_value}` : 'Normal or none');

  const uacr = profile.numeric_features['UACR'];
  let kidneyOk = false;
  if (uacr && uacr.values) {
    const elevCount = uacr.values.filter((v: number) => v >= ADA_ELEVATED_UACR_MG_PER_G).length;
    kidneyOk = elevCount >= 2;
  }
  make('R009', 'Kidney Context Signal', 'Persistent albuminuria', kidneyOk, `UACR elevated >=2 times`);

  const signalCount = [glycOk, bpOk, lipidOk, kidneyOk].filter(Boolean).length;
  const hasExistingDr = trajectory.latest_observed_stage_index !== null && trajectory.latest_observed_stage_index > 0;
  
  make('R010', 'Increasing Concern', 'existing DR & >=2 systemic', hasExistingDr && signalCount >= 2, `has_dr: ${hasExistingDr}, signals: ${signalCount}`);
  make('R011', 'High Concern', 'progression', r003 || r004, `progression detected`);
  make('R012', 'Watch', 'no progression & >=2 systemic', !(r003 || r004) && signalCount >= 2, `no progression, signals: ${signalCount}`);
  make('R013', 'Insufficient Data', 'no latest observation', !trajectory.latest_visit_has_observation, `latest_visit_has_observation: ${trajectory.latest_visit_has_observation}`);

  return evaluations;
}

export function aggregateRiskState(evaluations: Record<string, any>, nObserved: number) {
  if (evaluations['R013'].satisfied) return { state: 'INSUFFICIENT_DATA', reason: evaluations['R013'].reason };
  if (nObserved < 2) return { state: 'INSUFFICIENT_DATA', reason: 'Fewer than 2 retinal observations' };
  
  if (evaluations['R011'].satisfied) return { state: 'HIGH_CONCERN', reason: evaluations['R011'].reason };
  if (evaluations['R010'].satisfied) return { state: 'INCREASING_CONCERN', reason: evaluations['R010'].reason };
  if (evaluations['R012'].satisfied) return { state: 'WATCH', reason: evaluations['R012'].reason };
  
  return { state: 'STABLE', reason: 'Default V1 baseline' };
}
