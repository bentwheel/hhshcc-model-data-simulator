"""Tests for prescription processor."""

import pandas as pd

from hhshcc_sim.processors.prescriptions import clean_ndc, process_prescriptions


def test_clean_ndc_valid():
    """Test cleaning of valid NDC codes."""
    assert clean_ndc("00093310905") == "00093310905"
    assert clean_ndc("68180072009") == "68180072009"


def test_clean_ndc_with_dashes():
    """Test cleaning of NDC codes with dashes."""
    assert clean_ndc("0009-3310-905") == "00093310905"


def test_clean_ndc_short_padded():
    """Test that short NDC codes are zero-padded."""
    assert clean_ndc("93310905") == "00093310905"


def test_clean_ndc_missing():
    """Test that missing/negative values return None."""
    assert clean_ndc("-9") is None
    assert clean_ndc("-1") is None
    assert clean_ndc(None) is None


def test_clean_ndc_all_zeros():
    """Test that all-zero NDC returns None."""
    assert clean_ndc("00000000000") is None


def test_clean_ndc_with_decimal():
    """Test cleaning of NDC codes with decimal from Stata numeric conversion."""
    assert clean_ndc("93310905.0") == "00093310905"


def test_process_prescriptions(mock_pmed_df, simulator_config):
    """Test full prescription processing."""
    demographics = pd.DataFrame({
        "ENROLID": ["10001", "10002", "10003"],
    })

    result = process_prescriptions(mock_pmed_df, demographics, simulator_config)

    assert set(result.columns) == {"ENROLID", "NDC"}
    # Should exclude the -9 NDC value
    assert len(result) == 4  # 5 records minus 1 invalid
    # All NDCs should be 11 digits
    assert result["NDC"].str.match(r"^\d{11}$").all()
