"""Process MEPS Prescribed Medicines into NDC file records."""

import logging

import pandas as pd

from hhshcc_sim.config import SimulatorConfig

logger = logging.getLogger(__name__)


def clean_ndc(ndc_value) -> str | None:
    """Clean and validate an NDC code.

    Returns an 11-digit string, or None if invalid/missing.
    """
    if pd.isna(ndc_value):
        return None

    ndc_str = str(ndc_value).strip()

    # MEPS codes negative values for missing data
    if ndc_str.startswith("-"):
        return None

    # Remove dashes and spaces
    ndc_str = ndc_str.replace("-", "").replace(" ", "")

    # Remove any decimal point (some Stata numeric conversions add .0)
    if "." in ndc_str:
        ndc_str = ndc_str.split(".")[0]

    # Must be numeric
    if not ndc_str.isdigit():
        return None

    # Zero-pad to 11 digits
    ndc_str = ndc_str.zfill(11)

    # Reject all-zeros
    if ndc_str == "0" * 11:
        return None

    return ndc_str


def process_prescriptions(
    pmed_df: pd.DataFrame,
    demographics_df: pd.DataFrame,
    config: SimulatorConfig,
) -> pd.DataFrame:
    """Extract and clean NDC codes from MEPS Prescribed Medicines file.

    Args:
        pmed_df: MEPS Prescribed Medicines DataFrame.
        demographics_df: Output from process_demographics (for person filtering).
        config: Simulator configuration.

    Returns NDC DataFrame with columns: ENROLID, NDC
    """
    df = pmed_df.copy()
    df.columns = df.columns.str.upper()

    # Ensure DUPERSID is string
    df["DUPERSID"] = df["DUPERSID"].astype(str)

    # Find NDC column
    ndc_col = None
    for candidate in ["RXNDC", "NDC"]:
        if candidate in df.columns:
            ndc_col = candidate
            break

    if ndc_col is None:
        raise ValueError(
            f"Cannot find NDC column in PMED file. Available columns: {list(df.columns)}"
        )

    # Filter to target population
    valid_enrolids = set(demographics_df["ENROLID"].astype(str))
    df = df[df["DUPERSID"].isin(valid_enrolids)].copy()
    logger.info(f"Prescription records for target population: {len(df):,}")

    # Clean NDC codes
    df["NDC_CLEAN"] = df[ndc_col].apply(clean_ndc)
    df = df[df["NDC_CLEAN"].notna()].copy()
    logger.info(f"After NDC cleaning: {len(df):,} valid records")

    # Build output: deduplicate (ENROLID, NDC) pairs
    result = (
        df[["DUPERSID", "NDC_CLEAN"]]
        .rename(columns={"DUPERSID": "ENROLID", "NDC_CLEAN": "NDC"})
        .drop_duplicates()
        .reset_index(drop=True)
    )

    logger.info(f"NDC records (deduplicated): {len(result):,} for {result['ENROLID'].nunique():,} persons")
    return result
