from app.temporal.numeric_features import (
    analyze_numeric_series,
    calculate_absolute_change,
    calculate_percent_change,
    calculate_variability,
    classify_direction,
    classify_monotonicity,
)


def test_absolute_change_requires_two_points():
    assert calculate_absolute_change([7.0]) is None
    assert calculate_absolute_change([]) is None
    assert round(calculate_absolute_change([7.0, 8.4]), 4) == 1.4


def test_percent_change_none_with_insufficient_points_or_zero_baseline():
    assert calculate_percent_change([7.0]) is None
    assert calculate_percent_change([0, 5]) is None


def test_percent_change_value():
    assert round(calculate_percent_change([7.0, 8.4]), 4) == 20.0


def test_variability_mean_absolute_consecutive_difference():
    assert calculate_variability([7.0]) is None
    assert round(calculate_variability([7.0, 7.8, 8.4]), 4) == round((0.8 + 0.6) / 2, 4)


def test_direction_is_sign_based_with_no_magnitude_threshold():
    # Even a tiny nonzero change is reported as a direction -- no invented
    # "significant change" cutoff.
    assert classify_direction([7.00, 7.01]) == "increasing"
    assert classify_direction([7.01, 7.00]) == "decreasing"
    assert classify_direction([7.00, 7.00]) == "stable"
    assert classify_direction([7.00]) == "insufficient_data"


def test_monotonicity_requires_three_points():
    assert classify_monotonicity([1, 2]) == "insufficient_data"


def test_monotonicity_classification():
    assert classify_monotonicity([1, 2, 3]) == "monotonic_increase"
    assert classify_monotonicity([3, 2, 1]) == "monotonic_decrease"
    assert classify_monotonicity([1, 2, 1.5, 3]) == "mostly_increasing"
    assert classify_monotonicity([1, 3, 2, 4, 1]) == "mixed"


def test_percent_change_omitted_for_blood_pressure():
    features = analyze_numeric_series("Systolic_BP", ["2024-01-01", "2025-01-01"], [110, 128])
    assert features.absolute_change == 18
    assert features.percent_change is None


def test_percent_change_included_for_hba1c():
    features = analyze_numeric_series("HbA1c", ["2024-01-01", "2025-01-01"], [7.0, 8.4])
    assert round(features.percent_change, 2) == 20.0


def test_analyze_numeric_series_empty():
    features = analyze_numeric_series("HbA1c", [], [])
    assert features.n_observations == 0
    assert features.first_value is None
    assert features.latest_value is None
    assert features.direction == "insufficient_data"
