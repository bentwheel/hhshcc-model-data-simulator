"""Build and write an end-of-run summary report."""

import logging
from pathlib import Path

import pandas as pd

from hhshcc_sim.config import SimulatorConfig

logger = logging.getLogger(__name__)

_AGE_BINS = [-1, 1, 5, 17, 25, 34, 44, 54, 64, 200]
_AGE_LABELS = ["0-1", "2-5", "6-17", "18-25", "26-34", "35-44", "45-54", "55-64", "65+"]


def _fmt_pct(count: int, total: int) -> str:
    """Format a percentage string."""
    if total == 0:
        return "0.0%"
    return f"{100 * count / total:.1f}%"


def _distribution_table(series: pd.Series, label: str, order: list[str] | None = None) -> str:
    """Build a formatted distribution table from a Series."""
    counts = series.value_counts()
    total = counts.sum()
    if order is not None:
        counts = counts.reindex(order, fill_value=0)

    lines = [f"  {label:<16} {'Count':>8}    Pct"]
    for val, cnt in counts.items():
        lines.append(f"  {str(val):<16} {cnt:>8,}  {_fmt_pct(cnt, total):>6}")
    return "\n".join(lines)


def build_summary(
    config: SimulatorConfig,
    demographics_df: pd.DataFrame,
    enrollment_df: pd.DataFrame,
    diag_df: pd.DataFrame,
    ndc_df: pd.DataFrame,
    hcpcs_df: pd.DataFrame,
    validation_errors: list[str],
    elapsed: float,
) -> str:
    """Build the full summary report as a formatted string."""
    sep = "=" * 80
    lines = [
        sep,
        "HHS-HCC MODEL DATA SIMULATOR - RUN SUMMARY",
        sep,
        "",
    ]

    # Configuration
    years_str = ", ".join(str(y) for y in config.meps_years)
    prefix_display = config.output_prefix if config.output_prefix else "(none)"
    lines.extend([
        "Configuration",
        f"  MEPS year(s):       {years_str}",
        f"  Benefit year:       {config.benefit_year}",
        f"  Random seed:        {config.random_seed}",
        f"  DX mode:            {config.dx_mode}",
        f"  Age range:          {config.age_min}-{config.age_max}",
        f"  Output prefix:      {prefix_display}",
        f"  Output directory:   {config.output_dir}",
        "",
    ])

    # Output file row counts
    prefix = config.output_prefix
    n_person = len(demographics_df)
    n_diag = len(diag_df)
    n_ndc = len(ndc_df)
    n_hcpcs = len(hcpcs_df)

    lines.extend([
        "Output Files",
        f"  {prefix}PERSON.csv:  {n_person:>12,} rows",
        f"  {prefix}DIAG.csv:    {n_diag:>12,} rows",
        f"  {prefix}NDC.csv:     {n_ndc:>12,} rows",
        f"  {prefix}HCPCS.csv:   {n_hcpcs:>12,} rows",
        "",
    ])

    # Age group distribution
    if n_person > 0 and "AGE_LAST" in demographics_df.columns:
        age_bands = pd.cut(
            demographics_df["AGE_LAST"],
            bins=_AGE_BINS,
            labels=_AGE_LABELS,
        )
        lines.append("Age Group Distribution")
        lines.append(_distribution_table(age_bands, "Age Band", _AGE_LABELS))
        lines.append("")

    # Metal level distribution
    if len(enrollment_df) > 0 and "METAL" in enrollment_df.columns:
        metal_order = ["silver", "bronze", "gold", "platinum", "catastrophic"]
        lines.append("Metal Level Distribution")
        lines.append(_distribution_table(enrollment_df["METAL"], "Metal", metal_order))
        lines.append("")

    # CSR indicator distribution
    if len(enrollment_df) > 0 and "CSR_INDICATOR" in enrollment_df.columns:
        lines.append("CSR Indicator Distribution")
        lines.append(_distribution_table(enrollment_df["CSR_INDICATOR"], "CSR"))
        lines.append("")

    # Per-member utilization by age group
    if n_person > 0 and "AGE_LAST" in demographics_df.columns:
        person_ages = demographics_df[["ENROLID", "AGE_LAST"]].copy()
        person_ages["age_band"] = pd.cut(
            person_ages["AGE_LAST"], bins=_AGE_BINS, labels=_AGE_LABELS,
        )

        dx_counts = diag_df.groupby("ENROLID").size().rename("dx") if n_diag > 0 else pd.Series(dtype=int, name="dx")
        ndc_counts = ndc_df.groupby("ENROLID").size().rename("ndc") if n_ndc > 0 else pd.Series(dtype=int, name="ndc")
        hcpcs_counts = hcpcs_df.groupby("ENROLID").size().rename("hcpcs") if n_hcpcs > 0 else pd.Series(dtype=int, name="hcpcs")

        util = person_ages.set_index("ENROLID").join(dx_counts).join(ndc_counts).join(hcpcs_counts)
        util = util.fillna(0)

        lines.append("Per-Member Utilization by Age Group")
        lines.append(f"  {'Age Band':<16} {'Avg DX':>8} {'Avg NDC':>8} {'Avg HCPCS':>10}")

        for band in _AGE_LABELS:
            band_data = util[util["age_band"] == band]
            if len(band_data) == 0:
                continue
            avg_dx = band_data["dx"].mean()
            avg_ndc = band_data["ndc"].mean()
            avg_hcpcs = band_data["hcpcs"].mean()
            lines.append(f"  {band:<16} {avg_dx:>8.1f} {avg_ndc:>8.1f} {avg_hcpcs:>10.1f}")

        # Total row
        avg_dx_total = util["dx"].mean()
        avg_ndc_total = util["ndc"].mean()
        avg_hcpcs_total = util["hcpcs"].mean()
        lines.append(f"  {'Total':<16} {avg_dx_total:>8.1f} {avg_ndc_total:>8.1f} {avg_hcpcs_total:>10.1f}")
        lines.append("")

    # Unique code counts
    unique_dx = diag_df["DIAG"].nunique() if n_diag > 0 else 0
    unique_ndc = ndc_df["NDC"].nunique() if n_ndc > 0 else 0
    unique_hcpcs = hcpcs_df["HCPCS"].nunique() if n_hcpcs > 0 else 0
    lines.extend([
        "Unique Code Counts",
        f"  ICD-10 codes:   {unique_dx:>8,}",
        f"  NDC codes:      {unique_ndc:>8,}",
        f"  HCPCS codes:    {unique_hcpcs:>8,}",
        "",
    ])

    # Validation and timing
    if validation_errors:
        lines.append(f"Validation: FAILED ({len(validation_errors)} errors)")
        for err in validation_errors:
            lines.append(f"  - {err}")
    else:
        lines.append("Validation: PASSED")

    lines.append(f"Elapsed: {elapsed:.1f}s")
    lines.append(sep)

    return "\n".join(lines)


def write_summary(
    summary_text: str,
    output_dir: Path,
    prefix: str = "",
) -> Path:
    """Write the summary report to a text file and log it."""
    path = output_dir / f"{prefix}SUMMARY.txt"
    path.write_text(summary_text + "\n")

    for line in summary_text.split("\n"):
        logger.info(line)

    logger.info(f"Wrote {prefix}SUMMARY.txt -> {path}")
    return path
