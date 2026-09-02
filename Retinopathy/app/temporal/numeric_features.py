"""Deterministic temporal trend features for continuous measurements
(HbA1c, Systolic_BP, Diastolic_BP, LDL, UACR, eGFR, T1D_Duration).

Pure arithmetic only: absolute change, percent change, variability, and
sign-based direction/monotonicity. No magnitude threshold is applied to
call a change "significant" -- rules.csv documents no numeric cutoffs for
these trajectories (R006-R009 are qualitative: "slope > 0", "worsening
trajectory", "repeated elevated status"), so introducing one here would be
inventing a clinical threshold that isn't in the evidence base. Direction
is therefore sign-of-change only.

Clinical interpretation of a trend (e.g. "this counts as a worsening
glycemic trajectory risk signal") is the rule engine's job, not this
module's -- see rules.csv R006-R009, implemented in a later step.
"""

from dataclasses import dataclass
from statistics import mean

# Percent change is a standard way relative change is discussed for these
# measurements (e.g. eGFR decline and UACR trends are conventionally
# described in relative terms). Blood pressure is conventionally discussed
# in absolute mmHg, not percent, so percent change is omitted for it.
PERCENT_CHANGE_CONCEPTS = {"HbA1c", "LDL", "UACR", "eGFR"}


@dataclass(frozen=True)
class NumericSeriesFeatures:
    concept: str
    dates: list
    values: list
    n_observations: int
    first_value: float | None
    latest_value: float | None
    absolute_change: float | None
    percent_change: float | None
    variability: float | None
    direction: str
    monotonicity: str


def calculate_absolute_change(values: list) -> float | None:
    if len(values) < 2:
        return None
    return values[-1] - values[0]


def calculate_percent_change(values: list) -> float | None:
    if len(values) < 2 or values[0] == 0:
        return None
    return ((values[-1] - values[0]) / abs(values[0])) * 100


def calculate_variability(values: list) -> float | None:
    if len(values) < 2:
        return None
    diffs = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    return mean(diffs)


def classify_direction(values: list) -> str:
    change = calculate_absolute_change(values)
    if change is None:
        return "insufficient_data"
    if change > 0:
        return "increasing"
    if change < 0:
        return "decreasing"
    return "stable"


def classify_monotonicity(values: list) -> str:
    if len(values) < 3:
        return "insufficient_data"

    diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
    positive = sum(d > 0 for d in diffs)
    negative = sum(d < 0 for d in diffs)

    if positive == len(diffs):
        return "monotonic_increase"
    if negative == len(diffs):
        return "monotonic_decrease"
    if positive >= len(diffs) - 1:
        return "mostly_increasing"
    if negative >= len(diffs) - 1:
        return "mostly_decreasing"
    return "mixed"


def analyze_numeric_series(concept: str, dates: list, values: list) -> NumericSeriesFeatures:
    percent_change = (
        calculate_percent_change(values) if concept in PERCENT_CHANGE_CONCEPTS else None
    )
    return NumericSeriesFeatures(
        concept=concept,
        dates=list(dates),
        values=list(values),
        n_observations=len(values),
        first_value=values[0] if values else None,
        latest_value=values[-1] if values else None,
        absolute_change=calculate_absolute_change(values),
        percent_change=percent_change,
        variability=calculate_variability(values),
        direction=classify_direction(values),
        monotonicity=classify_monotonicity(values),
    )
