"""Validate output files against the HHS-HCC DIY spec."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def validate_person_file(path: Path) -> list[str]:
    """Validate PERSON.csv format and contents."""
    errors = []
    df = pd.read_csv(path, dtype=str)

    required_cols = {"ENROLID", "SEX", "DOB", "AGE_LAST", "METAL", "CSR_INDICATOR", "ENROLDURATION"}
    missing = required_cols - set(df.columns)
    if missing:
        errors.append(f"PERSON.csv missing columns: {missing}")
        return errors

    # SEX must be 1 or 2
    invalid_sex = df[~df["SEX"].isin(["1", "2"])]
    if len(invalid_sex) > 0:
        errors.append(f"PERSON.csv has {len(invalid_sex)} rows with invalid SEX values")

    # DOB must be 8 digits
    invalid_dob = df[~df["DOB"].str.match(r"^\d{8}$", na=False)]
    if len(invalid_dob) > 0:
        errors.append(f"PERSON.csv has {len(invalid_dob)} rows with invalid DOB format")

    # METAL must be one of the valid values
    valid_metals = {"platinum", "gold", "silver", "bronze", "catastrophic"}
    invalid_metal = df[~df["METAL"].isin(valid_metals)]
    if len(invalid_metal) > 0:
        errors.append(f"PERSON.csv has {len(invalid_metal)} rows with invalid METAL values")

    # CSR_INDICATOR must be 1-11
    invalid_csr = df[~df["CSR_INDICATOR"].isin([str(i) for i in range(1, 12)])]
    if len(invalid_csr) > 0:
        errors.append(f"PERSON.csv has {len(invalid_csr)} rows with invalid CSR_INDICATOR")

    # ENROLDURATION must be 1-12
    invalid_dur = df[~df["ENROLDURATION"].isin([str(i) for i in range(1, 13)])]
    if len(invalid_dur) > 0:
        errors.append(f"PERSON.csv has {len(invalid_dur)} rows with invalid ENROLDURATION")

    # ENROLID must be unique
    dupes = df[df["ENROLID"].duplicated()]
    if len(dupes) > 0:
        errors.append(f"PERSON.csv has {len(dupes)} duplicate ENROLID values")

    return errors


def validate_diag_file(path: Path, person_path: Path) -> list[str]:
    """Validate DIAG.csv format and referential integrity."""
    errors = []
    df = pd.read_csv(path, dtype=str)
    person_df = pd.read_csv(person_path, dtype=str)

    required_cols = {"ENROLID", "DIAG", "DIAGNOSIS_SERVICE_DATE", "AGE_AT_DIAGNOSIS"}
    missing = required_cols - set(df.columns)
    if missing:
        errors.append(f"DIAG.csv missing columns: {missing}")
        return errors

    # DIAG must be 3-7 characters, alphanumeric, no periods
    invalid_diag = df[~df["DIAG"].str.match(r"^[A-Z0-9]{3,7}$", na=False)]
    if len(invalid_diag) > 0:
        errors.append(f"DIAG.csv has {len(invalid_diag)} rows with invalid DIAG format")

    # DIAGNOSIS_SERVICE_DATE must be 8 digits
    invalid_date = df[~df["DIAGNOSIS_SERVICE_DATE"].str.match(r"^\d{8}$", na=False)]
    if len(invalid_date) > 0:
        errors.append(f"DIAG.csv has {len(invalid_date)} rows with invalid DIAGNOSIS_SERVICE_DATE")

    # Referential integrity: all ENROLIDs must exist in PERSON
    valid_ids = set(person_df["ENROLID"])
    orphan_ids = set(df["ENROLID"]) - valid_ids
    if orphan_ids:
        errors.append(f"DIAG.csv has {len(orphan_ids)} ENROLIDs not in PERSON.csv")

    return errors


def validate_ndc_file(path: Path, person_path: Path) -> list[str]:
    """Validate NDC.csv format and referential integrity."""
    errors = []
    df = pd.read_csv(path, dtype=str)
    person_df = pd.read_csv(person_path, dtype=str)

    required_cols = {"ENROLID", "NDC"}
    missing = required_cols - set(df.columns)
    if missing:
        errors.append(f"NDC.csv missing columns: {missing}")
        return errors

    # NDC must be 11 digits
    invalid_ndc = df[~df["NDC"].str.match(r"^\d{11}$", na=False)]
    if len(invalid_ndc) > 0:
        errors.append(f"NDC.csv has {len(invalid_ndc)} rows with invalid NDC format")

    # Referential integrity
    valid_ids = set(person_df["ENROLID"])
    orphan_ids = set(df["ENROLID"]) - valid_ids
    if orphan_ids:
        errors.append(f"NDC.csv has {len(orphan_ids)} ENROLIDs not in PERSON.csv")

    return errors


def validate_hcpcs_file(path: Path, person_path: Path) -> list[str]:
    """Validate HCPCS.csv format and referential integrity."""
    errors = []
    df = pd.read_csv(path, dtype=str)

    required_cols = {"ENROLID", "HCPCS"}
    missing = required_cols - set(df.columns)
    if missing:
        errors.append(f"HCPCS.csv missing columns: {missing}")
        return errors

    if len(df) == 0:
        return errors

    # HCPCS must be 5 characters, alphanumeric
    invalid_hcpcs = df[~df["HCPCS"].str.match(r"^[A-Z0-9]{5}$", na=False)]
    if len(invalid_hcpcs) > 0:
        errors.append(f"HCPCS.csv has {len(invalid_hcpcs)} rows with invalid HCPCS format")

    # Referential integrity
    person_df = pd.read_csv(person_path, dtype=str)
    valid_ids = set(person_df["ENROLID"])
    orphan_ids = set(df["ENROLID"]) - valid_ids
    if orphan_ids:
        errors.append(f"HCPCS.csv has {len(orphan_ids)} ENROLIDs not in PERSON.csv")

    return errors


def validate_all_outputs(output_dir: Path, prefix: str = "") -> list[str]:
    """Run all validators on the output directory. Returns list of error messages."""
    errors = []

    person_path = output_dir / f"{prefix}PERSON.csv"
    diag_path = output_dir / f"{prefix}DIAG.csv"
    ndc_path = output_dir / f"{prefix}NDC.csv"
    hcpcs_path = output_dir / f"{prefix}HCPCS.csv"

    for path, name in [
        (person_path, f"{prefix}PERSON.csv"),
        (diag_path, f"{prefix}DIAG.csv"),
        (ndc_path, f"{prefix}NDC.csv"),
        (hcpcs_path, f"{prefix}HCPCS.csv"),
    ]:
        if not path.exists():
            errors.append(f"{name} not found in {output_dir}")

    if errors:
        return errors

    errors.extend(validate_person_file(person_path))
    errors.extend(validate_diag_file(diag_path, person_path))
    errors.extend(validate_ndc_file(ndc_path, person_path))
    errors.extend(validate_hcpcs_file(hcpcs_path, person_path))

    if not errors:
        logger.info("All output files passed validation.")
    else:
        for err in errors:
            logger.warning(f"Validation error: {err}")

    return errors
