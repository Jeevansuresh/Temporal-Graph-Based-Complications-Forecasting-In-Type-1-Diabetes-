"""Test helper: build a PatientTemporalProfile in memory, without Neo4j.

Used by rule-engine / risk-aggregation / explanation unit tests so edge
cases (e.g. R010 INCREASING_CONCERN, which none of the 5 synthetic cases
happen to exercise) can be tested directly.
"""

from app.temporal.numeric_features import analyze_numeric_series
from app.temporal.profile import PatientTemporalProfile
from app.temporal.retinal_trajectory import analyze_retinal_trajectory


def build_test_profile(
    patient_id="TEST",
    dates=None,
    hba1c=None,
    sbp=None,
    dbp=None,
    ldl=None,
    uacr=None,
    egfr=None,
    t1d_duration_years=None,
    retinal_stages=None,
    age=13,
    sex="F",
    height_cm=150,
    puberty_status="started",
) -> PatientTemporalProfile:
    dates = dates or []

    def series(concept, values):
        values = values or []
        return analyze_numeric_series(concept, dates[: len(values)], values)

    numeric_features = {
        "HbA1c": series("HbA1c", hba1c),
        "Systolic_BP": series("Systolic_BP", sbp),
        "Diastolic_BP": series("Diastolic_BP", dbp),
        "LDL": series("LDL", ldl),
        "UACR": series("UACR", uacr),
        "eGFR": series("eGFR", egfr),
        "T1D_Duration": series("T1D_Duration", t1d_duration_years),
    }

    observed = []
    if retinal_stages is not None:
        for date, stage in zip(dates, retinal_stages):
            if stage is not None:
                observed.append({"date": date, "stage_index": stage})
    retinal_trajectory = analyze_retinal_trajectory(dates, observed)

    context = {
        "age": age,
        "sex": sex,
        "height_cm": height_cm,
        "puberty_status": puberty_status,
        "t1d_diagnosis": None,
    }

    return PatientTemporalProfile(
        patient_id=patient_id,
        context=context,
        numeric_features=numeric_features,
        retinal_trajectory=retinal_trajectory,
    )
