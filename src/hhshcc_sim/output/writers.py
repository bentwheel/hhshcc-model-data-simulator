"""Write the four HHS-HCC DIY input CSV files."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def write_person_file(
    demographics_df: pd.DataFrame,
    enrollment_df: pd.DataFrame,
    output_dir: Path,
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

    path = output_dir / "PERSON.csv"
    person.to_csv(path, index=False)
    logger.info(f"Wrote PERSON.csv: {len(person):,} rows -> {path}")
    return path


def write_diag_file(diag_df: pd.DataFrame, output_dir: Path) -> Path:
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

    path = output_dir / "DIAG.csv"
    diag.to_csv(path, index=False)
    logger.info(f"Wrote DIAG.csv: {len(diag):,} rows -> {path}")
    return path


def write_ndc_file(ndc_df: pd.DataFrame, output_dir: Path) -> Path:
    """Write NDC.csv.

    Columns: ENROLID, NDC
    """
    ndc = ndc_df[["ENROLID", "NDC"]].copy()
    ndc["NDC"] = ndc["NDC"].astype(str).str.zfill(11)

    path = output_dir / "NDC.csv"
    ndc.to_csv(path, index=False)
    logger.info(f"Wrote NDC.csv: {len(ndc):,} rows -> {path}")
    return path


def write_hcpcs_file(output_dir: Path) -> Path:
    """Write HCPCS.csv (header only, no data rows).

    Columns: ENROLID, HCPCS
    """
    path = output_dir / "HCPCS.csv"
    hcpcs = pd.DataFrame(columns=["ENROLID", "HCPCS"])
    hcpcs.to_csv(path, index=False)
    logger.info(f"Wrote HCPCS.csv: header only (placeholder) -> {path}")
    return path


def write_all_output_files(
    demographics_df: pd.DataFrame,
    enrollment_df: pd.DataFrame,
    diag_df: pd.DataFrame,
    ndc_df: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Path]:
    """Write all four HHS-HCC DIY input files.

    Returns dict mapping file type -> output path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    return {
        "person": write_person_file(demographics_df, enrollment_df, output_dir),
        "diag": write_diag_file(diag_df, output_dir),
        "ndc": write_ndc_file(ndc_df, output_dir),
        "hcpcs": write_hcpcs_file(output_dir),
    }
