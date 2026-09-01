from statistics import mean


DIRECTIONALITY = {
    "UACR": "higher_is_worse",
    "HbA1c": "higher_is_worse",
    "CGM_Time_in_Range": "lower_is_worse",
    "Systolic_BP": "higher_is_worse",
    "Diastolic_BP": "higher_is_worse",
    "Serum_Creatinine": "higher_is_worse",
    "eGFR": "lower_is_worse"
}


SIGNIFICANT_CHANGE = {
    "UACR": 0.20,
    "HbA1c": 0.10,
    "CGM_Time_in_Range": 0.10,
    "Systolic_BP": 0.05,
    "Diastolic_BP": 0.05,
    "Serum_Creatinine": 0.05,
    "eGFR": 0.05
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

    numerator = sum(
        (x - x_mean) * (y - y_mean)
        for x, y in enumerate(values)
    )

    denominator = sum(
        (x - x_mean) ** 2
        for x in range(n)
    )

    if denominator == 0:
        return 0.0

    return numerator / denominator


def calculate_variability(values):
    if len(values) < 2:
        return 0.0

    changes = [
        abs(values[i] - values[i - 1])
        for i in range(1, len(values))
    ]

    return mean(changes)


def classify_direction(concept, values):
    if len(values) < 2:
        return "insufficient_data"

    relative_change = abs(calculate_percent_change(values)) / 100
    threshold = SIGNIFICANT_CHANGE.get(concept, 0.05)

    if relative_change < threshold:
        return "stable"

    change = calculate_change(values)

    if change > 0:
        return "increasing"

    if change < 0:
        return "decreasing"

    return "stable"


def classify_monotonicity(values):
    if len(values) < 3:
        return "insufficient_data"

    differences = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    positive = sum(d > 0 for d in differences)
    negative = sum(d < 0 for d in differences)

    if positive == len(differences):
        return "monotonic_increase"

    if negative == len(differences):
        return "monotonic_decrease"

    if positive >= len(differences) - 1:
        return "mostly_increasing"

    if negative >= len(differences) - 1:
        return "mostly_decreasing"

    return "mixed"


def detect_transient_spike(values, abnormal_threshold):
    if len(values) < 3:
        return False

    middle = values[1:-1]

    spike = any(
        value > abnormal_threshold
        for value in middle
    )

    normalized_after = all(
        value <= abnormal_threshold
        for value in values[2:]
    )

    return spike and normalized_after


def detect_persistence(values, abnormal_threshold):
    abnormal = [
        value > abnormal_threshold
        for value in values
    ]

    return {
        "abnormal_count": sum(abnormal),
        "total_count": len(values),
        "persistent": sum(abnormal) >= 2,
        "all_recent_abnormal": all(abnormal[-2:]) if len(values) >= 2 else False
    }


def analyze_variable(concept, values):
    direction = classify_direction(concept, values)
    monotonicity = classify_monotonicity(values)

    result = {
        "concept": concept,
        "values": values,
        "direction": direction,
        "monotonicity": monotonicity,
        "change": round(calculate_change(values), 4),
        "percent_change": round(calculate_percent_change(values), 2),
        "slope": round(calculate_slope(values), 4),
        "variability": round(calculate_variability(values), 4)
    }

    if concept == "UACR":
        persistence = detect_persistence(values, 30)

        result["uacr_persistence"] = persistence

        result["transient_spike"] = (
            detect_transient_spike(values, 30)
        )

    return result


def calculate_trends(timeline):
    if not timeline:
        return {}

    concepts = timeline[0].keys()
    concepts = [
        concept
        for concept in concepts
        if concept != "date"
    ]

    trends = {}

    for concept in concepts:
        values = [
            visit[concept]
            for visit in timeline
            if concept in visit and visit[concept] is not None
        ]

        if values:
            trends[concept] = analyze_variable(
                concept,
                values
            )

    return trends


def detect_cross_variable_patterns(trends):
    patterns = []

    uacr = trends.get("UACR")
    egfr = trends.get("eGFR")
    hba1c = trends.get("HbA1c")
    tir = trends.get("CGM_Time_in_Range")
    sbp = trends.get("Systolic_BP")
    dbp = trends.get("Diastolic_BP")

    if uacr and egfr:
        if (
            uacr["direction"] == "increasing"
            and egfr["direction"] == "decreasing"
        ):
            patterns.append(
                "UACR increasing concurrently with eGFR decreasing"
            )

    if hba1c and tir:
        if (
            hba1c["direction"] == "increasing"
            and tir["direction"] == "decreasing"
        ):
            patterns.append(
                "HbA1c increasing while CGM time in range decreases"
            )

    if hba1c and sbp:
        if (
            hba1c["direction"] == "increasing"
            and sbp["direction"] == "increasing"
        ):
            patterns.append(
                "Worsening glycemic control with increasing systolic BP"
            )

    if sbp and dbp:
        if (
            sbp["direction"] == "increasing"
            and dbp["direction"] == "increasing"
        ):
            patterns.append(
                "Systolic and diastolic BP increasing together"
            )

    return patterns


def classify_patient_pattern(trends, cross_patterns):
    uacr = trends.get("UACR")
    egfr = trends.get("eGFR")
    hba1c = trends.get("HbA1c")
    tir = trends.get("CGM_Time_in_Range")
    sbp = trends.get("Systolic_BP")

    if uacr:
        persistence = uacr.get("uacr_persistence", {})

        if uacr.get("transient_spike"):
            return "TRANSIENT_UACR_ABNORMALITY"

        if (
            persistence.get("all_recent_abnormal")
            and uacr["direction"] == "increasing"
            and egfr
            and egfr["direction"] == "decreasing"
        ):
            return "PROGRESSIVE_RENAL_TRAJECTORY"

    if (
        hba1c
        and tir
        and sbp
        and hba1c["direction"] == "increasing"
        and tir["direction"] == "decreasing"
        and sbp["direction"] == "increasing"
        and uacr
        and egfr
        and uacr["direction"] != "increasing"
    ):
        return "WORSENING_METABOLIC_BP_WITH_STABLE_KIDNEY_MARKERS"

    meaningful_changes = 0

    for concept, trend in trends.items():
        if trend["direction"] != "stable":
            meaningful_changes += 1

    if meaningful_changes == 0:
        return "STABLE_TRAJECTORY"

    if (
        uacr
        and egfr
        and uacr["direction"] == "increasing"
        and egfr["direction"] == "decreasing"
    ):
        return "EMERGING_RENAL_SIGNAL"

    return "NON_SPECIFIC_CHANGE"


def analyze_patient(timeline):
    trends = calculate_trends(timeline)

    cross_patterns = detect_cross_variable_patterns(
        trends
    )

    patient_pattern = classify_patient_pattern(
        trends,
        cross_patterns
    )

    return {
        "trends": trends,
        "cross_variable_patterns": cross_patterns,
        "patient_pattern": patient_pattern
    }