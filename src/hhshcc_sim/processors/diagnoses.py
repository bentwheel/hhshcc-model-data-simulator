"""Process MEPS Medical Conditions into DIAG file records."""

import logging
from datetime import date

import numpy as np
import pandas as pd

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.processors.icd10_expansion import (
    expand_icd10_code,
    expand_icd10_codes_mode,
)
from hhshcc_sim.utils.date_helpers import calculate_age, dob_int_to_date, simulate_service_date

logger = logging.getLogger(__name__)


def _determine_setting(row: pd.Series) -> str:
    """Determine the healthcare setting for a condition record.

    Uses MEPS condition-level indicators: ERCOND, IPCOND, OPCOND.
    Values: 1=yes, 2=no, -1=inapplicable.
    Priority: ER > IP > OP > total (fallback).
    """
    if row.get("ERCOND", 2) == 1:
        return "ed"
    if row.get("IPCOND", 2) == 1:
        return "ip"
    if row.get("OPCOND", 2) == 1 or row.get("OBCOND", 2) == 1:
        return "op"
    return "total"


def process_diagnoses(
    cond_df: pd.DataFrame,
    prob_tables: dict[str, pd.DataFrame],
    demographics_df: pd.DataFrame,
    config: SimulatorConfig,
) -> pd.DataFrame:
    """Process medical conditions and expand ICD-10 codes.

    Args:
        cond_df: MEPS Medical Conditions DataFrame (from COND .dta file).
        prob_tables: ICD-10 expansion probability tables.
        demographics_df: Output from process_demographics (for person filtering and DOB).
        config: Simulator configuration.

    Returns DIAG DataFrame with columns:
        ENROLID, DIAG, DIAGNOSIS_SERVICE_DATE, AGE_AT_DIAGNOSIS
    """
    rng = np.random.default_rng(config.random_seed + 1)  # Offset seed from enrollment
    year = config.meps_year

    # Normalize column names
    df = cond_df.copy()
    df.columns = df.columns.str.upper()

    # Ensure DUPERSID is string
    df["DUPERSID"] = df["DUPERSID"].astype(str)

    # Get the ICD-10 column (may be ICD10CDX or CCCODEX depending on year)
    icd10_col = None
    for candidate in ["ICD10CDX", "CCCODEX"]:
        if candidate in df.columns:
            icd10_col = candidate
            break

    if icd10_col is None:
        raise ValueError(
            f"Cannot find ICD-10 code column in conditions file. "
            f"Available columns: {list(df.columns)}"
        )

    # Filter to valid ICD-10 codes (exclude negative/missing values)
    df[icd10_col] = df[icd10_col].astype(str).str.strip()
    df = df[df[icd10_col].str.match(r"^[A-Z]\d{2}$", na=False)].copy()
    logger.info(f"Valid ICD-10 condition records: {len(df):,}")

    # Filter to persons in target population
    valid_enrolids = set(demographics_df["ENROLID"].astype(str))
    df = df[df["DUPERSID"].isin(valid_enrolids)].copy()
    logger.info(f"After population filter: {len(df):,} condition records for {df['DUPERSID'].nunique():,} persons")

    # Build person-level lookup for DOB and enrolled months
    person_info = demographics_df.set_index("ENROLID")[
        ["DOB", "ENROLLED_MONTHS"]
    ].to_dict("index")

    if config.dx_mode == "mode":
        return _process_mode(df, icd10_col, prob_tables, person_info, rng, config)
    else:
        return _process_single(df, icd10_col, prob_tables, person_info, rng, config)


def _process_single(
    df: pd.DataFrame,
    icd10_col: str,
    prob_tables: dict[str, pd.DataFrame],
    person_info: dict,
    rng: np.random.Generator,
    config: SimulatorConfig,
) -> pd.DataFrame:
    """Single-draw expansion: one full code per condition record."""
    year = config.meps_year
    records = []

    for i, (_, row) in enumerate(df.iterrows()):
        person_id = row["DUPERSID"]
        icd10cdx = row[icd10_col]
        setting = _determine_setting(row)

        # Expand 3-char code to full code
        full_code = expand_icd10_code(icd10cdx, setting, prob_tables, rng)

        # Simulate service date
        info = person_info.get(person_id, {})
        enrolled_months = info.get("ENROLLED_MONTHS", [6])
        svc_date = simulate_service_date(year, enrolled_months, person_id, i, config.random_seed)

        # Calculate age at diagnosis
        dob_int = info.get("DOB", year * 10000 + 101)
        dob = dob_int_to_date(dob_int)
        age_at_dx = calculate_age(dob, svc_date)

        records.append({
            "ENROLID": person_id,
            "DIAG": full_code,
            "DIAGNOSIS_SERVICE_DATE": svc_date.year * 10000 + svc_date.month * 100 + svc_date.day,
            "AGE_AT_DIAGNOSIS": age_at_dx,
        })

    result = pd.DataFrame(records)
    logger.info(f"DIAG records (single mode): {len(result):,}")
    return result


def _process_mode(
    df: pd.DataFrame,
    icd10_col: str,
    prob_tables: dict[str, pd.DataFrame],
    person_info: dict,
    rng: np.random.Generator,
    config: SimulatorConfig,
) -> pd.DataFrame:
    """Mode-based expansion: generate N profiles per person, pick the most common."""
    year = config.meps_year
    records = []

    for person_id, person_conds in df.groupby("DUPERSID"):
        icd10cdx_list = person_conds[icd10_col].tolist()
        settings = [_determine_setting(row) for _, row in person_conds.iterrows()]

        # Generate mode profile
        expanded = expand_icd10_codes_mode(
            icd10cdx_list, settings, prob_tables, rng, config.n_simulations
        )

        # Build records for this person
        info = person_info.get(person_id, {})
        enrolled_months = info.get("ENROLLED_MONTHS", [6])
        dob_int = info.get("DOB", year * 10000 + 101)
        dob = dob_int_to_date(dob_int)

        for i, full_code in enumerate(expanded):
            svc_date = simulate_service_date(
                year, enrolled_months, person_id, i, config.random_seed
            )
            age_at_dx = calculate_age(dob, svc_date)

            records.append({
                "ENROLID": person_id,
                "DIAG": full_code,
                "DIAGNOSIS_SERVICE_DATE": (
                    svc_date.year * 10000 + svc_date.month * 100 + svc_date.day
                ),
                "AGE_AT_DIAGNOSIS": age_at_dx,
            })

    result = pd.DataFrame(records)
    logger.info(f"DIAG records (mode, n={config.n_simulations}): {len(result):,}")
    return result
