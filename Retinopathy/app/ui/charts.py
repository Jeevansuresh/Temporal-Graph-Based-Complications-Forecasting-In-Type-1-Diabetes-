"""Plotly figure builders for the Streamlit demo.

Pure functions: PatientView chart data in, a plotly.graph_objects.Figure
out. No clinical logic, no Streamlit imports (so figures can be built and
inspected in tests without a running app).
"""

import plotly.graph_objects as go

from app.ui.view_model import NumericChartData, RETINAL_STAGE_ORDER, RetinalTrajectoryChartData

MISSING_MARKER_Y = -0.6  # just below the No_DR row -- a visually distinct "uncertain" zone


def build_retinal_trajectory_figure(chart_data: RetinalTrajectoryChartData) -> go.Figure:
    """Retinal stage plotted on a fixed CATEGORICAL axis (never numeric/
    continuous). Missing visits are shown as a separate marker in a
    visually distinct row below the axis, with hover text making clear no
    exam was recorded -- never plotted as, or connected through as, No_DR.
    """
    fig = go.Figure()

    # Observed stage line: y is None at missing dates, so Plotly leaves a
    # visible gap rather than interpolating a value across it.
    fig.add_trace(
        go.Scatter(
            x=chart_data.dates,
            y=chart_data.stage_indices,
            mode="lines+markers",
            name="Observed retinal stage",
            connectgaps=False,
            marker=dict(size=11, color="#1f77b4"),
            line=dict(width=2, color="#1f77b4"),
            hovertext=[label or "" for label in chart_data.stage_labels],
            hovertemplate="%{x}<br>%{hovertext}<extra></extra>",
        )
    )

    missing_dates = [d for d, m in zip(chart_data.dates, chart_data.is_missing) if m]
    if missing_dates:
        fig.add_trace(
            go.Scatter(
                x=missing_dates,
                y=[MISSING_MARKER_Y] * len(missing_dates),
                mode="markers",
                name="No retinal exam recorded",
                marker=dict(size=12, color="#999999", symbol="x"),
                hovertemplate="%{x}<br>No retinal exam recorded -- uncertain, not No_DR<extra></extra>",
            )
        )

    fig.update_yaxes(
        tickmode="array",
        tickvals=list(range(len(RETINAL_STAGE_ORDER))),
        ticktext=RETINAL_STAGE_ORDER,
        range=[MISSING_MARKER_Y - 0.5, len(RETINAL_STAGE_ORDER) - 0.5],
        title="Retinal stage (ordinal)",
    )
    fig.update_xaxes(title="Visit date", type="category")
    fig.update_layout(
        title="Retinal stage trajectory",
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60),
    )
    return fig


def build_numeric_trend_figure(chart_data: NumericChartData) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=chart_data.dates,
            y=chart_data.values,
            mode="lines+markers",
            name=chart_data.concept,
            marker=dict(size=9),
            line=dict(width=2),
        )
    )
    y_title = f"{chart_data.concept} ({chart_data.unit})" if chart_data.unit else chart_data.concept
    fig.update_yaxes(title=y_title)
    fig.update_xaxes(title="Visit date", type="category")
    fig.update_layout(title=chart_data.concept.replace("_", " "), height=280, margin=dict(t=50))
    return fig
