"""Write the four HHS-HCC DIY input CSV files."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def write_person_file(
    demographics_df: pd.DataFrame,
    enrollment_df: pd.DataFrame,
    output_dir: Path,
    prefix: str = "",
) -> Path:
    """Write PERSON.csv by merging demographics and enrollment data.

    Columns: ENROLID, SEX, DOB, AGE_LAST, METAL, CSR_INDICATOR, ENROLDURATION
    """
    person = demographics_df[["ENROLID", "SEX", "DOB", "AGE_LAST"]].merge(
        enrollment_df[["ENROLID", "ENROLDURATION", "METAL", "CSR_INDICATOR"]],
        on="ENROLID",
        how="inner",
    )

    # Ensure correct column order per DIY spec
    person = person[
        ["ENROLID", "SEX", "DOB", "AGE_LAST", "METAL", "CSR_INDICATOR", "ENROLDURATION"]
    ]

    # Format types
    person["SEX"] = person["SEX"].astype(int)
    person["DOB"] = person["DOB"].astype(int)
    person["AGE_LAST"] = person["AGE_LAST"].astype(int)
    person["CSR_INDICATOR"] = person["CSR_INDICATOR"].astype(int)
    person["ENROLDURATION"] = person["ENROLDURATION"].astype(int)
    person["METAL"] = person["METAL"].str.lower()

    person = person.sort_values("ENROLID").reset_index(drop=True)

    path = output_dir / f"{prefix}PERSON.csv"
    person.to_csv(path, index=False)
    logger.info(f"Wrote {prefix}PERSON.csv: {len(person):,} rows -> {path}")
    return path


def write_diag_file(diag_df: pd.DataFrame, output_dir: Path, prefix: str = "") -> Path:
    """Write DIAG.csv.

    Columns: ENROLID, DIAG, DIAGNOSIS_SERVICE_DATE, AGE_AT_DIAGNOSIS
    """
    diag = diag_df[
        ["ENROLID", "DIAG", "DIAGNOSIS_SERVICE_DATE", "AGE_AT_DIAGNOSIS"]
    ].copy()

    # Ensure DIAG is string, no periods, left-justified, up to 7 chars
    diag["DIAG"] = diag["DIAG"].astype(str).str.replace(".", "", regex=False).str[:7]
    diag["DIAGNOSIS_SERVICE_DATE"] = diag["DIAGNOSIS_SERVICE_DATE"].astype(int)
    diag["AGE_AT_DIAGNOSIS"] = diag["AGE_AT_DIAGNOSIS"].astype(int)

    diag = diag.sort_values("ENROLID").reset_index(drop=True)

    path = output_dir / f"{prefix}DIAG.csv"
    diag.to_csv(path, index=False)
    logger.info(f"Wrote {prefix}DIAG.csv: {len(diag):,} rows -> {path}")
    return path


def write_ndc_file(ndc_df: pd.DataFrame, output_dir: Path, prefix: str = "") -> Path:
    """Write NDC.csv.

    Columns: ENROLID, NDC
    """
    ndc = ndc_df[["ENROLID", "NDC"]].copy()
    ndc["NDC"] = ndc["NDC"].astype(str).str.zfill(11)

    ndc = ndc.sort_values("ENROLID").reset_index(drop=True)

    path = output_dir / f"{prefix}NDC.csv"
    ndc.to_csv(path, index=False)
    logger.info(f"Wrote {prefix}NDC.csv: {len(ndc):,} rows -> {path}")
    return path


def write_hcpcs_file(hcpcs_df: pd.DataFrame, output_dir: Path, prefix: str = "") -> Path:
    """Write HCPCS.csv.

    Columns: ENROLID, HCPCS
    """
    path = output_dir / f"{prefix}HCPCS.csv"

    if len(hcpcs_df) == 0:
        hcpcs = pd.DataFrame(columns=["ENROLID", "HCPCS"])
    else:
        hcpcs = hcpcs_df[["ENROLID", "HCPCS"]].copy()
        hcpcs["HCPCS"] = hcpcs["HCPCS"].astype(str).str.strip()

    hcpcs = hcpcs.sort_values("ENROLID").reset_index(drop=True)

    hcpcs.to_csv(path, index=False)
    logger.info(f"Wrote {prefix}HCPCS.csv: {len(hcpcs):,} rows -> {path}")
    return path


def write_all_output_files(
    demographics_df: pd.DataFrame,
    enrollment_df: pd.DataFrame,
    diag_df: pd.DataFrame,
    ndc_df: pd.DataFrame,
    hcpcs_df: pd.DataFrame,
    output_dir: Path,
    prefix: str = "",
) -> dict[str, Path]:
    """Write all four HHS-HCC DIY input files.

    Returns dict mapping file type -> output path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    return {
        "person": write_person_file(demographics_df, enrollment_df, output_dir, prefix),
        "diag": write_diag_file(diag_df, output_dir, prefix),
        "ndc": write_ndc_file(ndc_df, output_dir, prefix),
        "hcpcs": write_hcpcs_file(hcpcs_df, output_dir, prefix),
    }
