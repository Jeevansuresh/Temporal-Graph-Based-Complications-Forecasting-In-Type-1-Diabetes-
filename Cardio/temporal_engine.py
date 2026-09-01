from statistics import mean


DIRECTIONALITY = {
    "Systolic_BP": "higher_is_worse",
    "Diastolic_BP": "higher_is_worse",
    "HbA1c": "higher_is_worse",
    "Fasting_Glucose": "higher_is_worse",
    "Random_Glucose": "higher_is_worse",
    "LDL_Cholesterol": "higher_is_worse",
    "HDL_Cholesterol": "lower_is_worse",
    "Triglycerides": "higher_is_worse",
    "Total_Cholesterol": "higher_is_worse",
    "Serum_Creatinine": "higher_is_worse",
    "UACR": "higher_is_worse",
    "eGFR": "lower_is_worse",
    "BNP_NTproBNP": "higher_is_worse",
    "BMI": "higher_is_worse",
    "Heart_Rate": "higher_is_worse"
}

SIGNIFICANT_CHANGE = {
    "Systolic_BP": 0.05,
    "Diastolic_BP": 0.05,
    "HbA1c": 0.08,
    "Fasting_Glucose": 0.10,
    "Random_Glucose": 0.10,
    "LDL_Cholesterol": 0.10,
    "HDL_Cholesterol": 0.10,
    "Triglycerides": 0.15,
    "Total_Cholesterol": 0.10,
    "Serum_Creatinine": 0.05,
    "UACR": 0.20,
    "eGFR": 0.05,
    "BNP_NTproBNP": 0.20,
    "BMI": 0.05,
    "Heart_Rate": 0.10
}


def calculate_change(values):
    if len(values) < 2:
        return 0.0
    return values[-1] - values[0]


def calculate_percent_change(values):
    if len(values) < 2 or values[0] == 0:
        return 0.0
    return ((values[-1] - values[0]) / abs(values[0])) * 100


def calculate_slope(values):
    if len(values) < 2:
        return 0.0
    n = len(values)
    x_mean = mean(range(n))
    y_mean = mean(values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in enumerate(values))
    denominator = sum((x - x_mean) ** 2 for x in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_variability(values):
    if len(values) < 2:
        return 0.0
    changes = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    return mean(changes)


def classify_direction(concept, values):
    if len(values) < 2:
        return "INSUFFICIENT_DATA"
    relative_change = abs(calculate_percent_change(values)) / 100
    threshold = SIGNIFICANT_CHANGE.get(concept, 0.05)
    if relative_change < threshold:
        return "STABLE"
    change = calculate_change(values)
    if change > 0:
        return "INCREASING"
    if change < 0:
        return "DECREASING"
    return "STABLE"


def classify_monotonicity(values):
    if len(values) < 3:
        return "INSUFFICIENT_DATA"
    differences = [values[i] - values[i - 1] for i in range(1, len(values))]
    positive = sum(d > 0 for d in differences)
    negative = sum(d < 0 for d in differences)
    if positive == len(differences):
        return "MONOTONIC_INCREASE"
    if negative == len(differences):
        return "MONOTONIC_DECREASE"
    if positive >= len(differences) - 1:
        return "MOSTLY_INCREASING"
    if negative >= len(differences) - 1:
        return "MOSTLY_DECREASING"
    return "MIXED"


def detect_persistence(values, abnormal_threshold, greater_than=True):
    if greater_than:
        abnormal = [value >= abnormal_threshold for value in values]
    else:
        abnormal = [value <= abnormal_threshold for value in values]
    return {
        "abnormal_count": sum(abnormal),
        "total_count": len(values),
        "persistent": sum(abnormal) >= 2,
        "all_recent_abnormal": all(abnormal[-2:]) if len(values) >= 2 else False,
        "latest_abnormal": abnormal[-1] if values else False
    }


def analyze_variable(concept, values):
    direction = classify_direction(concept, values)
    monotonicity = classify_monotonicity(values)
    abs_change = calculate_change(values)
    pct_change = calculate_percent_change(values)
    slope = calculate_slope(values)
    variability = calculate_variability(values)

    result = {
        "concept": concept,
        "values": values,
        "first": values[0],
        "latest": values[-1],
        "direction": direction,
        "directionality": DIRECTIONALITY.get(concept, "higher_is_worse"),
        "monotonicity": monotonicity,
        "absolute_change": round(abs_change, 4),
        "percentage_change": round(pct_change, 2),
        "slope": round(slope, 4),
        "variability": round(variability, 4)
    }

    if concept == "UACR":
        result["persistence"] = detect_persistence(values, 30.0, greater_than=True)
    elif concept == "Systolic_BP":
        result["persistence"] = detect_persistence(values, 130.0, greater_than=True)
    elif concept == "Diastolic_BP":
        result["persistence"] = detect_persistence(values, 80.0, greater_than=True)
    elif concept == "BNP_NTproBNP":
        result["persistence"] = detect_persistence(values, 100.0, greater_than=True)
    elif concept == "eGFR":
        result["persistence"] = detect_persistence(values, 60.0, greater_than=False)
    elif concept == "LDL_Cholesterol":
        result["persistence"] = detect_persistence(values, 100.0, greater_than=True)

    return result


def calculate_trends(timeline):
    if not timeline:
        return {}
    
    # Handle dict of visits keyed by date or list of dicts
    if isinstance(timeline, dict):
        visits = [timeline[d] for d in sorted(timeline.keys())]
    else:
        visits = timeline

    if not visits:
        return {}

    concepts = set()
    for v in visits:
        for k in v.keys():
            if k not in ["date", "visit_id", "visit_date", "visit_time", "time", "age", "age_years", "sex", "t1d_duration", "t1d_duration_years", "smoking_status", "hypertension_status", "dyslipidemia", "known_ascvd", "known_cad", "ecg_abnormality", "cardiovascular_symptoms", "clinical_action"]:
                concepts.add(k)

    trends = {}
    for concept in sorted(concepts):
        vals = []
        for v in visits:
            val = v.get(concept)
            if isinstance(val, dict):
                val = val.get("value")
            if val is not None:
                try:
                    vals.append(float(val))
                except (ValueError, TypeError):
                    pass
        if vals:
            trends[concept] = analyze_variable(concept, vals)

    return trends


def determine_worsening_variables(trends):
    worsening = []
    for concept, data in trends.items():
        direction = data["direction"]
        directionality = data.get("directionality", DIRECTIONALITY.get(concept, "higher_is_worse"))
        
        if directionality == "lower_is_worse":
            is_worse = direction in ["DECREASING", "MOSTLY_DECREASING"]
        else:
            is_worse = direction in ["INCREASING", "MOSTLY_INCREASING"]

        if is_worse:
            worsening.append(concept)
    return worsening


def detect_cross_variable_patterns(trends):
    patterns = []
    sbp = trends.get("Systolic_BP")
    dbp = trends.get("Diastolic_BP")
    hba1c = trends.get("HbA1c")
    ldl = trends.get("LDL_Cholesterol")
    hdl = trends.get("HDL_Cholesterol")
    tg = trends.get("Triglycerides")
    uacr = trends.get("UACR")
    egfr = trends.get("eGFR")
    bnp = trends.get("BNP_NTproBNP")

    # BP dual elevation
    if sbp and dbp:
        if sbp["direction"] in ["INCREASING", "MOSTLY_INCREASING"] and dbp["direction"] in ["INCREASING", "MOSTLY_INCREASING"]:
            patterns.append("Concomitant systolic and diastolic blood pressure elevation across visits")

    # Dyslipidemia progression
    if ldl and hdl:
        if ldl["direction"] in ["INCREASING", "MOSTLY_INCREASING"] and hdl["direction"] in ["DECREASING", "MOSTLY_DECREASING"]:
            patterns.append("Atherogenic dyslipidemia progression (rising LDL-C concurrent with falling HDL-C)")
    elif ldl and tg:
        if ldl["direction"] in ["INCREASING", "MOSTLY_INCREASING"] and tg["direction"] in ["INCREASING", "MOSTLY_INCREASING"]:
            patterns.append("Progressive lipid profile elevation (rising LDL-C and triglycerides)")

    # Glycemic-Cardiovascular worsening
    if hba1c and sbp:
        if hba1c["direction"] in ["INCREASING", "MOSTLY_INCREASING"] and sbp["direction"] in ["INCREASING", "MOSTLY_INCREASING"]:
            patterns.append("Glycemic deterioration accompanied by progressive systolic hypertension")

    # Cardiorenal intersection
    if uacr and egfr:
        if uacr["direction"] in ["INCREASING", "MOSTLY_INCREASING"] and egfr["direction"] in ["DECREASING", "MOSTLY_DECREASING"]:
            patterns.append("Cardiorenal microvascular progression (rising UACR with declining eGFR)")

    # Heart failure signal progression
    if bnp and (sbp or uacr):
        if bnp["direction"] in ["INCREASING", "MOSTLY_INCREASING"] and bnp["latest"] > 100:
            patterns.append("Rising natriuretic peptide (BNP/NT-proBNP) signaling accelerating heart failure risk")

    return patterns


def classify_patient_pattern(trends, cross_patterns, baseline_context=None):
    if baseline_context:
        ctx_lower = baseline_context.lower()
        has_negation = "no " in ctx_lower or "without" in ctx_lower or "none" in ctx_lower
        is_secondary = any(term in ctx_lower for term in ["established ascvd", "cad history", "secondary", "prior mi", "documented cad", "known ascvd/cad"])
        if is_secondary and not has_negation:
            return "ESTABLISHED_ASCVD_SECONDARY_PREVENTION_TRAJECTORY"

    bnp = trends.get("BNP_NTproBNP")
    sbp = trends.get("Systolic_BP")
    ldl = trends.get("LDL_Cholesterol")
    uacr = trends.get("UACR")

    if bnp and bnp["latest"] >= 100 and sbp and sbp["direction"] in ["INCREASING", "MOSTLY_INCREASING"]:
        return "ACCELERATING_CARDIOMETABOLIC_RISK_WITH_EMERGING_HF_CAD_SIGNALS"

    if (sbp and sbp["latest"] >= 130) or (uacr and uacr["latest"] >= 30) or (ldl and ldl["latest"] >= 160):
        return "PROGRESSIVE_HYPERTENSION_ALBUMINURIA_DYSLIPIDEMIA"

    worsening = determine_worsening_variables(trends)
    if not worsening or len(worsening) <= 1:
        return "STABLE_LOW_MODERATE_CARDIO_TRAJECTORY"

    return "MULTIFACTORIAL_CARDIOVASCULAR_RISK_PROGRESSION"


def analyze_patient(timeline, baseline_context=None):
    trends = calculate_trends(timeline)
    cross_patterns = detect_cross_variable_patterns(trends)
    patient_pattern = classify_patient_pattern(trends, cross_patterns, baseline_context)
    worsening_variables = determine_worsening_variables(trends)

    return {
        "trends": trends,
        "cross_variable_patterns": cross_patterns,
        "patient_pattern": patient_pattern,
        "worsening_variables": worsening_variables
    }
