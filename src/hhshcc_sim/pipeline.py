"""End-to-end pipeline orchestrator."""

import logging
import time

import pandas as pd

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.data.ca_icd10_download import download_ca_icd10_files
from hhshcc_sim.data.cms_diy_download import (
    download_cms_diy_tables,
    parse_hcpcs_to_rxc,
    parse_ndc_to_rxc,
)
from hhshcc_sim.data.meps_download import download_all_meps_files
from hhshcc_sim.output.validators import validate_all_outputs
from hhshcc_sim.output.writers import write_all_output_files
from hhshcc_sim.processors.demographics import process_demographics
from hhshcc_sim.processors.diagnoses import process_diagnoses
from hhshcc_sim.processors.enrollment import process_enrollment
from hhshcc_sim.processors.hcpcs import build_rxc_crosswalk, process_hcpcs
from hhshcc_sim.processors.icd10_expansion import (
    build_expansion_probabilities,
    load_ca_icd10_frequencies,
)
from hhshcc_sim.processors.prescriptions import process_prescriptions
from hhshcc_sim.utils.io import read_stata

logger = logging.getLogger(__name__)


def _prefix_enrolids(df: pd.DataFrame, meps_year: int, col: str = "ENROLID") -> pd.DataFrame:
    """Prefix ENROLID values with the MEPS year to ensure uniqueness across years."""
    df = df.copy()
    df[col] = f"{meps_year}_" + df[col].astype(str)
    return df


def run_pipeline(config: SimulatorConfig) -> None:
    """Execute the full simulation pipeline.

    When multiple MEPS years are specified, data from each year is processed
    independently and then concatenated. ENROLIDs are prefixed with the MEPS
    year (e.g., '2022_10001') to prevent collisions across years.

    Diagnosis service dates and AGE_LAST are calculated relative to the
    benefit year, not the MEPS data year.
    """
    start = time.time()
    years_str = ", ".join(str(y) for y in config.meps_years)
    logger.info(f"Starting HHS-HCC simulation")
    logger.info(f"  MEPS year(s): {years_str}")
    logger.info(f"  Benefit year: {config.benefit_year}")
    logger.info(f"  Output dir: {config.output_dir}")
    logger.info(f"  Random seed: {config.random_seed}")
    logger.info(f"  DX mode: {config.dx_mode}")
    logger.info(f"  Age range: {config.age_min}-{config.age_max} (as of {config.benefit_year})")

    # Stage 1: Download all data
    logger.info("=" * 60)
    logger.info("Stage 1: Downloading data")
    all_meps_paths = download_all_meps_files(config)
    ca_paths = download_ca_icd10_files(config)
    cms_tables_path = download_cms_diy_tables(config)

    # Stage 2: Build ICD-10 expansion tables (shared across all MEPS years)
    logger.info("=" * 60)
    logger.info("Stage 2: Building ICD-10 expansion tables")
    ca_freq_df = load_ca_icd10_frequencies(
        ca_paths["ed"], ca_paths["ip"], ca_paths["op"]
    )
    prob_tables = build_expansion_probabilities(ca_freq_df)

    # Build RXC crosswalk tables for HCPCS generation
    logger.info("Building RXC crosswalk tables (Table 10a/10b)")
    ndc_to_rxc_df = parse_ndc_to_rxc(cms_tables_path)
    hcpcs_to_rxc_df = parse_hcpcs_to_rxc(cms_tables_path)
    ndc_rxc_map, rxc_hcpcs_map = build_rxc_crosswalk(ndc_to_rxc_df, hcpcs_to_rxc_df)

    # Stage 3-6: Process each MEPS year independently, then concatenate
    all_demographics = []
    all_enrollment = []
    all_diag = []
    all_ndc = []

    for meps_year in config.meps_years:
        logger.info("=" * 60)
        logger.info(f"Processing MEPS year {meps_year}")
        year_paths = all_meps_paths[meps_year]

        # Read raw files for this year
        logger.info(f"  Reading raw data files for {meps_year}")
        fyc_df = read_stata(year_paths["fyc"])
        cond_df = read_stata(year_paths["cond"])
        pmed_df = read_stata(year_paths["pmed"])

        # Process demographics (AGE_LAST is based on benefit_year)
        logger.info(f"  Processing demographics for {meps_year}")
        demo_df = process_demographics(fyc_df, meps_year, config)

        if len(demo_df) == 0:
            logger.warning(f"  No eligible persons found in MEPS {meps_year}, skipping")
            continue

        # Process enrollment
        logger.info(f"  Processing enrollment for {meps_year}")
        enroll_df = process_enrollment(demo_df, config)

        # Process diagnoses (service dates placed in benefit_year)
        logger.info(f"  Processing diagnoses for {meps_year}")
        diag_df = process_diagnoses(cond_df, prob_tables, demo_df, config)

        # Process prescriptions
        logger.info(f"  Processing prescriptions for {meps_year}")
        ndc_df = process_prescriptions(pmed_df, demo_df, config)

        # Prefix ENROLIDs with MEPS year for cross-year uniqueness
        # (only needed when combining multiple years, but always applied for consistency)
        demo_df = _prefix_enrolids(demo_df, meps_year)
        enroll_df = _prefix_enrolids(enroll_df, meps_year)
        if len(diag_df) > 0:
            diag_df = _prefix_enrolids(diag_df, meps_year)
        if len(ndc_df) > 0:
            ndc_df = _prefix_enrolids(ndc_df, meps_year)

        all_demographics.append(demo_df)
        all_enrollment.append(enroll_df)
        all_diag.append(diag_df)
        all_ndc.append(ndc_df)

    if not all_demographics:
        logger.error("No eligible persons found across any MEPS year. Aborting.")
        return

    # Concatenate across years
    demographics_df = pd.concat(all_demographics, ignore_index=True)
    enrollment_df = pd.concat(all_enrollment, ignore_index=True)
    diag_df = pd.concat(all_diag, ignore_index=True) if all_diag else pd.DataFrame(
        columns=["ENROLID", "DIAG", "DIAGNOSIS_SERVICE_DATE", "AGE_AT_DIAGNOSIS"]
    )
    ndc_df = pd.concat(all_ndc, ignore_index=True) if all_ndc else pd.DataFrame(
        columns=["ENROLID", "NDC"]
    )

    # Generate HCPCS records from NDC->RXC->HCPCS crosswalk
    logger.info("=" * 60)
    logger.info("Processing HCPCS via RXC crosswalk")
    hcpcs_df = process_hcpcs(ndc_df, ndc_rxc_map, rxc_hcpcs_map, config)

    logger.info("=" * 60)
    logger.info(
        f"Combined totals: {len(demographics_df):,} persons, "
        f"{len(diag_df):,} diagnoses, {len(ndc_df):,} NDCs, "
        f"{len(hcpcs_df):,} HCPCS"
    )

    # Stage 7: Write output files
    logger.info("=" * 60)
    logger.info("Stage 7: Writing output files")
    output_paths = write_all_output_files(
        demographics_df, enrollment_df, diag_df, ndc_df, hcpcs_df, config.output_dir
    )

    # Stage 8: Validate
    logger.info("=" * 60)
    logger.info("Stage 8: Validating output files")
    errors = validate_all_outputs(config.output_dir)

    elapsed = time.time() - start
    logger.info("=" * 60)
    if errors:
        logger.warning(f"Pipeline completed with {len(errors)} validation errors in {elapsed:.1f}s")
        for err in errors:
            logger.warning(f"  - {err}")
    else:
        logger.info(f"Pipeline completed successfully in {elapsed:.1f}s")

    logger.info("Output files:")
    for name, path in output_paths.items():
        logger.info(f"  {name}: {path}")
