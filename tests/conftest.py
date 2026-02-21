"""Shared test fixtures for HHS-HCC simulator tests."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def mock_fyc_df():
    """Small FYC-like DataFrame with known demographics and coverage.

    Simulates 5 persons with varying ages, sex, coverage, and income.
    Uses MEPS 2022 variable naming conventions (suffix '22').
    """
    data = {
        "DUPERSID": ["10001", "10002", "10003", "10004", "10005"],
        "SEX": [1, 2, 1, 2, 1],
        "DOBMM": [3, 7, 1, 11, 5],
        "DOBYY": [1985, 1992, 2015, 1960, 2000],
        # Monthly private insurance: 1=covered, 2=not covered
        "PRIJA22": [1, 1, 1, 1, 2],
        "PRIFE22": [1, 1, 1, 1, 2],
        "PRIMA22": [1, 1, 1, 1, 2],
        "PRIAP22": [1, 1, 1, 1, 2],
        "PRIMY22": [1, 1, 1, 1, 2],
        "PRIJU22": [1, 1, 1, 2, 2],
        "PRIJL22": [1, 2, 1, 2, 2],
        "PRIAU22": [1, 2, 1, 2, 2],
        "PRISE22": [1, 2, 1, 2, 1],
        "PRIOC22": [1, 2, 1, 2, 1],
        "PRINO22": [1, 2, 1, 2, 1],
        "PRIDE22": [1, 2, 1, 2, 1],
        # Poverty level (% FPL)
        "POVLEV22": [350.0, 125.0, 500.0, 180.0, 250.0],
        # Survey weight (persons represented in US population)
        "PERWT22F": [15000.0, 25000.0, 10000.0, 20000.0, 30000.0],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_cond_df():
    """Small conditions DataFrame with known 3-char ICD-10 codes."""
    data = {
        "DUPERSID": ["10001", "10001", "10002", "10003", "10004"],
        "ICD10CDX": ["E11", "I10", "J45", "R05", "F32"],
        "ERCOND": [2, 2, 1, 2, 2],
        "IPCOND": [2, 2, 2, 2, 2],
        "OPCOND": [1, 1, 2, 1, 1],
        "OBCOND": [2, 2, 2, 2, 2],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_pmed_df():
    """Small prescriptions DataFrame with known NDC codes."""
    data = {
        "DUPERSID": ["10001", "10001", "10002", "10002", "10003"],
        "RXNDC": ["00093310905", "68180072009", "00378180010", "-9", "00093310905"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_ca_freq_df():
    """Small ICD-10 frequency table for testing expansion."""
    data = {
        "ICD10CDX": ["E11", "E11", "E11", "I10", "J45", "J45", "R05", "F32", "F32"],
        "ICD10CM": ["E1110", "E1165", "E119", "I10", "J4520", "J459", "R05", "F320", "F321"],
        "ED_FREQ": [10, 50, 40, 100, 30, 70, 100, 60, 40],
        "IP_FREQ": [20, 60, 20, 100, 20, 80, 100, 50, 50],
        "OP_FREQ": [5, 70, 25, 100, 40, 60, 100, 55, 45],
        "TOTAL_FREQ": [35, 180, 85, 300, 90, 210, 300, 165, 135],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_prob_tables(mock_ca_freq_df):
    """Pre-built probability tables from mock CA frequency data."""
    from hhshcc_sim.processors.icd10_expansion import build_expansion_probabilities

    return build_expansion_probabilities(mock_ca_freq_df)


@pytest.fixture
def simulator_config(tmp_path):
    """A SimulatorConfig using temporary directories."""
    from hhshcc_sim.config import SimulatorConfig

    return SimulatorConfig(
        meps_years=[2022],
        benefit_year=2025,
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "output",
        random_seed=42,
    )
