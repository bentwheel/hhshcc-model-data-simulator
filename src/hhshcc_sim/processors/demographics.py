"""Process MEPS FYC data into PERSON-level demographic fields."""

import logging

import pandas as pd

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.data.meps_registry import MEPS_MONTH_ABBREVS, MEPS_YEAR_SUFFIX
from hhshcc_sim.utils.date_helpers import calculate_age, make_dob, simulate_birth_day

logger = logging.getLogger(__name__)


def _get_private_coverage_months(row: pd.Series, year_suffix: str) -> list[int]:
    """Determine which months (1-12) a person had private insurance coverage.

    MEPS FYC encodes monthly private insurance as PRIJAyy, PRIFEyy, ..., PRIDEyy
    where values: 1=covered, 2=not covered.
    """
    months = []
    for i, abbrev in enumerate(MEPS_MONTH_ABBREVS, start=1):
        col = f"PRI{abbrev}{year_suffix}"
        val = row.get(col, 2)
        if val == 1:
            months.append(i)
    return months


def process_demographics(fyc_df: pd.DataFrame, config: SimulatorConfig) -> pd.DataFrame:
    """Extract and filter demographics from the MEPS FYC file.

    Filters to:
    - Ages config.age_min through config.age_max
    - At least 1 month of private insurance coverage

    Returns a DataFrame with columns:
        ENROLID, SEX, DOB, DOBYY, DOBMM, DOBDD, AGE_LAST, POVLEV, ENROLLED_MONTHS
    """
    yy = config.meps_year_suffix
    year = config.meps_year

    # Ensure key columns exist
    required = ["DUPERSID", "SEX", "DOBMM", "DOBYY"]
    missing = [c for c in required if c not in fyc_df.columns]
    if missing:
        raise ValueError(f"FYC file missing required columns: {missing}")

    df = fyc_df.copy()

    # Filter out invalid DOB values (MEPS codes -1 for inapplicable)
    df = df[df["DOBMM"].gt(0) & df["DOBYY"].gt(0)].copy()

    # Calculate enrolled months (private insurance)
    df["ENROLLED_MONTHS"] = df.apply(
        lambda row: _get_private_coverage_months(row, yy), axis=1
    )
    df["N_ENROLLED_MONTHS"] = df["ENROLLED_MONTHS"].apply(len)

    # Filter: at least 1 month private coverage
    df = df[df["N_ENROLLED_MONTHS"] > 0].copy()
    logger.info(f"After private coverage filter: {len(df):,} persons")

    # Simulate birth day and build full DOB
    df["DUPERSID"] = df["DUPERSID"].astype(str)
    df["DOBMM"] = df["DOBMM"].astype(int)
    df["DOBYY"] = df["DOBYY"].astype(int)

    df["DOBDD"] = df.apply(
        lambda row: simulate_birth_day(
            row["DOBMM"], row["DOBYY"], row["DUPERSID"], config.random_seed
        ),
        axis=1,
    )
    df["DOB"] = df.apply(
        lambda row: make_dob(row["DOBYY"], row["DOBMM"], row["DOBDD"]), axis=1
    )

    # Calculate AGE_LAST (age as of Dec 31 of benefit year)
    from datetime import date

    end_of_year = date(year, 12, 31)
    df["AGE_LAST"] = df.apply(
        lambda row: calculate_age(
            date(row["DOBYY"], row["DOBMM"], row["DOBDD"]), end_of_year
        ),
        axis=1,
    )

    # Filter by age range
    df = df[(df["AGE_LAST"] >= config.age_min) & (df["AGE_LAST"] <= config.age_max)].copy()
    logger.info(f"After age filter ({config.age_min}-{config.age_max}): {len(df):,} persons")

    # Extract poverty level for income-informed metal/CSR simulation
    povlev_col = f"POVLEV{yy}"
    if povlev_col in df.columns:
        df["POVLEV"] = df[povlev_col]
    elif "POVLEV" in df.columns:
        pass  # Already named without suffix
    else:
        logger.warning(f"Poverty level column {povlev_col} not found; defaulting to 400")
        df["POVLEV"] = 400.0

    # Build ENROLID from DUPERSID
    df["ENROLID"] = df["DUPERSID"]

    # Select output columns
    result = df[
        ["ENROLID", "SEX", "DOB", "DOBYY", "DOBMM", "DOBDD", "AGE_LAST", "POVLEV",
         "ENROLLED_MONTHS", "N_ENROLLED_MONTHS"]
    ].copy()

    # Ensure SEX is integer
    result["SEX"] = result["SEX"].astype(int)

    logger.info(f"Demographics processed: {len(result):,} persons")
    return result.reset_index(drop=True)
