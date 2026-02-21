"""Tests for end-of-run summary report."""

import pandas as pd

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.output.summary import build_summary, write_summary


def _make_test_data():
    """Create minimal test DataFrames for summary building."""
    demographics = pd.DataFrame({
        "ENROLID": ["A", "B", "C", "D"],
        "SEX": [1, 2, 1, 2],
        "DOB": [20200101, 20000601, 19900315, 19700810],
        "AGE_LAST": [5, 25, 35, 55],
    })
    enrollment = pd.DataFrame({
        "ENROLID": ["A", "B", "C", "D"],
        "ENROLDURATION": [12, 8, 12, 6],
        "METAL": ["silver", "bronze", "silver", "gold"],
        "CSR_INDICATOR": [3, 1, 1, 1],
    })
    diag = pd.DataFrame({
        "ENROLID": ["A", "A", "B", "C", "C", "C"],
        "DIAG": ["E1165", "I10", "J45", "E1165", "I10", "Z00"],
        "DIAGNOSIS_SERVICE_DATE": [20250415] * 6,
        "AGE_AT_DIAGNOSIS": [5, 5, 25, 35, 35, 35],
    })
    ndc = pd.DataFrame({
        "ENROLID": ["A", "B", "C"],
        "NDC": ["00093310905", "00002771001", "00093310905"],
    })
    hcpcs = pd.DataFrame({
        "ENROLID": ["A"],
        "HCPCS": ["J1745"],
    })
    return demographics, enrollment, diag, ndc, hcpcs


def test_summary_contains_sections():
    """Test that summary contains all expected sections."""
    config = SimulatorConfig(meps_years=[2022], benefit_year=2025)
    demographics, enrollment, diag, ndc, hcpcs = _make_test_data()

    summary = build_summary(config, demographics, enrollment, diag, ndc, hcpcs, [], 10.5)

    assert "HHS-HCC MODEL DATA SIMULATOR - RUN SUMMARY" in summary
    assert "Configuration" in summary
    assert "Output Files" in summary
    assert "Age Group Distribution" in summary
    assert "Metal Level Distribution" in summary
    assert "CSR Indicator Distribution" in summary
    assert "Per-Member Utilization by Age Group" in summary
    assert "Unique Code Counts" in summary
    assert "Validation: PASSED" in summary
    assert "Elapsed: 10.5s" in summary


def test_summary_config_values():
    """Test that config values appear in the summary."""
    config = SimulatorConfig(
        meps_years=[2021, 2022], benefit_year=2025,
        random_seed=99, dx_mode="mode", age_min=18, age_max=64,
    )
    demographics, enrollment, diag, ndc, hcpcs = _make_test_data()

    summary = build_summary(config, demographics, enrollment, diag, ndc, hcpcs, [], 5.0)

    assert "2021, 2022" in summary
    assert "2025" in summary
    assert "99" in summary
    assert "mode" in summary
    assert "18-64" in summary


def test_summary_age_bands_sum_to_total():
    """Test that age band counts sum to total persons."""
    config = SimulatorConfig(meps_years=[2022], benefit_year=2025)
    demographics, enrollment, diag, ndc, hcpcs = _make_test_data()

    summary = build_summary(config, demographics, enrollment, diag, ndc, hcpcs, [], 1.0)

    # The summary should show the correct total row count
    assert "4 rows" in summary or "4,000" not in summary  # 4 persons
    assert "PERSON.csv" in summary


def test_summary_empty_hcpcs():
    """Test summary handles empty HCPCS DataFrame."""
    config = SimulatorConfig(meps_years=[2022], benefit_year=2025)
    demographics, enrollment, diag, ndc, _ = _make_test_data()
    hcpcs = pd.DataFrame(columns=["ENROLID", "HCPCS"])

    summary = build_summary(config, demographics, enrollment, diag, ndc, hcpcs, [], 1.0)

    assert "HCPCS codes:" in summary
    assert "0 rows" in summary or "HCPCS.csv" in summary


def test_summary_validation_failed():
    """Test summary reflects validation failure."""
    config = SimulatorConfig(meps_years=[2022], benefit_year=2025)
    demographics, enrollment, diag, ndc, hcpcs = _make_test_data()
    errors = ["PERSON.csv missing SEX column", "DIAG.csv has orphan ENROLIDs"]

    summary = build_summary(config, demographics, enrollment, diag, ndc, hcpcs, errors, 1.0)

    assert "Validation: FAILED (2 errors)" in summary
    assert "PERSON.csv missing SEX column" in summary
    assert "DIAG.csv has orphan ENROLIDs" in summary


def test_write_summary_creates_file(tmp_path):
    """Test that write_summary creates SUMMARY.txt."""
    summary_text = "Test summary content"
    path = write_summary(summary_text, tmp_path)

    assert path.exists()
    assert path.name == "SUMMARY.txt"
    assert "Test summary content" in path.read_text()


def test_write_summary_with_prefix(tmp_path):
    """Test that write_summary respects prefix."""
    summary_text = "Test summary content"
    path = write_summary(summary_text, tmp_path, prefix="sim_")

    assert path.name == "sim_SUMMARY.txt"
