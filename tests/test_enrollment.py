"""Tests for enrollment processor."""

import numpy as np
import pandas as pd

from hhshcc_sim.processors.enrollment import (
    process_enrollment,
    simulate_csr_indicator,
    simulate_metal_level,
)


def test_simulate_metal_level_under_30():
    """Test that catastrophic plans are available for persons under 30."""
    rng = np.random.default_rng(42)
    # Run many samples for a young person
    metals = [simulate_metal_level(25, 400.0, rng) for _ in range(1000)]
    assert "catastrophic" in metals


def test_simulate_metal_level_over_30():
    """Test that catastrophic plans are NOT available for persons 30+."""
    rng = np.random.default_rng(42)
    metals = [simulate_metal_level(35, 400.0, rng) for _ in range(1000)]
    assert "catastrophic" not in metals


def test_simulate_metal_level_low_income_silver_bias():
    """Test that low-income persons are more likely to get silver."""
    rng_low = np.random.default_rng(42)
    rng_high = np.random.default_rng(42)

    low_income_metals = [simulate_metal_level(40, 130.0, rng_low) for _ in range(1000)]
    high_income_metals = [simulate_metal_level(40, 500.0, rng_high) for _ in range(1000)]

    low_silver_pct = low_income_metals.count("silver") / len(low_income_metals)
    high_silver_pct = high_income_metals.count("silver") / len(high_income_metals)

    # Low income should have higher silver percentage
    assert low_silver_pct > high_silver_pct


def test_simulate_csr_indicator_non_silver():
    """Test that non-silver plans always get CSR=1."""
    rng = np.random.default_rng(42)
    for metal in ["bronze", "gold", "platinum", "catastrophic"]:
        assert simulate_csr_indicator(metal, 130.0, rng) == 1


def test_simulate_csr_indicator_silver_low_income():
    """Test CSR assignment for silver plans at different income levels."""
    rng = np.random.default_rng(42)

    # 100-150% FPL -> CSR variant 3
    assert simulate_csr_indicator("silver", 130.0, rng) == 3

    # 150-200% FPL -> CSR variant 3
    assert simulate_csr_indicator("silver", 175.0, rng) == 3

    # 200-250% FPL -> CSR variant 1
    assert simulate_csr_indicator("silver", 225.0, rng) == 1

    # Above 250% -> CSR variant 1
    assert simulate_csr_indicator("silver", 300.0, rng) == 1


def test_process_enrollment(simulator_config):
    """Test full enrollment processing."""
    demographics = pd.DataFrame({
        "ENROLID": ["10001", "10002", "10003"],
        "AGE_LAST": [37, 30, 7],
        "POVLEV": [350.0, 125.0, 500.0],
        "N_ENROLLED_MONTHS": [12, 6, 12],
    })

    result = process_enrollment(demographics, simulator_config)

    assert len(result) == 3
    assert set(result.columns) == {"ENROLID", "ENROLDURATION", "METAL", "CSR_INDICATOR"}
    assert result["ENROLDURATION"].between(1, 12).all()
    assert result["METAL"].isin(["platinum", "gold", "silver", "bronze", "catastrophic"]).all()
    assert result["CSR_INDICATOR"].between(1, 11).all()
