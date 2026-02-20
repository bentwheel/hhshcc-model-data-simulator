"""Configuration dataclass for the simulator."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SimulatorConfig:
    """Configuration for an HHS-HCC simulation run."""

    meps_year: int
    data_dir: Path = field(default_factory=lambda: Path("./data"))
    output_dir: Path = field(default_factory=lambda: Path("./data/output"))
    random_seed: int = 42
    dx_mode: str = "single"  # "single" or "mode"
    n_simulations: int = 500  # only used when dx_mode="mode"
    age_min: int = 0
    age_max: int = 64
    skip_download: bool = False

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        self.output_dir = Path(self.output_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def meps_year_suffix(self) -> str:
        """Two-digit year suffix used in MEPS FYC variable names."""
        return str(self.meps_year)[-2:]
