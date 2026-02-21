"""Tests for demographics processor."""

from hhshcc_sim.processors.demographics import process_demographics

MEPS_YEAR = 2022


def test_process_demographics_basic(mock_fyc_df, simulator_config):
    """Test basic demographics processing with mock FYC data."""
    result = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)

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

    # AGE_LAST should be 0-64 (our filter range, based on benefit year 2025)
    assert (result["AGE_LAST"] >= 0).all()
    assert (result["AGE_LAST"] <= 64).all()


def test_process_demographics_age_preserves_meps_distribution(mock_fyc_df, simulator_config):
    """Test that AGE_LAST preserves the person's age from the MEPS data year.

    DOBs are shifted forward by (benefit_year - meps_year) so that the MEPS age
    distribution is preserved. A person born in 1985 was age 37 in MEPS 2022,
    and should remain age 37 in the output regardless of the benefit year.
    """
    # Benefit year is 2025, MEPS year is 2022, offset = 3
    result = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)

    # Person born 1985 in MEPS 2022: age 37 (= 2022 - 1985), preserved via DOB shift
    person = result[result["ENROLID"] == "10001"]
    if len(person) > 0:
        assert person.iloc[0]["AGE_LAST"] == 37
        # DOBYY should be shifted: 1985 + 3 = 1988
        assert person.iloc[0]["DOBYY"] == 1988


def test_process_demographics_age_filter(mock_fyc_df, simulator_config):
    """Test that age filtering works correctly based on benefit year."""
    simulator_config.age_min = 21
    simulator_config.age_max = 64
    result = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)

    # Only adults 21+ (as of benefit year 2025) should remain
    assert (result["AGE_LAST"] >= 21).all()


def test_process_demographics_deterministic(mock_fyc_df, simulator_config):
    """Test that DOB simulation is deterministic with same seed."""
    result1 = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)
    result2 = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)

    assert result1["DOB"].tolist() == result2["DOB"].tolist()


def test_process_demographics_different_seed(mock_fyc_df, simulator_config):
    """Test that different seeds produce different DOB days."""
    result1 = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)

    simulator_config.random_seed = 99
    result2 = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)

    # DOBs should differ (at least in the day portion) for most persons
    # (not guaranteed for all due to hash collisions, but very likely)
    assert result1["DOB"].tolist() != result2["DOB"].tolist()
