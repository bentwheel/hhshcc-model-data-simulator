"""Process enrollment data: duration, metal level, and CSR indicator simulation."""

import logging

import numpy as np
import pandas as pd
from tqdm import tqdm

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.utils import tqdm_disabled

logger = logging.getLogger(__name__)

# Published ACA marketplace metal level distributions (approximate, from CMS MLMS data)
# These are base rates before income adjustment
_BASE_METAL_PROBS = {
    "silver": 0.73,
    "bronze": 0.19,
    "gold": 0.06,
    "platinum": 0.01,
    "catastrophic": 0.01,
}

# Income-based adjustments: lower-income individuals are more likely to choose silver
# (because CSR subsidies only apply to silver plans)
# FPL brackets and their silver probability boost
_INCOME_SILVER_BOOST = {
    # (min_fpl, max_fpl): silver_boost
    (0, 150): 0.20,      # Very low income -> strong silver preference for CSR
    (150, 200): 0.15,    # Low income -> moderate silver preference
    (200, 250): 0.10,    # Moderate income -> slight silver preference
    (250, 400): 0.00,    # Above CSR threshold -> no boost
    (400, float("inf")): -0.05,  # Higher income -> slightly less silver, more gold/platinum
}


def _get_metal_probs(age: int, poverty_level: float) -> dict[str, float]:
    """Get metal level probabilities adjusted for age and income.

    - Catastrophic plans are only available to individuals under 30.
    - Silver probability is boosted for lower-income individuals (CSR eligible).
    """
    probs = _BASE_METAL_PROBS.copy()

    # Catastrophic is only available under 30
    if age >= 30:
        # Redistribute catastrophic probability to bronze
        probs["bronze"] += probs["catastrophic"]
        probs["catastrophic"] = 0.0

    # Apply income-based silver boost
    silver_boost = 0.0
    for (min_fpl, max_fpl), boost in _INCOME_SILVER_BOOST.items():
        if min_fpl <= poverty_level < max_fpl:
            silver_boost = boost
            break

    if silver_boost != 0.0:
        probs["silver"] = max(0.01, probs["silver"] + silver_boost)
        # Redistribute the boost from/to other metals proportionally
        other_metals = [m for m in probs if m != "silver" and probs[m] > 0]
        adjustment = -silver_boost / len(other_metals) if other_metals else 0
        for metal in other_metals:
            probs[metal] = max(0.001, probs[metal] + adjustment)

    # Normalize to sum to 1.0
    total = sum(probs.values())
    return {k: v / total for k, v in probs.items()}


def simulate_metal_level(age: int, poverty_level: float, rng: np.random.Generator) -> str:
    """Simulate a plausible metal level based on age and income."""
    probs = _get_metal_probs(age, poverty_level)
    metals = list(probs.keys())
    probabilities = [probs[m] for m in metals]
    return rng.choice(metals, p=probabilities)


def simulate_csr_indicator(
    metal: str, poverty_level: float, rng: np.random.Generator
) -> int:
    """Simulate a CSR indicator based on metal level and income.

    CSR only applies to silver plan enrollees with income 100-250% FPL.
    Per CY2025 DIY spec CSR_INDICATOR values:
      1 = Non-CSR / standard
      3 = 87-94% AV Silver (100-200% FPL)
      1 = 73% AV Silver (200-250% FPL, minimal CSR benefit)
    """
    if metal != "silver":
        return 1

    if 100 <= poverty_level < 150:
        # 94% AV Silver - highest CSR
        return 3
    elif 150 <= poverty_level < 200:
        # 87% AV Silver
        return 3
    elif 200 <= poverty_level < 250:
        # 73% AV Silver - effectively standard
        return 1
    else:
        # Not CSR eligible (below 100% or above 250%)
        return 1


def process_enrollment(
    demographics_df: pd.DataFrame, config: SimulatorConfig
) -> pd.DataFrame:
    """Process enrollment data: compute duration, simulate metal and CSR.

    Args:
        demographics_df: Output from process_demographics, must include
            ENROLID, AGE_LAST, POVLEV, N_ENROLLED_MONTHS.
        config: Simulator configuration.

    Returns DataFrame with columns:
        ENROLID, ENROLDURATION, METAL, CSR_INDICATOR
    """
    rng = np.random.default_rng(config.random_seed)

    # Vectorize ENROLDURATION: clip to [1, 12]
    enrolduration = np.clip(demographics_df["N_ENROLLED_MONTHS"].values.astype(int), 1, 12)

    # Metal must remain per-row (probability distribution varies by age + income)
    ages = demographics_df["AGE_LAST"].astype(int).values
    povlevs = demographics_df["POVLEV"].fillna(400.0).astype(float).values
    metals = [
        simulate_metal_level(int(a), float(p), rng)
        for a, p in tqdm(
            zip(ages, povlevs),
            total=len(ages),
            desc="Enrollment",
            disable=tqdm_disabled(),
            leave=False,
        )
    ]

    # Vectorize CSR_INDICATOR: CSR=3 only for silver + income 100-200% FPL
    metals_arr = np.array(metals)
    csr = np.where(
        (metals_arr == "silver") & (povlevs >= 100) & (povlevs < 200),
        3, 1,
    )

    result = pd.DataFrame({
        "ENROLID": demographics_df["ENROLID"].values,
        "ENROLDURATION": enrolduration,
        "METAL": metals,
        "CSR_INDICATOR": csr,
    })

    logger.info(f"Enrollment processed: {len(result):,} persons")
    logger.info(f"  Metal distribution: {result['METAL'].value_counts().to_dict()}")
    logger.info(f"  CSR distribution: {result['CSR_INDICATOR'].value_counts().to_dict()}")
    return result
