"""Process NDC codes through RXC crosswalk to generate HCPCS records."""

import logging

import numpy as np
import pandas as pd

from hhshcc_sim.config import SimulatorConfig

logger = logging.getLogger(__name__)


def build_rxc_crosswalk(
    ndc_to_rxc_df: pd.DataFrame,
    hcpcs_to_rxc_df: pd.DataFrame,
) -> tuple[dict[str, int], dict[int, list[str]]]:
    """Build lookup tables from parsed Table 10a and 10b.

    Returns:
        ndc_rxc_map: dict mapping NDC (11-digit str) -> RXC (int)
        rxc_hcpcs_map: dict mapping RXC (int) -> list of HCPCS codes
    """
    ndc_rxc_map = dict(zip(ndc_to_rxc_df["NDC"], ndc_to_rxc_df["RXC"].astype(int)))

    rxc_hcpcs_map: dict[int, list[str]] = {}
    for _, row in hcpcs_to_rxc_df.iterrows():
        rxc = int(row["RXC"])
        hcpcs = row["HCPCS"]
        rxc_hcpcs_map.setdefault(rxc, []).append(hcpcs)

    return ndc_rxc_map, rxc_hcpcs_map


def process_hcpcs(
    ndc_df: pd.DataFrame,
    ndc_rxc_map: dict[str, int],
    rxc_hcpcs_map: dict[int, list[str]],
    config: SimulatorConfig,
) -> pd.DataFrame:
    """Generate HCPCS records by crossing NDC codes through the RXC crosswalk.

    For each person who has an NDC that maps to an RXC (via Table 10a), and
    that RXC has corresponding HCPCS codes (via Table 10b), one HCPCS code is
    selected randomly from the available codes for that RXC.

    This simulates the scenario where a drug identified by NDC could also be
    identified via a HCPCS procedure code (e.g., J-codes for drugs administered
    in clinical settings).

    Args:
        ndc_df: NDC DataFrame with columns ENROLID, NDC.
        ndc_rxc_map: NDC -> RXC lookup from Table 10a.
        rxc_hcpcs_map: RXC -> [HCPCS] lookup from Table 10b.
        config: Simulator configuration.

    Returns:
        HCPCS DataFrame with columns: ENROLID, HCPCS
    """
    rng = np.random.default_rng(config.random_seed + 3)  # Offset seed from other processors

    if len(ndc_df) == 0:
        logger.info("No NDC records; HCPCS output will be empty")
        return pd.DataFrame(columns=["ENROLID", "HCPCS"])

    # Map each NDC to its RXC
    ndc_df = ndc_df.copy()
    ndc_df["RXC"] = ndc_df["NDC"].map(ndc_rxc_map)

    # Keep only rows where the NDC mapped to an RXC
    matched = ndc_df.dropna(subset=["RXC"]).copy()
    matched["RXC"] = matched["RXC"].astype(int)

    logger.info(
        f"NDC->RXC matches: {len(matched):,} of {len(ndc_df):,} NDC records "
        f"({matched['ENROLID'].nunique():,} persons)"
    )

    if len(matched) == 0:
        logger.info("No NDC->RXC matches found; HCPCS output will be empty")
        return pd.DataFrame(columns=["ENROLID", "HCPCS"])

    # For each matched (ENROLID, RXC), pick a HCPCS code from that RXC
    records = []
    for _, row in matched.iterrows():
        rxc = row["RXC"]
        hcpcs_codes = rxc_hcpcs_map.get(rxc)
        if not hcpcs_codes:
            continue
        chosen = rng.choice(hcpcs_codes)
        records.append({"ENROLID": row["ENROLID"], "HCPCS": chosen})

    if not records:
        logger.info("No RXC->HCPCS matches found; HCPCS output will be empty")
        return pd.DataFrame(columns=["ENROLID", "HCPCS"])

    result = pd.DataFrame(records).drop_duplicates().reset_index(drop=True)
    logger.info(
        f"HCPCS records (deduplicated): {len(result):,} for "
        f"{result['ENROLID'].nunique():,} persons"
    )
    return result
