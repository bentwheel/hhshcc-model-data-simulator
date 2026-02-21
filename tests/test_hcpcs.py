"""Tests for HCPCS processor (RXC crosswalk)."""

import pandas as pd

from hhshcc_sim.processors.hcpcs import build_rxc_crosswalk, process_hcpcs


def _mock_ndc_to_rxc():
    """Mock Table 10a data."""
    return pd.DataFrame({
        "NDC": ["00093310905", "68180072009", "00378180010", "11111111111"],
        "RXC": [1, 1, 5, 8],
        "RXC_LABEL": [
            "Anti-Infective",
            "Anti-Infective",
            "Diabetes",
            "Immunosuppressant",
        ],
    })


def _mock_hcpcs_to_rxc():
    """Mock Table 10b data."""
    return pd.DataFrame({
        "HCPCS": ["J1745", "J0135", "J7502", "J3262"],
        "RXC": [1, 1, 5, 8],
        "RXC_LABEL": [
            "Anti-Infective",
            "Anti-Infective",
            "Diabetes",
            "Immunosuppressant",
        ],
    })


def test_build_rxc_crosswalk():
    """Test that crosswalk lookup tables are built correctly."""
    ndc_rxc_map, rxc_hcpcs_map = build_rxc_crosswalk(
        _mock_ndc_to_rxc(), _mock_hcpcs_to_rxc()
    )

    # NDC map should have 4 entries
    assert len(ndc_rxc_map) == 4
    assert ndc_rxc_map["00093310905"] == 1
    assert ndc_rxc_map["00378180010"] == 5

    # RXC HCPCS map should have 3 RXCs
    assert len(rxc_hcpcs_map) == 3
    assert set(rxc_hcpcs_map[1]) == {"J1745", "J0135"}
    assert rxc_hcpcs_map[5] == ["J7502"]
    assert rxc_hcpcs_map[8] == ["J3262"]


def test_process_hcpcs_basic(simulator_config):
    """Test basic HCPCS generation from NDC crosswalk."""
    ndc_df = pd.DataFrame({
        "ENROLID": ["10001", "10001", "10002"],
        "NDC": ["00093310905", "68180072009", "00378180010"],
    })

    ndc_rxc_map, rxc_hcpcs_map = build_rxc_crosswalk(
        _mock_ndc_to_rxc(), _mock_hcpcs_to_rxc()
    )

    result = process_hcpcs(ndc_df, ndc_rxc_map, rxc_hcpcs_map, simulator_config)

    assert len(result) > 0
    assert set(result.columns) == {"ENROLID", "HCPCS"}

    # All HCPCS codes should be from our mock data
    assert result["HCPCS"].isin(["J1745", "J0135", "J7502", "J3262"]).all()

    # Person 10001 has NDCs mapping to RXC 1, person 10002 to RXC 5
    assert "10001" in result["ENROLID"].values
    assert "10002" in result["ENROLID"].values


def test_process_hcpcs_no_matching_ndcs(simulator_config):
    """Test that unmatched NDCs produce no HCPCS records."""
    ndc_df = pd.DataFrame({
        "ENROLID": ["10001"],
        "NDC": ["99999999999"],  # Not in crosswalk
    })

    ndc_rxc_map, rxc_hcpcs_map = build_rxc_crosswalk(
        _mock_ndc_to_rxc(), _mock_hcpcs_to_rxc()
    )

    result = process_hcpcs(ndc_df, ndc_rxc_map, rxc_hcpcs_map, simulator_config)
    assert len(result) == 0
    assert set(result.columns) == {"ENROLID", "HCPCS"}


def test_process_hcpcs_empty_input(simulator_config):
    """Test with empty NDC DataFrame."""
    ndc_df = pd.DataFrame(columns=["ENROLID", "NDC"])

    ndc_rxc_map, rxc_hcpcs_map = build_rxc_crosswalk(
        _mock_ndc_to_rxc(), _mock_hcpcs_to_rxc()
    )

    result = process_hcpcs(ndc_df, ndc_rxc_map, rxc_hcpcs_map, simulator_config)
    assert len(result) == 0


def test_process_hcpcs_deterministic(simulator_config):
    """Test that HCPCS generation is deterministic with same seed."""
    ndc_df = pd.DataFrame({
        "ENROLID": ["10001", "10001"],
        "NDC": ["00093310905", "68180072009"],
    })

    ndc_rxc_map, rxc_hcpcs_map = build_rxc_crosswalk(
        _mock_ndc_to_rxc(), _mock_hcpcs_to_rxc()
    )

    result1 = process_hcpcs(ndc_df, ndc_rxc_map, rxc_hcpcs_map, simulator_config)
    result2 = process_hcpcs(ndc_df, ndc_rxc_map, rxc_hcpcs_map, simulator_config)

    assert result1["HCPCS"].tolist() == result2["HCPCS"].tolist()


def test_process_hcpcs_deduplicates(simulator_config):
    """Test that duplicate (ENROLID, HCPCS) pairs are removed."""
    # Two NDCs for same person, both mapping to RXC 1 which only has 2 HCPCS codes
    # Even if they get the same HCPCS, dedup should handle it
    ndc_df = pd.DataFrame({
        "ENROLID": ["10001", "10001"],
        "NDC": ["00093310905", "68180072009"],
    })

    # Build crosswalk with single HCPCS per RXC to force a duplicate
    single_hcpcs = pd.DataFrame({
        "HCPCS": ["J1745"],
        "RXC": [1],
        "RXC_LABEL": ["Anti-Infective"],
    })

    ndc_rxc_map, rxc_hcpcs_map = build_rxc_crosswalk(
        _mock_ndc_to_rxc(), single_hcpcs
    )

    result = process_hcpcs(ndc_df, ndc_rxc_map, rxc_hcpcs_map, simulator_config)

    # Should be deduplicated to 1 row
    assert len(result) == 1
    assert result.iloc[0]["HCPCS"] == "J1745"
