"""Weighted resampling of the MEPS eligible population to a target sample size."""

import logging

import numpy as np
import pandas as pd

from hhshcc_sim.config import SimulatorConfig

logger = logging.getLogger(__name__)


def resample_population(
    demo_df: pd.DataFrame,
    fyc_df: pd.DataFrame,
    meps_year: int,
    config: SimulatorConfig,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Weighted resample of the eligible population to config.sample_size persons.

    Uses MEPS survey weights (PERWTyyF) from the FYC file to produce a
    representative sample via sampling with replacement. Each sampled person
    receives a ``_X`` suffix on their ENROLID (where X is the ith occurrence
    of that respondent in the sample).

    Args:
        demo_df: Demographics DataFrame (ENROLID = DUPERSID at this point).
        fyc_df: Raw FYC DataFrame containing survey weight columns.
        meps_year: MEPS data year (used to construct weight column name).
        config: Simulator configuration.

    Returns:
        Tuple of (resampled_demo_df, resample_map) where resample_map maps
        each new suffixed ENROLID to the original ENROLID.
    """
    yy = str(meps_year)[-2:]
    weight_col = f"PERWT{yy}F"

    # Extract weights from FYC for eligible persons
    fyc = fyc_df.copy()
    fyc["DUPERSID"] = fyc["DUPERSID"].astype(str)

    if weight_col in fyc.columns:
        weight_lookup = fyc.set_index("DUPERSID")[weight_col]
    else:
        # Try uppercase normalization
        fyc_upper = {c.upper(): c for c in fyc.columns}
        if weight_col.upper() in fyc_upper:
            weight_lookup = fyc.set_index("DUPERSID")[fyc_upper[weight_col.upper()]]
        else:
            logger.warning(
                f"Survey weight column {weight_col} not found in FYC file; "
                f"using equal weights"
            )
            weight_lookup = pd.Series(1.0, index=fyc["DUPERSID"])

    # Map weights onto the eligible population
    weights = demo_df["ENROLID"].map(weight_lookup).fillna(1.0).astype(float)

    # Ensure non-negative weights
    weights = weights.clip(lower=0.0)
    total = weights.sum()
    if total <= 0:
        logger.warning("All survey weights are zero; using equal weights")
        probs = np.ones(len(demo_df)) / len(demo_df)
    else:
        probs = weights.values / total

    # Deterministic weighted sampling with replacement
    rng = np.random.default_rng(config.random_seed + 100)
    indices = rng.choice(len(demo_df), size=config.sample_size, replace=True, p=probs)

    sampled = demo_df.iloc[indices].copy()

    # Assign _X suffixes (counter per original ENROLID)
    suffix_counts: dict[str, int] = {}
    new_enrolids = []
    resample_map: dict[str, str] = {}

    for enrolid in sampled["ENROLID"]:
        suffix_counts[enrolid] = suffix_counts.get(enrolid, 0) + 1
        new_id = f"{enrolid}_{suffix_counts[enrolid]}"
        new_enrolids.append(new_id)
        resample_map[new_id] = enrolid

    sampled["ENROLID"] = new_enrolids

    logger.info(
        f"  Resampled {len(demo_df):,} eligible persons -> "
        f"{config.sample_size:,} sample ({len(suffix_counts):,} unique respondents)"
    )

    return sampled.reset_index(drop=True), resample_map


def expand_for_resampled(
    df: pd.DataFrame,
    resample_map: dict[str, str],
    id_col: str = "ENROLID",
) -> pd.DataFrame:
    """Expand a DataFrame to match the resampled population.

    For each new ENROLID in resample_map, copies the rows belonging to the
    original ENROLID and renames them to the new suffixed ENROLID.

    Args:
        df: DataFrame with an ID column (e.g., enrollment, diagnoses, NDCs).
        resample_map: Mapping from new suffixed ENROLID to original ENROLID.
        id_col: Name of the ID column to match and rename.

    Returns:
        Expanded DataFrame with rows duplicated for each resampled copy.
    """
    if df.empty or not resample_map:
        return df

    # Group rows by original ENROLID for efficient lookup
    orig_ids = set(resample_map.values())
    grouped = {
        oid: group_df for oid, group_df in df[df[id_col].isin(orig_ids)].groupby(id_col)
    }

    pieces = []
    for new_id, orig_id in resample_map.items():
        rows = grouped.get(orig_id)
        if rows is not None and len(rows) > 0:
            chunk = rows.copy()
            chunk[id_col] = new_id
            pieces.append(chunk)

    if not pieces:
        return df.iloc[:0].copy()

    return pd.concat(pieces, ignore_index=True)
