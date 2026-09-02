from app.reasoning.rule_engine import (
    evaluate_all_rules,
    evaluate_bp_risk_signal,
    evaluate_glycemic_risk_signal,
    evaluate_kidney_context_risk_signal,
    evaluate_lipid_risk_signal,
)
from tests.profile_builder import build_test_profile

DATES = ["2024-01-10", "2025-01-10", "2026-01-10"]


# ---- R006 Glycemic_Risk_Signal ----------------------------------------


def test_glycemic_signal_fires_on_increasing_hba1c():
    profile = build_test_profile(dates=DATES, hba1c=[7.0, 7.8, 8.4])
    satisfied, _ = evaluate_glycemic_risk_signal(profile)
    assert satisfied is True


def test_glycemic_signal_does_not_fire_on_stable_hba1c():
    profile = build_test_profile(dates=DATES, hba1c=[7.0, 7.1, 7.0])
    satisfied, _ = evaluate_glycemic_risk_signal(profile)
    assert satisfied is False


def test_glycemic_signal_insufficient_data():
    profile = build_test_profile(dates=DATES, hba1c=[7.0])
    satisfied, reason = evaluate_glycemic_risk_signal(profile)
    assert satisfied is False
    assert "Insufficient" in reason


# ---- R007 BP_Risk_Signal (ADA-grounded, REF003) ------------------------


def test_bp_signal_not_classified_under_age_13():
    profile = build_test_profile(dates=DATES, sbp=[125, 130, 135], dbp=[85, 88, 90], age=12)
    satisfied, reason = evaluate_bp_risk_signal(profile)
    assert satisfied is False
    assert "percentile" in reason


def test_bp_signal_fires_on_two_repeated_elevated_readings_age_13_plus():
    profile = build_test_profile(dates=DATES, sbp=[110, 120, 128], dbp=[70, 76, 82], age=13)
    satisfied, _ = evaluate_bp_risk_signal(profile)
    assert satisfied is True


def test_bp_signal_does_not_fire_on_single_elevated_reading():
    profile = build_test_profile(dates=DATES, sbp=[110, 118, 128], dbp=[70, 76, 82], age=13)
    satisfied, _ = evaluate_bp_risk_signal(profile)
    assert satisfied is False


def test_bp_signal_does_not_fire_when_never_elevated():
    profile = build_test_profile(dates=DATES, sbp=[110, 111, 112], dbp=[70, 70, 70], age=13)
    satisfied, _ = evaluate_bp_risk_signal(profile)
    assert satisfied is False


# ---- R008 Lipid_Risk_Signal (ADA pediatric LDL goal, REF002) -----------


def test_lipid_signal_fires_when_latest_ldl_at_or_above_goal():
    profile = build_test_profile(dates=DATES, ldl=[90, 108, 121])
    satisfied, _ = evaluate_lipid_risk_signal(profile)
    assert satisfied is True


def test_lipid_signal_does_not_fire_below_goal():
    profile = build_test_profile(dates=DATES, ldl=[90, 92, 91])
    satisfied, _ = evaluate_lipid_risk_signal(profile)
    assert satisfied is False


# ---- R009 Kidney_Context_Risk_Signal (ADA elevated UACR, REF001) -------


def test_kidney_signal_fires_on_two_confirmed_elevated_uacr():
    profile = build_test_profile(dates=DATES, uacr=[8, 31, 35])
    satisfied, _ = evaluate_kidney_context_risk_signal(profile)
    assert satisfied is True


def test_kidney_signal_does_not_fire_on_single_elevated_uacr():
    profile = build_test_profile(dates=DATES, uacr=[8, 15, 31])
    satisfied, _ = evaluate_kidney_context_risk_signal(profile)
    assert satisfied is False


def test_kidney_signal_ignores_egfr_decline_alone():
    # eGFR consistently declining but UACR never elevated -- must not fire.
    profile = build_test_profile(dates=DATES, uacr=[8, 8, 9], egfr=[112, 106, 100])
    satisfied, reason = evaluate_kidney_context_risk_signal(profile)
    assert satisfied is False
    assert "eGFR" in reason


# ---- R003/R004/R005 map directly onto retinal_trajectory ---------------


def test_r003_r004_r005_stable():
    profile = build_test_profile(dates=DATES, retinal_stages=[0, 0, 0])
    evaluations = evaluate_all_rules(profile)
    assert evaluations["R005"].satisfied is True
    assert evaluations["R003"].satisfied is False
    assert evaluations["R004"].satisfied is False


def test_r003_incident_and_r004_progression_both_satisfied():
    profile = build_test_profile(dates=DATES, retinal_stages=[0, 0, 1])
    evaluations = evaluate_all_rules(profile)
    assert evaluations["R003"].satisfied is True
    assert evaluations["R004"].satisfied is True
    assert evaluations["R005"].satisfied is False


def test_r004_progression_without_incident_when_existing_dr():
    profile = build_test_profile(dates=DATES, retinal_stages=[1, 1, 2])
    evaluations = evaluate_all_rules(profile)
    assert evaluations["R003"].satisfied is False
    assert evaluations["R004"].satisfied is True


# ---- Evidence/rule provenance is always retained ------------------------


def test_every_rule_evaluation_retains_rule_id_and_evidence_ids():
    profile = build_test_profile(dates=DATES, retinal_stages=[0, 0, 1], hba1c=[7.0, 7.8, 8.4])
    evaluations = evaluate_all_rules(profile)
    assert set(evaluations.keys()) == {f"R{n:03d}" for n in range(1, 14)}
    for rule_id, evaluation in evaluations.items():
        assert evaluation.rule_id == rule_id
        assert evaluation.evidence_ids, f"{rule_id} has no evidence_ids"


def test_r001_screening_eligibility():
    profile = build_test_profile(
        dates=DATES, t1d_duration_years=[3.5, 4.5, 5.5], age=13, puberty_status="started"
    )
    evaluations = evaluate_all_rules(profile)
    assert evaluations["R001"].satisfied is True


def test_r001_not_eligible_when_duration_too_short():
    profile = build_test_profile(dates=DATES, t1d_duration_years=[1.0, 2.0, 2.5], age=13)
    evaluations = evaluate_all_rules(profile)
    assert evaluations["R001"].satisfied is False
