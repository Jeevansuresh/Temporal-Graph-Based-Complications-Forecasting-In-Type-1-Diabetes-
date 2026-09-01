from app.graph.csv_validation import load_csv_rows
from app.graph.patient_validation import load_synthetic_cases, validate_synthetic_cases


def _known_concepts():
    return {row["name"] for row in load_csv_rows()["nodes"]}


def test_real_synthetic_cases_are_valid_and_fully_mapped():
    data = load_synthetic_cases()
    result = validate_synthetic_cases(data, _known_concepts())
    assert result.is_valid
    assert result.unmapped_concepts == []
    assert len(data["cases"]) == 5


def test_detects_missing_top_level_keys():
    result = validate_synthetic_cases({"cases": []}, _known_concepts())
    assert not result.is_valid
    assert "schema" in result.missing_top_level_keys


def test_detects_duplicate_patient_ids():
    case = {
        "id": "P001",
        "age": 10,
        "sex": "F",
        "height_cm": 140,
        "puberty_status": "not_started",
        "t1d_diagnosis": "2020-01-01",
        "timeline": [],
    }
    data = {"schema": {}, "cases": [case, dict(case)]}
    result = validate_synthetic_cases(data, _known_concepts())
    assert not result.is_valid
    assert result.duplicate_patient_ids == ["P001"]


def test_detects_missing_required_case_fields():
    data = {
        "schema": {},
        "cases": [{"id": "P099", "timeline": []}],
    }
    result = validate_synthetic_cases(data, _known_concepts())
    assert not result.is_valid
    assert any("P099" in item for item in result.cases_missing_fields)


def test_detects_invalid_visit_date():
    case = {
        "id": "P098",
        "age": 10,
        "sex": "F",
        "height_cm": 140,
        "puberty_status": "not_started",
        "t1d_diagnosis": "2020-01-01",
        "timeline": [{"date": "not-a-date", "hba1c": 7.0}],
    }
    data = {"schema": {}, "cases": [case]}
    result = validate_synthetic_cases(data, _known_concepts())
    assert not result.is_valid
    assert any("P098" in item for item in result.invalid_dates)


def test_detects_out_of_range_retinal_stage():
    case = {
        "id": "P097",
        "age": 10,
        "sex": "F",
        "height_cm": 140,
        "puberty_status": "not_started",
        "t1d_diagnosis": "2020-01-01",
        "timeline": [{"date": "2024-01-01", "retinal_stage": 9}],
    }
    data = {"schema": {}, "cases": [case]}
    result = validate_synthetic_cases(data, _known_concepts())
    assert not result.is_valid
    assert any("P097" in item for item in result.invalid_retinal_stage)


def test_null_retinal_stage_is_not_flagged_as_invalid():
    case = {
        "id": "P096",
        "age": 10,
        "sex": "F",
        "height_cm": 140,
        "puberty_status": "not_started",
        "t1d_diagnosis": "2020-01-01",
        "timeline": [{"date": "2024-01-01", "retinal_stage": None}],
    }
    data = {"schema": {}, "cases": [case]}
    result = validate_synthetic_cases(data, _known_concepts())
    assert result.invalid_retinal_stage == []


def test_detects_unmapped_concept_when_ckg_incomplete():
    data = load_synthetic_cases()
    result = validate_synthetic_cases(data, {"HbA1c"})
    assert not result.is_valid
    assert "Systolic_BP" in result.unmapped_concepts
