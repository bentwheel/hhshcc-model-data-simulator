"""Tests for output file writers."""

import pandas as pd

from hhshcc_sim.output.writers import (
    write_all_output_files,
    write_hcpcs_file,
    write_person_file,
)


def test_write_person_file(tmp_path):
    """Test PERSON.csv output format."""
    demographics = pd.DataFrame({
        "ENROLID": ["10001", "10002"],
        "SEX": [1, 2],
        "DOB": [19850315, 19920708],
        "AGE_LAST": [37, 30],
    })
    enrollment = pd.DataFrame({
        "ENROLID": ["10001", "10002"],
        "ENROLDURATION": [12, 8],
        "METAL": ["silver", "bronze"],
        "CSR_INDICATOR": [1, 1],
    })

    path = write_person_file(demographics, enrollment, tmp_path)
    result = pd.read_csv(path, dtype=str)

    assert list(result.columns) == [
        "ENROLID", "SEX", "DOB", "AGE_LAST", "METAL", "CSR_INDICATOR", "ENROLDURATION"
    ]
    assert len(result) == 2
    assert result.iloc[0]["METAL"] == "silver"


def test_write_hcpcs_file_empty(tmp_path):
    """Test HCPCS.csv with empty DataFrame."""
    hcpcs = pd.DataFrame(columns=["ENROLID", "HCPCS"])
    path = write_hcpcs_file(hcpcs, tmp_path)
    result = pd.read_csv(path, dtype=str)

    assert list(result.columns) == ["ENROLID", "HCPCS"]
    assert len(result) == 0


def test_write_hcpcs_file_with_data(tmp_path):
    """Test HCPCS.csv with actual records."""
    hcpcs = pd.DataFrame({
        "ENROLID": ["10001", "10002"],
        "HCPCS": ["J1745", "J0135"],
    })
    path = write_hcpcs_file(hcpcs, tmp_path)
    result = pd.read_csv(path, dtype=str)

    assert list(result.columns) == ["ENROLID", "HCPCS"]
    assert len(result) == 2
    assert result.iloc[0]["HCPCS"] == "J1745"


def test_write_all_output_files(tmp_path):
    """Test that all 4 output files are created."""
    demographics = pd.DataFrame({
        "ENROLID": ["10001"],
        "SEX": [1],
        "DOB": [19850315],
        "AGE_LAST": [37],
    })
    enrollment = pd.DataFrame({
        "ENROLID": ["10001"],
        "ENROLDURATION": [12],
        "METAL": ["silver"],
        "CSR_INDICATOR": [1],
    })
    diag = pd.DataFrame({
        "ENROLID": ["10001"],
        "DIAG": ["E1165"],
        "DIAGNOSIS_SERVICE_DATE": [20220415],
        "AGE_AT_DIAGNOSIS": [36],
    })
    ndc = pd.DataFrame({
        "ENROLID": ["10001"],
        "NDC": ["00093310905"],
    })
    hcpcs = pd.DataFrame({
        "ENROLID": ["10001"],
        "HCPCS": ["J1745"],
    })

    output_dir = tmp_path / "output"
    paths = write_all_output_files(demographics, enrollment, diag, ndc, hcpcs, output_dir)

    assert "person" in paths
    assert "diag" in paths
    assert "ndc" in paths
    assert "hcpcs" in paths

    for path in paths.values():
        assert path.exists()
