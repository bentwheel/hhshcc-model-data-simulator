"""CLI entry point for the HHS-HCC Model Data Simulator."""

import logging
import sys

import click

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.data.meps_registry import SUPPORTED_YEARS
from hhshcc_sim.pipeline import run_pipeline


@click.command()
@click.option(
    "--year",
    type=int,
    required=True,
    help=f"MEPS data year ({SUPPORTED_YEARS[0]}-{SUPPORTED_YEARS[-1]})",
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
    help="Minimum age filter",
)
@click.option(
    "--age-max",
    type=int,
    default=64,
    show_default=True,
    help="Maximum age filter",
)
@click.option(
    "--no-download",
    is_flag=True,
    default=False,
    help="Skip downloading; use cached files only",
)
@click.option(
    "-v", "--verbose",
    count=True,
    help="Increase verbosity (-v for INFO, -vv for DEBUG)",
)
def main(
    year: int,
    output_dir: str,
    data_dir: str,
    seed: int,
    dx_mode: str,
    n_simulations: int,
    age_min: int,
    age_max: int,
    no_download: bool,
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

    # Validate year
    if year not in SUPPORTED_YEARS:
        click.echo(
            f"Error: Year {year} is not supported. "
            f"Supported years: {SUPPORTED_YEARS}",
            err=True,
        )
        sys.exit(1)

    config = SimulatorConfig(
        meps_year=year,
        data_dir=data_dir,
        output_dir=output_dir,
        random_seed=seed,
        dx_mode=dx_mode,
        n_simulations=n_simulations,
        age_min=age_min,
        age_max=age_max,
        skip_download=no_download,
    )

    run_pipeline(config)

    click.echo(f"Done! Output files written to {config.output_dir}")


if __name__ == "__main__":
    main()
