"""Retinopathy TKG demo -- Streamlit entrypoint.

Run from Retinopathy/:
    streamlit run app/ui/streamlit_app.py

This file only renders. All clinical logic lives in app/reasoning/ and
app/temporal/ (via app/ui/view_model.py, which reshapes their output for
display and computes nothing itself). See README.md for setup.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

import streamlit as st

from app.graph.csv_validation import ROOT_DIR
from app.ui.charts import build_numeric_trend_figure, build_retinal_trajectory_figure
from app.ui.view_model import PatientView, build_patient_view

PATIENT_IDS = ["P001", "P002", "P003", "P004", "P005"]

RISK_STATE_STYLE = {
    "STABLE": ("#e6f4ea", "#1e7e34"),
    "WATCH": ("#fff8e1", "#8a6d00"),
    "INCREASING_CONCERN": ("#ffe8d6", "#b35c00"),
    "HIGH_CONCERN": ("#fdecea", "#c62828"),
    "INSUFFICIENT_DATA": ("#eceff1", "#455a64"),
}

NUMERIC_CHART_ORDER = ["HbA1c", "Systolic_BP", "Diastolic_BP", "LDL", "UACR", "eGFR"]


@st.cache_data(show_spinner=False)
def _load_case_descriptions() -> dict:
    data = json.loads((ROOT_DIR / "synthetic_cases.json").read_text(encoding="utf-8"))
    return {case["id"]: case.get("description", "") for case in data["cases"]}


def _render_disclaimer() -> None:
    st.warning(
        "**Research / demo clinical decision support prototype.** "
        "This is NOT a diagnostic tool and does not recommend treatment. "
        "It reports deterministic, rule-based, evidence-cited observations "
        "from synthetic data only -- no machine learning, no calibrated "
        "probabilities, no prediction of future outcomes, and no "
        "autonomous clinical decisions. A qualitative risk state "
        "(STABLE / WATCH / INCREASING_CONCERN / HIGH_CONCERN / "
        "INSUFFICIENT_DATA) is not a diagnosis and does not estimate "
        "likelihood.",
        icon="⚠️",
    )


def _render_risk_badge(view: PatientView) -> None:
    bg, fg = RISK_STATE_STYLE.get(view.risk_state, ("#eee", "#333"))
    st.markdown(
        f"""
        <div style="background:{bg};color:{fg};border:1px solid {fg}33;
                    border-radius:10px;padding:16px 20px;margin:8px 0 16px 0;">
          <div style="font-size:0.85rem;letter-spacing:.05em;
                      text-transform:uppercase;opacity:.75;">Risk state</div>
          <div style="font-size:1.9rem;font-weight:700;">{view.risk_state}</div>
          <div style="font-size:0.95rem;margin-top:4px;">{view.precedence_reason}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_patient_summary(view: PatientView, description: str) -> None:
    st.subheader(f"Patient {view.patient_id}")
    if description:
        st.caption(description)
    ctx = view.context
    cols = st.columns(5)
    cols[0].metric("Age", ctx.get("age"))
    cols[1].metric("Sex", ctx.get("sex"))
    cols[2].metric("Height (cm)", ctx.get("height_cm"))
    cols[3].metric("Puberty status", ctx.get("puberty_status"))
    cols[4].metric("T1D diagnosis", ctx.get("t1d_diagnosis"))


def _render_latest_retinal_state(view: PatientView) -> None:
    latest = view.latest_retinal_state
    st.markdown("#### Current / latest retinal state")
    if latest.get("stage_label") is None:
        st.error("No retinal exam has ever been recorded for this patient.")
        return

    if latest.get("is_current_visit"):
        st.success(
            f"**{latest['stage_label']}** (stage {latest['stage_index']}) -- "
            f"observed at the most recent visit ({latest['date']})."
        )
    else:
        st.warning(
            f"Most recent visit has **no retinal exam recorded**. "
            f"Last **known** stage: **{latest['stage_label']}** "
            f"(stage {latest['stage_index']}) as of {latest['date']} -- "
            f"this is historical, not current."
        )


def _render_retinal_chart(view: PatientView) -> None:
    st.markdown("#### Retinal stage trajectory")
    st.plotly_chart(
        build_retinal_trajectory_figure(view.retinal_chart_data),
        width="stretch",
    )
    summary = view.retinal_trajectory_summary
    st.caption(
        f"Visits: {summary['n_visits_total']} total, {summary['n_observed']} with a "
        f"retinal exam. Most recent observed transition: **{summary['overall_transition_type']}**."
    )
    if summary["transitions"]:
        st.dataframe(
            [
                {
                    "From": f"{t['from_date']} ({t['from_stage_index']})",
                    "To": f"{t['to_date']} ({t['to_stage_index']})",
                    "Transition": t["transition_type"],
                }
                for t in summary["transitions"]
            ],
            hide_index=True,
            width="stretch",
        )


def _render_supporting_signal_charts(view: PatientView) -> None:
    st.markdown("#### Supporting systemic signals over time")
    st.caption(
        "These are risk-factor ASSOCIATIONS with retinopathy risk, not direct "
        "retinal observations and not diagnoses on their own."
    )
    available = [c for c in NUMERIC_CHART_ORDER if c in view.numeric_chart_data]
    if not available:
        st.info("No supporting systemic measurements available for this patient.")
        return

    cols = st.columns(2)
    for i, concept in enumerate(available):
        with cols[i % 2]:
            st.plotly_chart(
                build_numeric_trend_figure(view.numeric_chart_data[concept]),
                width="stretch",
            )


def _render_supporting_signals_table(view: PatientView) -> None:
    st.markdown("#### Supporting-signal rule evaluation (R006-R009)")
    st.dataframe(
        [
            {
                "Rule": s["rule_id"],
                "Signal": s["output_concept"],
                "Triggered": "Yes" if s["satisfied"] else "No",
                "Reason": s["reason"],
            }
            for s in view.supporting_signals
        ],
        hide_index=True,
        width="stretch",
    )


def _render_triggered_rules_and_evidence(view: PatientView) -> None:
    st.markdown("#### Triggered rules and evidence")
    if not view.triggered_rules:
        st.info("No rules triggered.")
    for rule in view.triggered_rules:
        with st.expander(f"{rule['rule_id']} -- {rule['output_concept']}", expanded=True):
            st.write(f"**Trigger:** {rule['trigger']}")
            st.write(f"**Reason:** {rule['reason']}")
            for eid in rule["evidence_ids"]:
                citation = view.evidence_citations.get(eid)
                if citation:
                    st.markdown(
                        f"- **{eid}** ({citation.get('evidence_strength') or 'strength n/a'}): "
                        f"{citation.get('citation')} -- \"{citation.get('claim')}\" "
                        f"[population: {citation.get('population')}]"
                        + (f" [{citation['url']}]" if citation.get("url") else "")
                    )
                else:
                    st.markdown(f"- **{eid}**: citation not found")


def _render_reference_standards(view: PatientView) -> None:
    with st.expander("Operational reference standards used for rule thresholds"):
        st.caption(
            "These are external clinical reference values used ONLY to "
            "operationalize qualitative rule clauses (e.g. 'elevated BP "
            "status'). They are kept separate from the Clinical Knowledge "
            "Graph's own evidence base (evidence.csv / evidence_audit.csv)."
        )
        st.dataframe(
            [
                {
                    "ID": r["standard_id"],
                    "Source": r["source_name"],
                    "Version": r["publication_version"],
                    "Threshold": r["exact_threshold"],
                    "Population": r["population_context"],
                    "Unit": r["unit"],
                    "Operationalizes": r["operationalizes_rule_clause"],
                }
                for r in view.reference_standards
            ],
            hide_index=True,
            width="stretch",
        )


def _render_uncertainty_and_notes(view: PatientView) -> None:
    st.markdown("#### Missing data / uncertainty")
    if view.missing_data_notes:
        for note in view.missing_data_notes:
            st.warning(note)
    else:
        st.success("No missing-data uncertainty flagged for this patient.")

    st.info(view.association_vs_observation_note)

    with st.expander("What is intentionally NOT evaluated (V1 scope limits)"):
        for note in view.operational_notes:
            st.markdown(f"- {note}")


def main() -> None:
    st.set_page_config(page_title="Retinopathy TKG Demo", layout="wide")
    st.title("Pediatric T1D Retinopathy -- Temporal Knowledge Graph Demo")
    _render_disclaimer()

    descriptions = _load_case_descriptions()
    patient_id = st.selectbox(
        "Select patient",
        PATIENT_IDS,
        format_func=lambda pid: f"{pid} -- {descriptions.get(pid, '')}",
    )

    with st.spinner("Loading patient data and running the deterministic rule engine..."):
        view = build_patient_view(patient_id)

    _render_patient_summary(view, descriptions.get(patient_id, ""))
    _render_risk_badge(view)

    left, right = st.columns([1, 1])
    with left:
        _render_latest_retinal_state(view)
        _render_retinal_chart(view)
    with right:
        _render_supporting_signal_charts(view)

    st.divider()
    st.header("Explanation")
    _render_supporting_signals_table(view)
    _render_triggered_rules_and_evidence(view)
    _render_reference_standards(view)
    _render_uncertainty_and_notes(view)


if __name__ == "__main__":
    main()
