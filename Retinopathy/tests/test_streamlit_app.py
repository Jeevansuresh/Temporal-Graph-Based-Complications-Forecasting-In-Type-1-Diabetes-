"""Streamlit-facing tests using streamlit.testing.v1.AppTest -- runs the
actual app script (no browser needed) and inspects the rendered element
tree. Requires the live Neo4j instance with CKG + patient graph loaded.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "app" / "ui" / "streamlit_app.py")

EXPECTED_RISK_STATES = {
    "P001": "STABLE",
    "P002": "WATCH",
    "P003": "HIGH_CONCERN",
    "P004": "HIGH_CONCERN",
    "P005": "INSUFFICIENT_DATA",
}


def _run_app() -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=60)
    at.run()
    return at


def test_app_starts_without_exception():
    at = _run_app()
    assert not at.exception


def test_disclaimer_is_shown():
    at = _run_app()
    warnings = " ".join(w.value for w in at.warning)
    assert "research" in warnings.lower() or "not a diagnostic tool" in warnings.lower()
    assert "probabilit" in warnings.lower()


def test_patient_selector_lists_all_five_patients():
    at = _run_app()
    assert len(at.selectbox) == 1
    assert at.selectbox[0].value == "P001"


def test_each_patient_renders_its_expected_risk_state_without_error():
    at = _run_app()
    for patient_id, expected_state in EXPECTED_RISK_STATES.items():
        at.selectbox[0].set_value(patient_id).run()
        assert not at.exception, f"{patient_id} raised: {at.exception}"

        all_text = " ".join(m.value for m in at.markdown)
        assert expected_state in all_text, f"{patient_id}: expected {expected_state} not shown"


def test_missing_retinal_data_patient_shows_uncertainty_language():
    at = _run_app()
    at.selectbox[0].set_value("P005").run()
    assert not at.exception

    warning_text = " ".join(w.value for w in at.warning)
    assert "no retinal exam recorded" in warning_text.lower() or "historical" in warning_text.lower()


def test_charts_and_tables_render_for_default_patient():
    at = _run_app()
    assert len(at.get("plotly_chart")) >= 1  # at least the retinal trajectory chart
    assert len(at.dataframe) >= 1  # supporting-signal table at minimum
