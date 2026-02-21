"""Configuration dataclass for the simulator."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SimulatorConfig:
    """Configuration for an HHS-HCC simulation run."""

    meps_years: list[int]
    benefit_year: int
    data_dir: Path = field(default_factory=lambda: Path("./data"))
    output_dir: Path = field(default_factory=lambda: Path("./data/output"))
    random_seed: int = 42
    dx_mode: str = "single"  # "single" or "mode"
    n_simulations: int = 500  # only used when dx_mode="mode"
    age_min: int = 0
    age_max: int = 64
    skip_download: bool = False
    output_prefix: str = ""

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.output_dir = Path(self.output_dir)
        if isinstance(self.meps_years, int):
            self.meps_years = [self.meps_years]
        self.meps_years = sorted(self.meps_years)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def most_recent_meps_year(self) -> int:
        """Most recent MEPS year, used for CA ICD-10 frequency data."""
        return max(self.meps_years)
