"""Tests for output validators."""

import pandas as pd

from hhshcc_sim.output.validators import validate_all_outputs, validate_person_file


def _write_valid_outputs(output_dir):
    """Helper to write a set of valid output files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame({
        "ENROLID": ["10001"],
        "SEX": [1],
        "DOB": [19850315],
        "AGE_LAST": [37],
        "METAL": ["silver"],
        "CSR_INDICATOR": [1],
        "ENROLDURATION": [12],
    }).to_csv(output_dir / "PERSON.csv", index=False)

    pd.DataFrame({
        "ENROLID": ["10001"],
        "DIAG": ["E1165"],
        "DIAGNOSIS_SERVICE_DATE": [20220415],
        "AGE_AT_DIAGNOSIS": [36],
    }).to_csv(output_dir / "DIAG.csv", index=False)

    pd.DataFrame({
        "ENROLID": ["10001"],
        "NDC": ["00093310905"],
    }).to_csv(output_dir / "NDC.csv", index=False)

    pd.DataFrame(columns=["ENROLID", "HCPCS"]).to_csv(
        output_dir / "HCPCS.csv", index=False
    )


def test_validate_valid_outputs(tmp_path):
    """Test that valid outputs pass validation."""
    output_dir = tmp_path / "output"
    _write_valid_outputs(output_dir)

    errors = validate_all_outputs(output_dir)
    assert errors == []


def test_validate_missing_file(tmp_path):
    """Test that missing files are detected."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)

    errors = validate_all_outputs(output_dir)
    assert len(errors) > 0
    assert any("not found" in e for e in errors)


def test_validate_invalid_sex(tmp_path):
    """Test that invalid SEX values are caught."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)

    pd.DataFrame({
        "ENROLID": ["10001"],
        "SEX": [3],  # Invalid
        "DOB": [19850315],
        "AGE_LAST": [37],
        "METAL": ["silver"],
        "CSR_INDICATOR": [1],
        "ENROLDURATION": [12],
    }).to_csv(output_dir / "PERSON.csv", index=False)

    errors = validate_person_file(output_dir / "PERSON.csv")
    assert any("invalid SEX" in e for e in errors)


def test_validate_orphan_enrolid(tmp_path):
    """Test that DIAG ENROLIDs not in PERSON are caught."""
    output_dir = tmp_path / "output"
    _write_valid_outputs(output_dir)

    # Add an orphan ENROLID to DIAG
    pd.DataFrame({
        "ENROLID": ["10001", "99999"],
        "DIAG": ["E1165", "I10"],
        "DIAGNOSIS_SERVICE_DATE": [20220415, 20220601],
        "AGE_AT_DIAGNOSIS": [36, 40],
    }).to_csv(output_dir / "DIAG.csv", index=False)

    errors = validate_all_outputs(output_dir)
    assert any("not in PERSON" in e for e in errors)
