"""Download and parse CMS HHS-HCC DIY Tables Excel file."""

import logging
import warnings
from pathlib import Path

import pandas as pd

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.data.meps_download import download_file

logger = logging.getLogger(__name__)

# Maps benefit year -> CMS DIY Tables XLSX download URL.
# These files contain Table 10a (NDC->RXC) and Table 10b (HCPCS->RXC) crosswalks.
CMS_DIY_TABLES_URLS: dict[int, str] = {
    2025: "https://www.cms.gov/files/document/cy2025-diy-tables-01-23-2026.xlsx",
}

# Fallback: use the most recent available tables for unsupported benefit years.
# The RXC crosswalk is cumulative and largely stable across years.
_DEFAULT_TABLES_YEAR = 2025


def _get_tables_url(benefit_year: int) -> tuple[int, str]:
    """Get the best available DIY tables URL for a benefit year.

    Returns (actual_year, url) tuple.
    """
    if benefit_year in CMS_DIY_TABLES_URLS:
        return benefit_year, CMS_DIY_TABLES_URLS[benefit_year]

    logger.warning(
        f"No CMS DIY tables URL for benefit year {benefit_year}; "
        f"using CY{_DEFAULT_TABLES_YEAR} tables as fallback"
    )
    return _DEFAULT_TABLES_YEAR, CMS_DIY_TABLES_URLS[_DEFAULT_TABLES_YEAR]


def download_cms_diy_tables(config: SimulatorConfig) -> Path:
    """Download the CMS DIY Tables XLSX file.

    Returns path to the downloaded Excel file.
    """
    tables_year, url = _get_tables_url(config.benefit_year)
    raw_dir = config.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    filename = f"cms_diy_tables_cy{tables_year}.xlsx"
    dest = raw_dir / filename

    if config.skip_download and dest.exists():
        logger.info(f"Already cached: {dest}")
        return dest

    if dest.exists():
        logger.info(f"Already cached: {dest}")
        return dest

    logger.info(f"Downloading CMS CY{tables_year} DIY Tables")
    download_file(url, dest, description=f"CMS DIY Tables CY{tables_year}")
    return dest


def parse_ndc_to_rxc(tables_path: Path) -> pd.DataFrame:
    """Parse Table 10a (RXC to NDC Crosswalk) from the DIY Tables file.

    Returns DataFrame with columns: NDC (str, 11-digit), RXC (int), RXC_LABEL (str)
    """
    # The sheet has a title row, subtitle row, and blank row before the actual headers.
    # Suppress openpyxl warning about print areas referencing named ranges in this workbook.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Print area cannot be set", category=UserWarning)
        df = pd.read_excel(tables_path, sheet_name="Table 10a", header=3, dtype=str)

    # Normalize column names
    df.columns = df.columns.str.strip().str.upper()

    # Clean NDC: ensure 11-digit zero-padded string
    df["NDC"] = df["NDC"].astype(str).str.strip().str.replace("-", "").str.zfill(11)

    # Clean RXC: extract numeric value
    df["RXC"] = pd.to_numeric(df["RXC"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["RXC"])

    # Rename label column
    label_col = [c for c in df.columns if "LABEL" in c]
    if label_col:
        df = df.rename(columns={label_col[0]: "RXC_LABEL"})
    else:
        df["RXC_LABEL"] = ""

    result = df[["NDC", "RXC", "RXC_LABEL"]].copy()
    logger.info(f"Parsed Table 10a: {len(result):,} NDC->RXC mappings across {result['RXC'].nunique()} RXCs")
    return result


def parse_hcpcs_to_rxc(tables_path: Path) -> pd.DataFrame:
    """Parse Table 10b (RXC to HCPCS Crosswalk) from the DIY Tables file.

    Returns DataFrame with columns: HCPCS (str), RXC (int), RXC_LABEL (str)
    """
    # The sheet has a title row, subtitle row, and blank row before the actual headers.
    # Suppress openpyxl warning about print areas referencing named ranges in this workbook.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Print area cannot be set", category=UserWarning)
        df = pd.read_excel(tables_path, sheet_name="Table 10b", header=3, dtype=str)

    # Normalize column names
    df.columns = df.columns.str.strip().str.upper()

    # Clean HCPCS: strip whitespace
    df["HCPCS"] = df["HCPCS"].astype(str).str.strip()

    # Clean RXC: extract numeric value
    df["RXC"] = pd.to_numeric(df["RXC"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["RXC"])

    # Rename label column
    label_col = [c for c in df.columns if "LABEL" in c]
    if label_col:
        df = df.rename(columns={label_col[0]: "RXC_LABEL"})
    else:
        df["RXC_LABEL"] = ""

    result = df[["HCPCS", "RXC", "RXC_LABEL"]].copy()
    logger.info(f"Parsed Table 10b: {len(result):,} HCPCS->RXC mappings across {result['RXC'].nunique()} RXCs")
    return result
