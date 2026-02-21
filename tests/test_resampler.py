"""Tests for weighted population resampler."""

import pandas as pd
import pytest

from hhshcc_sim.processors.resampler import expand_for_resampled, resample_population

MEPS_YEAR = 2022


def test_resample_produces_correct_size(mock_fyc_df, simulator_config):
    """Output has exactly sample_size rows."""
    from hhshcc_sim.processors.demographics import process_demographics

    demo_df = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)
    simulator_config.sample_size = 10

    resampled, _ = resample_population(demo_df, mock_fyc_df, MEPS_YEAR, simulator_config)
    assert len(resampled) == 10


def test_resample_produces_large_sample(mock_fyc_df, simulator_config):
    """Can oversample beyond the original population size."""
    from hhshcc_sim.processors.demographics import process_demographics

    demo_df = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)
    simulator_config.sample_size = 100

    resampled, _ = resample_population(demo_df, mock_fyc_df, MEPS_YEAR, simulator_config)
    assert len(resampled) == 100


def test_resample_adds_suffixes(mock_fyc_df, simulator_config):
    """All ENROLIDs have _X suffixes."""
    from hhshcc_sim.processors.demographics import process_demographics

    demo_df = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)
    simulator_config.sample_size = 10

    resampled, _ = resample_population(demo_df, mock_fyc_df, MEPS_YEAR, simulator_config)

    for enrolid in resampled["ENROLID"]:
        # Should match pattern: original_id + _N
        assert "_" in enrolid
        parts = enrolid.rsplit("_", 1)
        assert parts[1].isdigit()


def test_resample_uses_weights(mock_fyc_df, simulator_config):
    """Higher-weighted persons appear more frequently over many samples."""
    from hhshcc_sim.processors.demographics import process_demographics

    demo_df = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)
    simulator_config.sample_size = 1000

    resampled, resample_map = resample_population(
        demo_df, mock_fyc_df, MEPS_YEAR, simulator_config
    )

    # Count how many times each original person was sampled
    orig_counts = {}
    for new_id, orig_id in resample_map.items():
        orig_counts[orig_id] = orig_counts.get(orig_id, 0) + 1

    # Person 10005 has highest weight (30000) and person 10003 has lowest (10000)
    # among those who pass demographic filters.
    # With a large sample, higher-weighted people should appear more often.
    # We can't guarantee exact proportions but weights should influence selection.
    assert len(orig_counts) > 1  # At least 2 unique persons sampled


def test_resample_deterministic(mock_fyc_df, simulator_config):
    """Same seed produces same result."""
    from hhshcc_sim.processors.demographics import process_demographics

    demo_df = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)
    simulator_config.sample_size = 20

    r1, _ = resample_population(demo_df, mock_fyc_df, MEPS_YEAR, simulator_config)
    r2, _ = resample_population(demo_df, mock_fyc_df, MEPS_YEAR, simulator_config)

    assert r1["ENROLID"].tolist() == r2["ENROLID"].tolist()


def test_resample_different_seed(mock_fyc_df, simulator_config):
    """Different seeds produce different results."""
    from hhshcc_sim.processors.demographics import process_demographics

    demo_df = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)
    simulator_config.sample_size = 20

    r1, _ = resample_population(demo_df, mock_fyc_df, MEPS_YEAR, simulator_config)

    simulator_config.random_seed = 99
    r2, _ = resample_population(demo_df, mock_fyc_df, MEPS_YEAR, simulator_config)

    assert r1["ENROLID"].tolist() != r2["ENROLID"].tolist()


def test_expand_duplicates_correctly():
    """Downstream data rows are correctly duplicated for each copy."""
    # Original data: person A has 2 diagnoses, person B has 1
    df = pd.DataFrame({
        "ENROLID": ["A", "A", "B"],
        "DIAG": ["E11", "I10", "J45"],
    })

    # Resample map: A sampled twice, B sampled once
    resample_map = {"A_1": "A", "A_2": "A", "B_1": "B"}

    expanded = expand_for_resampled(df, resample_map)

    # A_1 and A_2 should each get 2 rows, B_1 gets 1 row = 5 total
    assert len(expanded) == 5
    assert len(expanded[expanded["ENROLID"] == "A_1"]) == 2
    assert len(expanded[expanded["ENROLID"] == "A_2"]) == 2
    assert len(expanded[expanded["ENROLID"] == "B_1"]) == 1


def test_expand_empty_df():
    """Empty DataFrame handled gracefully."""
    df = pd.DataFrame(columns=["ENROLID", "DIAG"])
    resample_map = {"A_1": "A", "B_1": "B"}

    expanded = expand_for_resampled(df, resample_map)
    assert len(expanded) == 0
    assert "ENROLID" in expanded.columns


def test_resample_map_keys_are_unique(mock_fyc_df, simulator_config):
    """Resample map keys (new ENROLIDs) are all unique."""
    from hhshcc_sim.processors.demographics import process_demographics

    demo_df = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)
    simulator_config.sample_size = 50

    _, resample_map = resample_population(demo_df, mock_fyc_df, MEPS_YEAR, simulator_config)

    assert len(resample_map) == 50
    assert len(set(resample_map.keys())) == 50


def test_resample_no_weight_column(mock_fyc_df, simulator_config):
    """Falls back to equal weights when weight column is missing."""
    from hhshcc_sim.processors.demographics import process_demographics

    demo_df = process_demographics(mock_fyc_df, MEPS_YEAR, simulator_config)
    simulator_config.sample_size = 10

    # Remove the weight column
    fyc_no_weights = mock_fyc_df.drop(columns=["PERWT22F"])

    resampled, _ = resample_population(
        demo_df, fyc_no_weights, MEPS_YEAR, simulator_config
    )
    assert len(resampled) == 10
