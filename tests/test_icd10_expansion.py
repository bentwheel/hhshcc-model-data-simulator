"""Tests for ICD-10 code expansion."""

import numpy as np

from hhshcc_sim.processors.icd10_expansion import (
    build_expansion_probabilities,
    expand_icd10_code,
    expand_icd10_codes_mode,
)


def test_build_expansion_probabilities(mock_ca_freq_df):
    """Test probability table construction from frequency data."""
    prob_tables = build_expansion_probabilities(mock_ca_freq_df)

    # Should have entries for each 3-char prefix
    assert "E11" in prob_tables
    assert "I10" in prob_tables
    assert "J45" in prob_tables
    assert "R05" in prob_tables
    assert "F32" in prob_tables

    # E11 should have 3 full codes
    assert len(prob_tables["E11"]) == 3

    # Probabilities should sum to ~1.0 for each column
    for prefix, table in prob_tables.items():
        for col in ["ED_PROB", "IP_PROB", "OP_PROB", "TOTAL_PROB"]:
            assert abs(table[col].sum() - 1.0) < 1e-10, f"{prefix} {col} doesn't sum to 1"


def test_expand_icd10_code_known_prefix(mock_prob_tables):
    """Test expansion of a known 3-char prefix."""
    rng = np.random.default_rng(42)
    result = expand_icd10_code("E11", "total", mock_prob_tables, rng)

    # Should be one of the known E11 expansions
    assert result in ["E1110", "E1165", "E119"]


def test_expand_icd10_code_unknown_prefix(mock_prob_tables):
    """Test expansion of an unknown prefix returns the prefix as-is."""
    rng = np.random.default_rng(42)
    result = expand_icd10_code("Z99", "total", mock_prob_tables, rng)
    assert result == "Z99"


def test_expand_icd10_code_single_expansion(mock_prob_tables):
    """Test that I10 (only one full code) always returns I10."""
    rng = np.random.default_rng(42)
    for _ in range(100):
        assert expand_icd10_code("I10", "total", mock_prob_tables, rng) == "I10"


def test_expand_icd10_code_deterministic(mock_prob_tables):
    """Test deterministic expansion with same seed."""
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)

    results1 = [expand_icd10_code("E11", "total", mock_prob_tables, rng1) for _ in range(100)]
    results2 = [expand_icd10_code("E11", "total", mock_prob_tables, rng2) for _ in range(100)]

    assert results1 == results2


def test_expand_icd10_codes_mode(mock_prob_tables):
    """Test mode-based expansion returns a valid profile."""
    rng = np.random.default_rng(42)
    codes = ["E11", "I10", "J45"]
    settings = ["op", "total", "ed"]

    result = expand_icd10_codes_mode(codes, settings, mock_prob_tables, rng, n_simulations=100)

    assert len(result) == 3
    assert result[0] in ["E1110", "E1165", "E119"]
    assert result[1] == "I10"
    assert result[2] in ["J4520", "J459"]
