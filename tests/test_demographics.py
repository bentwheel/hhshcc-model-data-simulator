"""Tests for demographics processor."""

from hhshcc_sim.processors.demographics import process_demographics


def test_process_demographics_basic(mock_fyc_df, simulator_config):
    """Test basic demographics processing with mock FYC data."""
    result = process_demographics(mock_fyc_df, simulator_config)

    # Person 10005 has only 4 months coverage (Sep-Dec) -> should still be included
    # All 5 persons have at least 1 month of private coverage in this mock data
    # But person 10005 has some months covered, so they should be included
    assert len(result) > 0

    # Check required columns exist
    for col in ["ENROLID", "SEX", "DOB", "AGE_LAST", "POVLEV", "ENROLLED_MONTHS"]:
        assert col in result.columns

    # SEX should be 1 or 2
    assert result["SEX"].isin([1, 2]).all()

    # DOB should be 8-digit YYYYMMDD
    assert (result["DOB"] > 19000101).all()
    assert (result["DOB"] < 20300101).all()

    # AGE_LAST should be 0-64 (our filter range)
    assert (result["AGE_LAST"] >= 0).all()
    assert (result["AGE_LAST"] <= 64).all()


def test_process_demographics_age_filter(mock_fyc_df, simulator_config):
    """Test that age filtering works correctly."""
    # Person born in 1960 would be 62 in 2022 -> included
    # Person born in 2015 would be 7 in 2022 -> included
    simulator_config.age_min = 21
    simulator_config.age_max = 64
    result = process_demographics(mock_fyc_df, simulator_config)

    # Only adults 21+ should remain
    assert (result["AGE_LAST"] >= 21).all()


def test_process_demographics_deterministic(mock_fyc_df, simulator_config):
    """Test that DOB simulation is deterministic with same seed."""
    result1 = process_demographics(mock_fyc_df, simulator_config)
    result2 = process_demographics(mock_fyc_df, simulator_config)

    assert result1["DOB"].tolist() == result2["DOB"].tolist()


def test_process_demographics_different_seed(mock_fyc_df, simulator_config):
    """Test that different seeds produce different DOB days."""
    result1 = process_demographics(mock_fyc_df, simulator_config)

    simulator_config.random_seed = 99
    result2 = process_demographics(mock_fyc_df, simulator_config)

    # DOBs should differ (at least in the day portion) for most persons
    # (not guaranteed for all due to hash collisions, but very likely)
    assert result1["DOB"].tolist() != result2["DOB"].tolist()
