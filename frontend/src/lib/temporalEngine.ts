const SIGNIFICANT_CHANGE: Record<string, number> = {
  UACR: 0.20,
  HbA1c: 0.10,
  CGM_Time_in_Range: 0.10,
  Systolic_BP: 0.05,
  Diastolic_BP: 0.05,
  Serum_Creatinine: 0.05,
  eGFR: 0.05,
};

function calculateChange(values: number[]) {
  if (values.length < 2) return 0.0;
  return values[values.length - 1] - values[0];
}

function calculatePercentChange(values: number[]) {
  if (values.length < 2 || values[0] === 0) return 0.0;
  return ((values[values.length - 1] - values[0]) / Math.abs(values[0])) * 100;
}

function calculateSlope(values: number[]) {
  if (values.length < 2) return 0.0;
  
  const n = values.length;
  let sumX = 0, sumY = 0;
  for (let i = 0; i < n; i++) {
    sumX += i;
    sumY += values[i];
  }
  const xMean = sumX / n;
  const yMean = sumY / n;
  
  let numerator = 0;
  let denominator = 0;
  for (let i = 0; i < n; i++) {
    numerator += (i - xMean) * (values[i] - yMean);
    denominator += Math.pow(i - xMean, 2);
  }
  
  return denominator === 0 ? 0.0 : numerator / denominator;
}

function calculateVariability(values: number[]) {
  if (values.length < 2) return 0.0;
  let sum = 0;
  for (let i = 1; i < values.length; i++) {
    sum += Math.abs(values[i] - values[i - 1]);
  }
  return sum / (values.length - 1);
}

function classifyDirection(concept: string, values: number[]) {
  if (values.length < 2) return 'insufficient_data';
  
  const relativeChange = Math.abs(calculatePercentChange(values)) / 100;
  const threshold = SIGNIFICANT_CHANGE[concept] ?? 0.05;
  
  if (relativeChange < threshold) return 'stable';
  
  const change = calculateChange(values);
  if (change > 0) return 'increasing';
  if (change < 0) return 'decreasing';
  
  return 'stable';
}

function classifyMonotonicity(values: number[]) {
  if (values.length < 3) return 'insufficient_data';
  
  let positive = 0;
  let negative = 0;
  
  for (let i = 1; i < values.length; i++) {
    const d = values[i] - values[i - 1];
    if (d > 0) positive++;
    if (d < 0) negative++;
  }
  
  const diffCount = values.length - 1;
  
  if (positive === diffCount) return 'monotonic_increase';
  if (negative === diffCount) return 'monotonic_decrease';
  if (positive >= diffCount - 1) return 'mostly_increasing';
  if (negative >= diffCount - 1) return 'mostly_decreasing';
  
  return 'mixed';
}

export function analyzePatientTrends(timeline: Record<string, Record<string, number>>) {
  const dates = Object.keys(timeline).sort();
  if (dates.length === 0) return { trends: {}, patterns: [], overall: 'NO_DATA' };
  
  // Extract all concepts
  const conceptsSet = new Set<string>();
  for (const date of dates) {
    for (const concept of Object.keys(timeline[date])) {
      conceptsSet.add(concept);
    }
  }
  
  const concepts = Array.from(conceptsSet);
  const trends: Record<string, any> = {};
  
  for (const concept of concepts) {
    const values = dates.map(date => timeline[date][concept]).filter(v => v !== undefined);
    
    if (values.length > 0) {
      trends[concept] = {
        concept,
        values,
        first: values[0],
        latest: values[values.length - 1],
        absolute_change: calculateChange(values),
        percent_change: calculatePercentChange(values),
        direction: classifyDirection(concept, values),
        monotonicity: classifyMonotonicity(values),
        slope: calculateSlope(values),
        variability: calculateVariability(values),
      };
      
      if (concept === 'UACR') {
        const abnormal = values.map(v => v > 30);
        const abnormalCount = abnormal.filter(Boolean).length;
        trends[concept].uacr_persistence = {
          abnormal_count: abnormalCount,
          total_count: values.length,
          persistent: abnormalCount >= 2,
          all_recent_abnormal: values.length >= 2 ? abnormal[abnormal.length - 1] && abnormal[abnormal.length - 2] : false,
        };
      }
    }
  }
  
  const patterns: string[] = [];
  const uacr = trends['UACR'];
  const egfr = trends['eGFR'];
  const hba1c = trends['HbA1c'];
  const tir = trends['CGM_Time_in_Range'];
  const sbp = trends['Systolic_BP'];
  const dbp = trends['Diastolic_BP'];

  if (uacr && egfr && uacr.direction === 'increasing' && egfr.direction === 'decreasing') {
    patterns.push('UACR increasing concurrently with eGFR decreasing');
  }
  
  if (hba1c && tir && hba1c.direction === 'increasing' && tir.direction === 'decreasing') {
    patterns.push('HbA1c increasing while CGM time in range decreases');
  }
  
  if (hba1c && sbp && hba1c.direction === 'increasing' && sbp.direction === 'increasing') {
    patterns.push('Worsening glycemic control with increasing systolic BP');
  }
  
  if (sbp && dbp && sbp.direction === 'increasing' && dbp.direction === 'increasing') {
    patterns.push('Systolic and diastolic BP increasing together');
  }

  let patient_pattern = 'NON_SPECIFIC_CHANGE';
  
  if (uacr && uacr.uacr_persistence?.all_recent_abnormal && uacr.direction === 'increasing' && egfr?.direction === 'decreasing') {
    patient_pattern = 'PROGRESSIVE_RENAL_TRAJECTORY';
  } else if (hba1c && tir && sbp && hba1c.direction === 'increasing' && tir.direction === 'decreasing' && sbp.direction === 'increasing' && uacr && egfr && uacr.direction !== 'increasing') {
    patient_pattern = 'WORSENING_METABOLIC_BP_WITH_STABLE_KIDNEY_MARKERS';
  } else {
    let meaningful = 0;
    for (const key of Object.keys(trends)) {
      if (trends[key].direction !== 'stable' && trends[key].direction !== 'insufficient_data') meaningful++;
    }
    
    if (meaningful === 0) {
      patient_pattern = 'STABLE_TRAJECTORY';
    } else if (uacr?.direction === 'increasing' && egfr?.direction === 'decreasing') {
      patient_pattern = 'EMERGING_RENAL_SIGNAL';
    }
  }

  return { trends, patterns, patient_pattern };
}
