"""ICD-10 code expansion from 3-character truncated codes to full codes.

MEPS truncates all ICD-10-CM codes to 3 characters for confidentiality.
This module uses California CHHS diagnosis code frequency data to build
probability distributions for expanding truncated codes to their full
(up to 7 character) versions.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Sheet names vary across years in the CA CHHS XLSX files.
# These are the common patterns for the diagnosis frequency sheet.
_DIAG_SHEET_PATTERNS = [
    "Diagnosis",
    "DiagnosisCode",
    "Diagnosis Code",
    "DX",
    "Sheet1",
]

# Column name patterns for the ICD-10 code column
_CODE_COL_PATTERNS = [
    "ICDCMCode",
    "ICDCM_Code",
    "ICD-CM Code",
    "DiagnosisCode",
    "Diagnosis Code",
    "DXCode",
    "DX_Code",
    "ICD_10_CM_Code",
]

# Column name patterns for the frequency/count column
_FREQ_COL_PATTERNS = [
    "TotalDiag",
    "Total_Diag",
    "TotalDiagnoses",
    "Total Diagnoses",
    "Total",
    "Frequency",
    "Count",
    "TotalFreq",
]


def _find_column(df: pd.DataFrame, patterns: list[str]) -> str | None:
    """Find a column matching one of the given patterns (case-insensitive)."""
    cols_lower = {c.lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    for pattern in patterns:
        key = pattern.lower().replace(" ", "").replace("_", "")
        if key in cols_lower:
            return cols_lower[key]
    return None


def _find_diag_sheet(xlsx_path: Path) -> str:
    """Find the diagnosis frequency sheet name in an XLSX file."""
    xl = pd.ExcelFile(xlsx_path)
    sheet_names = xl.sheet_names

    # Try exact and partial matches
    for pattern in _DIAG_SHEET_PATTERNS:
        for sheet in sheet_names:
            if pattern.lower() in sheet.lower():
                return sheet

    # Fallback: use first sheet
    logger.warning(
        f"Could not identify diagnosis sheet in {xlsx_path.name}. "
        f"Available sheets: {sheet_names}. Using first sheet."
    )
    return sheet_names[0]


def _read_ca_frequency_file(xlsx_path: Path) -> pd.DataFrame:
    """Read a single CA CHHS frequency XLSX file and normalize columns.

    Returns DataFrame with columns: ICD10CM, FREQ
    """
    sheet = _find_diag_sheet(xlsx_path)
    df = pd.read_excel(xlsx_path, sheet_name=sheet, engine="openpyxl")

    # Find the code column
    code_col = _find_column(df, _CODE_COL_PATTERNS)
    if code_col is None:
        raise ValueError(
            f"Cannot find ICD-10 code column in {xlsx_path.name}. "
            f"Available columns: {list(df.columns)}"
        )

    # Find the frequency column
    freq_col = _find_column(df, _FREQ_COL_PATTERNS)
    if freq_col is None:
        raise ValueError(
            f"Cannot find frequency column in {xlsx_path.name}. "
            f"Available columns: {list(df.columns)}"
        )

    result = pd.DataFrame({
        "ICD10CM": df[code_col].astype(str).str.strip().str.replace(".", "", regex=False),
        "FREQ": pd.to_numeric(df[freq_col], errors="coerce").fillna(0).astype(int),
    })

    # Remove empty/invalid codes
    result = result[result["ICD10CM"].str.len() >= 3].copy()
    result = result[result["FREQ"] > 0].copy()

    return result


def load_ca_icd10_frequencies(
    ed_path: Path, ip_path: Path, op_path: Path
) -> pd.DataFrame:
    """Parse and merge the three CA frequency XLSX files.

    Returns DataFrame with columns:
        ICD10CDX (3-char prefix), ICD10CM (full code),
        ED_FREQ, IP_FREQ, OP_FREQ, TOTAL_FREQ
    """
    logger.info("Loading CA ICD-10 frequency data...")

    ed_df = _read_ca_frequency_file(ed_path).rename(columns={"FREQ": "ED_FREQ"})
    ip_df = _read_ca_frequency_file(ip_path).rename(columns={"FREQ": "IP_FREQ"})
    op_df = _read_ca_frequency_file(op_path).rename(columns={"FREQ": "OP_FREQ"})

    logger.info(f"  ED: {len(ed_df):,} codes, IP: {len(ip_df):,} codes, OP: {len(op_df):,} codes")

    # Merge on full ICD10CM code
    merged = ed_df.merge(ip_df, on="ICD10CM", how="outer")
    merged = merged.merge(op_df, on="ICD10CM", how="outer")

    # Fill missing frequencies with 0
    for col in ["ED_FREQ", "IP_FREQ", "OP_FREQ"]:
        merged[col] = merged[col].fillna(0).astype(int)

    merged["TOTAL_FREQ"] = merged["ED_FREQ"] + merged["IP_FREQ"] + merged["OP_FREQ"]

    # Extract 3-char prefix
    merged["ICD10CDX"] = merged["ICD10CM"].str[:3]

    # Remove codes with zero total frequency
    merged = merged[merged["TOTAL_FREQ"] > 0].copy()

    logger.info(f"  Merged: {len(merged):,} unique full codes across {merged['ICD10CDX'].nunique():,} 3-char prefixes")

    return merged


def build_expansion_probabilities(
    freq_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """For each 3-char prefix, build a probability table of full codes.

    Returns dict mapping ICD10CDX -> DataFrame with columns:
        ICD10CM, ED_PROB, IP_PROB, OP_PROB, TOTAL_PROB
    """
    prob_tables: dict[str, pd.DataFrame] = {}

    for prefix, group in freq_df.groupby("ICD10CDX"):
        table = group[["ICD10CM", "ED_FREQ", "IP_FREQ", "OP_FREQ", "TOTAL_FREQ"]].copy()

        # Convert frequencies to probabilities within this prefix group
        for freq_col, prob_col in [
            ("ED_FREQ", "ED_PROB"),
            ("IP_FREQ", "IP_PROB"),
            ("OP_FREQ", "OP_PROB"),
            ("TOTAL_FREQ", "TOTAL_PROB"),
        ]:
            total = table[freq_col].sum()
            if total > 0:
                table[prob_col] = table[freq_col] / total
            else:
                # Uniform fallback if no data for this setting
                table[prob_col] = 1.0 / len(table)

        prob_tables[prefix] = table[
            ["ICD10CM", "ED_PROB", "IP_PROB", "OP_PROB", "TOTAL_PROB"]
        ].reset_index(drop=True)

    return prob_tables


def expand_icd10_code(
    icd10cdx: str,
    setting: str,
    prob_tables: dict[str, pd.DataFrame],
    rng: np.random.Generator,
) -> str:
    """Draw a single full ICD-10-CM code from the frequency distribution.

    Args:
        icd10cdx: 3-character truncated ICD-10 code.
        setting: One of 'ed', 'ip', 'op', or 'total'.
        prob_tables: Output from build_expansion_probabilities.
        rng: NumPy random generator.

    Returns the expanded full ICD-10-CM code, or the original 3-char code
    if no expansion data is available.
    """
    if icd10cdx not in prob_tables:
        return icd10cdx

    table = prob_tables[icd10cdx]
    prob_col = f"{setting.upper()}_PROB"

    if prob_col not in table.columns:
        prob_col = "TOTAL_PROB"

    probs = table[prob_col].values
    # Ensure probabilities sum to 1 (handle floating point)
    probs = probs / probs.sum()

    idx = rng.choice(len(table), p=probs)
    return table.iloc[idx]["ICD10CM"]


def expand_icd10_codes_mode(
    icd10cdx_list: list[str],
    settings: list[str],
    prob_tables: dict[str, pd.DataFrame],
    rng: np.random.Generator,
    n_simulations: int = 500,
) -> list[str]:
    """Generate N diagnosis profiles and return the most common (mode) profile.

    Args:
        icd10cdx_list: List of 3-char truncated codes for one person.
        settings: Corresponding care settings for each code.
        prob_tables: Expansion probability tables.
        rng: NumPy random generator.
        n_simulations: Number of profiles to generate.

    Returns the most frequently occurring profile (list of full codes).
    """
    from collections import Counter

    profile_counts: Counter[tuple[str, ...]] = Counter()

    for _ in range(n_simulations):
        profile = tuple(
            expand_icd10_code(code, setting, prob_tables, rng)
            for code, setting in zip(icd10cdx_list, settings)
        )
        profile_counts[profile] += 1

    # Return the most common profile
    most_common = profile_counts.most_common(1)[0][0]
    return list(most_common)
