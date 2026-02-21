"""Tests for reproducibility manifest."""

import json

import pandas as pd

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.output.manifest import write_manifest
from hhshcc_sim.output.writers import write_all_output_files


def _make_test_data():
    """Create minimal test DataFrames for writing output files."""
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
    diag = pd.DataFrame({
        "ENROLID": ["10001", "10001", "10002"],
        "DIAG": ["E1165", "I10", "J45"],
        "DIAGNOSIS_SERVICE_DATE": [20250415, 20250601, 20250301],
        "AGE_AT_DIAGNOSIS": [39, 39, 32],
    })
    ndc = pd.DataFrame({
        "ENROLID": ["10001", "10002"],
        "NDC": ["00093310905", "00002771001"],
    })
    hcpcs = pd.DataFrame({
        "ENROLID": ["10001"],
        "HCPCS": ["J1745"],
    })
    return demographics, enrollment, diag, ndc, hcpcs


def test_manifest_created(tmp_path):
    """Test that manifest.json is created with expected structure."""
    config = SimulatorConfig(meps_years=[2022], benefit_year=2025, output_dir=tmp_path)
    demographics, enrollment, diag, ndc, hcpcs = _make_test_data()

    output_paths = write_all_output_files(
        demographics, enrollment, diag, ndc, hcpcs, tmp_path
    )
    row_counts = {
        "person": len(demographics),
        "diag": len(diag),
        "ndc": len(ndc),
        "hcpcs": len(hcpcs),
    }

    manifest_path = write_manifest(config, output_paths, row_counts, [], 10.5)

    assert manifest_path.exists()
    assert manifest_path.name == "manifest.json"

    data = json.loads(manifest_path.read_text())
    assert "timestamp" in data
    assert "python_version" in data
    assert "config" in data
    assert "output_files" in data
    assert "validation" in data
    assert "elapsed_seconds" in data


def test_manifest_config_values(tmp_path):
    """Test that config values in manifest match the SimulatorConfig."""
    config = SimulatorConfig(
        meps_years=[2021, 2022],
        benefit_year=2025,
        random_seed=99,
        dx_mode="mode",
        n_simulations=100,
        age_min=18,
        age_max=64,
        output_dir=tmp_path,
    )
    demographics, enrollment, diag, ndc, hcpcs = _make_test_data()
    output_paths = write_all_output_files(
        demographics, enrollment, diag, ndc, hcpcs, tmp_path
    )
    row_counts = {"person": 2, "diag": 3, "ndc": 2, "hcpcs": 1}

    manifest_path = write_manifest(config, output_paths, row_counts, [], 5.0)
    data = json.loads(manifest_path.read_text())

    assert data["config"]["meps_years"] == [2021, 2022]
    assert data["config"]["benefit_year"] == 2025
    assert data["config"]["random_seed"] == 99
    assert data["config"]["dx_mode"] == "mode"
    assert data["config"]["n_simulations"] == 100
    assert data["config"]["age_min"] == 18
    assert data["config"]["age_max"] == 64


def test_manifest_row_counts(tmp_path):
    """Test that row counts are recorded correctly."""
    config = SimulatorConfig(meps_years=[2022], benefit_year=2025, output_dir=tmp_path)
    demographics, enrollment, diag, ndc, hcpcs = _make_test_data()
    output_paths = write_all_output_files(
        demographics, enrollment, diag, ndc, hcpcs, tmp_path
    )
    row_counts = {"person": 2, "diag": 3, "ndc": 2, "hcpcs": 1}

    manifest_path = write_manifest(config, output_paths, row_counts, [], 1.0)
    data = json.loads(manifest_path.read_text())

    assert data["output_files"]["person"]["row_count"] == 2
    assert data["output_files"]["diag"]["row_count"] == 3
    assert data["output_files"]["ndc"]["row_count"] == 2
    assert data["output_files"]["hcpcs"]["row_count"] == 1

    # Each file should have size_bytes > 0
    for name in ["person", "diag", "ndc", "hcpcs"]:
        assert data["output_files"][name]["size_bytes"] > 0


def test_manifest_validation_passed(tmp_path):
    """Test manifest with no validation errors."""
    config = SimulatorConfig(meps_years=[2022], benefit_year=2025, output_dir=tmp_path)
    demographics, enrollment, diag, ndc, hcpcs = _make_test_data()
    output_paths = write_all_output_files(
        demographics, enrollment, diag, ndc, hcpcs, tmp_path
    )

    manifest_path = write_manifest(config, output_paths, {}, [], 1.0)
    data = json.loads(manifest_path.read_text())

    assert data["validation"]["passed"] is True
    assert data["validation"]["error_count"] == 0
    assert data["validation"]["errors"] == []


def test_manifest_validation_failed(tmp_path):
    """Test manifest with validation errors."""
    config = SimulatorConfig(meps_years=[2022], benefit_year=2025, output_dir=tmp_path)
    demographics, enrollment, diag, ndc, hcpcs = _make_test_data()
    output_paths = write_all_output_files(
        demographics, enrollment, diag, ndc, hcpcs, tmp_path
    )
    errors = ["PERSON.csv missing SEX column", "DIAG.csv has orphan ENROLIDs"]

    manifest_path = write_manifest(config, output_paths, {}, errors, 1.0)
    data = json.loads(manifest_path.read_text())

    assert data["validation"]["passed"] is False
    assert data["validation"]["error_count"] == 2
    assert data["validation"]["errors"] == errors


def test_manifest_with_prefix(tmp_path):
    """Test manifest respects output_prefix."""
    config = SimulatorConfig(
        meps_years=[2022], benefit_year=2025, output_dir=tmp_path, output_prefix="sim_"
    )
    demographics, enrollment, diag, ndc, hcpcs = _make_test_data()
    output_paths = write_all_output_files(
        demographics, enrollment, diag, ndc, hcpcs, tmp_path, prefix="sim_"
    )

    manifest_path = write_manifest(config, output_paths, {}, [], 1.0)

    assert manifest_path.name == "sim_manifest.json"
    data = json.loads(manifest_path.read_text())
    assert data["config"]["output_prefix"] == "sim_"
