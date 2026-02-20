"""File reading utilities for MEPS data."""

import logging
from pathlib import Path

import pandas as pd
import pyreadstat

logger = logging.getLogger(__name__)


def read_stata(path: Path) -> pd.DataFrame:
    """Read a Stata .dta file and return a DataFrame.

    Converts all column names to uppercase for consistency across MEPS years.
    """
    path = Path(path)
    logger.info(f"Reading Stata file: {path} ({path.stat().st_size / 1e6:.1f} MB)")
    df, meta = pyreadstat.read_dta(str(path))
    df.columns = df.columns.str.upper()
    logger.info(f"  Read {len(df):,} rows x {len(df.columns)} columns")
    return df
