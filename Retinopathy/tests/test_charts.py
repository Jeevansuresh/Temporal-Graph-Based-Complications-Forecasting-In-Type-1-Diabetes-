"""Pure unit tests for Plotly figure builders -- checks figure structure,
not rendering (no browser needed).
"""

from app.ui.charts import build_numeric_trend_figure, build_retinal_trajectory_figure
from app.ui.view_model import NumericChartData, RetinalTrajectoryChartData


def test_retinal_figure_has_categorical_ordinal_axis_not_continuous():
    chart_data = RetinalTrajectoryChartData(
        dates=["2024-01-01", "2025-01-01", "2026-01-01"],
        stage_indices=[0, 0, 1],
        stage_labels=["No_DR", "No_DR", "Mild_NPDR"],
        is_missing=[False, False, False],
    )
    fig = build_retinal_trajectory_figure(chart_data)

    yaxis = fig.layout.yaxis
    assert yaxis.tickmode == "array"
    assert list(yaxis.ticktext) == ["No_DR", "Mild_NPDR", "Moderate_NPDR", "Severe_NPDR", "PDR"]
    # x-axis must be categorical (dates), not a numeric/continuous axis.
    assert fig.layout.xaxis.type == "category"


def test_retinal_figure_does_not_connect_gaps_across_missing_visits():
    chart_data = RetinalTrajectoryChartData(
        dates=["2024-01-01", "2025-01-01", "2026-01-01"],
        stage_indices=[0, None, None],
        stage_labels=["No_DR", None, None],
        is_missing=[False, True, True],
    )
    fig = build_retinal_trajectory_figure(chart_data)

    observed_trace = fig.data[0]
    assert observed_trace.connectgaps is False
    assert list(observed_trace.y) == [0, None, None]


def test_retinal_figure_adds_distinct_missing_marker_trace():
    chart_data = RetinalTrajectoryChartData(
        dates=["2024-01-01", "2025-01-01", "2026-01-01"],
        stage_indices=[0, None, None],
        stage_labels=["No_DR", None, None],
        is_missing=[False, True, True],
    )
    fig = build_retinal_trajectory_figure(chart_data)

    assert len(fig.data) == 2  # observed line + missing marker trace
    missing_trace = fig.data[1]
    assert list(missing_trace.x) == ["2025-01-01", "2026-01-01"]
    assert missing_trace.marker.symbol == "x"
    assert "No retinal exam" in missing_trace.hovertemplate


def test_retinal_figure_no_missing_trace_when_fully_observed():
    chart_data = RetinalTrajectoryChartData(
        dates=["2024-01-01", "2025-01-01"],
        stage_indices=[0, 0],
        stage_labels=["No_DR", "No_DR"],
        is_missing=[False, False],
    )
    fig = build_retinal_trajectory_figure(chart_data)
    assert len(fig.data) == 1


def test_numeric_trend_figure_preserves_dates_and_values():
    chart_data = NumericChartData(
        concept="HbA1c",
        unit="%",
        dates=["2024-01-01", "2025-01-01", "2026-01-01"],
        values=[7.0, 7.8, 8.4],
    )
    fig = build_numeric_trend_figure(chart_data)
    assert list(fig.data[0].x) == chart_data.dates
    assert list(fig.data[0].y) == chart_data.values
    assert "%" in fig.layout.yaxis.title.text
