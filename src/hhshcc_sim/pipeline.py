"""End-to-end pipeline orchestrator."""

import logging
import time

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.data.ca_icd10_download import download_ca_icd10_files
from hhshcc_sim.data.meps_download import download_meps_files
from hhshcc_sim.output.validators import validate_all_outputs
from hhshcc_sim.output.writers import write_all_output_files
from hhshcc_sim.processors.demographics import process_demographics
from hhshcc_sim.processors.diagnoses import process_diagnoses
from hhshcc_sim.processors.enrollment import process_enrollment
from hhshcc_sim.processors.icd10_expansion import (
    build_expansion_probabilities,
    load_ca_icd10_frequencies,
)
from hhshcc_sim.processors.prescriptions import process_prescriptions
from hhshcc_sim.utils.io import read_stata

logger = logging.getLogger(__name__)


def run_pipeline(config: SimulatorConfig) -> None:
    """Execute the full simulation pipeline."""
    start = time.time()
    logger.info(f"Starting HHS-HCC simulation for MEPS year {config.meps_year}")
    logger.info(f"  Output dir: {config.output_dir}")
    logger.info(f"  Random seed: {config.random_seed}")
    logger.info(f"  DX mode: {config.dx_mode}")
    logger.info(f"  Age range: {config.age_min}-{config.age_max}")

    # Stage 1: Download data
    logger.info("=" * 60)
    logger.info("Stage 1: Downloading data")
    meps_paths = download_meps_files(config)
    ca_paths = download_ca_icd10_files(config)

    # Stage 2: Read raw files
    logger.info("=" * 60)
    logger.info("Stage 2: Reading raw data files")
    fyc_df = read_stata(meps_paths["fyc"])
    cond_df = read_stata(meps_paths["cond"])
    pmed_df = read_stata(meps_paths["pmed"])

    # Stage 3: Process demographics
    logger.info("=" * 60)
    logger.info("Stage 3: Processing demographics")
    demographics_df = process_demographics(fyc_df, config)

    # Stage 4: Process enrollment
    logger.info("=" * 60)
    logger.info("Stage 4: Processing enrollment")
    enrollment_df = process_enrollment(demographics_df, config)

    # Stage 5: Build ICD-10 expansion tables and process diagnoses
    logger.info("=" * 60)
    logger.info("Stage 5: Processing diagnoses (ICD-10 expansion)")
    ca_freq_df = load_ca_icd10_frequencies(
        ca_paths["ed"], ca_paths["ip"], ca_paths["op"]
    )
    prob_tables = build_expansion_probabilities(ca_freq_df)
    diag_df = process_diagnoses(cond_df, prob_tables, demographics_df, config)

    # Stage 6: Process prescriptions
    logger.info("=" * 60)
    logger.info("Stage 6: Processing prescriptions")
    ndc_df = process_prescriptions(pmed_df, demographics_df, config)

    # Stage 7: Write output files
    logger.info("=" * 60)
    logger.info("Stage 7: Writing output files")
    output_paths = write_all_output_files(
        demographics_df, enrollment_df, diag_df, ndc_df, config.output_dir
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
