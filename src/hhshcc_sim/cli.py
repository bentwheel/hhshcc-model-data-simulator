"""CLI entry point for the HHS-HCC Model Data Simulator."""

import logging
import sys

import click

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.data.meps_registry import SUPPORTED_YEARS
from hhshcc_sim.pipeline import run_pipeline

SUPPORTED_BENEFIT_YEARS = list(range(2023, 2027))


@click.command()
@click.option(
    "--meps-years",
    type=int,
    required=True,
    multiple=True,
    help=(
        f"MEPS data year(s) to derive simulated data from ({SUPPORTED_YEARS[0]}-{SUPPORTED_YEARS[-1]}). "
        "Can be specified multiple times to combine years, e.g. --meps-years 2021 --meps-years 2022"
    ),
)
@click.option(
    "--benefit-year",
    type=int,
    required=True,
    help=(
        f"HHS-HCC model benefit year ({SUPPORTED_BENEFIT_YEARS[0]}-{SUPPORTED_BENEFIT_YEARS[-1]}). "
        "Diagnosis service dates will be placed in this year."
    ),
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default="./data/output",
    show_default=True,
    help="Directory for output CSV files",
)
@click.option(
    "--data-dir",
    type=click.Path(),
    default="./data",
    show_default=True,
    help="Directory for raw/cached data files",
)
@click.option(
    "--seed",
    type=int,
    default=42,
    show_default=True,
    help="Random seed for reproducibility",
)
@click.option(
    "--dx-mode",
    type=click.Choice(["single", "mode"]),
    default="single",
    show_default=True,
    help="ICD-10 expansion mode: 'single' (one draw) or 'mode' (N simulations)",
)
@click.option(
    "--n-simulations",
    type=int,
    default=500,
    show_default=True,
    help="Number of simulations per person (only used with --dx-mode mode)",
)
@click.option(
    "--age-min",
    type=int,
    default=0,
    show_default=True,
    help="Minimum age filter (based on benefit year)",
)
@click.option(
    "--age-max",
    type=int,
    default=64,
    show_default=True,
    help="Maximum age filter (based on benefit year)",
)
@click.option(
    "--no-download",
    is_flag=True,
    default=False,
    help="Skip downloading; use cached files only",
)
@click.option(
    "--output-prefix",
    type=str,
    default="",
    show_default=True,
    help="Prefix for output filenames (e.g., 'sim_' produces sim_PERSON.csv)",
)
@click.option(
    "--sample-size",
    type=int,
    default=500,
    show_default=True,
    help="Number of persons to sample per MEPS year using survey weights (0 = use full population)",
)
@click.option(
    "-v", "--verbose",
    count=True,
    help="Increase verbosity (-v for INFO, -vv for DEBUG)",
)
def main(
    meps_years: tuple[int, ...],
    benefit_year: int,
    output_dir: str,
    data_dir: str,
    seed: int,
    dx_mode: str,
    n_simulations: int,
    age_min: int,
    age_max: int,
    no_download: bool,
    output_prefix: str,
    sample_size: int,
    verbose: int,
) -> None:
    """Generate simulated HHS-HCC DIY input files from MEPS data."""
    # Configure logging
    if verbose >= 2:
        level = logging.DEBUG
    elif verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    # Validate MEPS years
    for y in meps_years:
        if y not in SUPPORTED_YEARS:
            click.echo(
                f"Error: MEPS year {y} is not supported. "
                f"Supported years: {SUPPORTED_YEARS}",
                err=True,
            )
            sys.exit(1)

    # Validate benefit year
    if benefit_year not in SUPPORTED_BENEFIT_YEARS:
        click.echo(
            f"Error: Benefit year {benefit_year} is not supported. "
            f"Supported years: {SUPPORTED_BENEFIT_YEARS}",
            err=True,
        )
        sys.exit(1)

    config = SimulatorConfig(
        meps_years=list(meps_years),
        benefit_year=benefit_year,
        data_dir=data_dir,
        output_dir=output_dir,
        random_seed=seed,
        dx_mode=dx_mode,
        n_simulations=n_simulations,
        age_min=age_min,
        age_max=age_max,
        skip_download=no_download,
        output_prefix=output_prefix,
        sample_size=sample_size,
    )

    run_pipeline(config)

    click.echo(f"Done! Output files written to {config.output_dir}")


if __name__ == "__main__":
    main()
