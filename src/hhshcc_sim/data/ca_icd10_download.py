"""Download California CHHS ICD-10 diagnosis code frequency files."""

import logging
from pathlib import Path

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.data.ca_icd10_registry import get_ca_urls
from hhshcc_sim.data.meps_download import download_file

logger = logging.getLogger(__name__)


def download_ca_icd10_files(config: SimulatorConfig) -> dict[str, Path]:
    """Download ED, IP, OP frequency XLSX files from CA CHHS.

    Returns dict mapping setting ('ed', 'ip', 'op') -> local file path.
    """
    ca_year = config.most_recent_meps_year
    urls = get_ca_urls(ca_year)
    raw_dir = config.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    paths = {}
    for setting, url in urls.items():
        filename = f"ca_icd10_{ca_year}_{setting}.xlsx"
        dest = raw_dir / filename

        if config.skip_download and dest.exists():
            logger.info(f"Already cached: {dest}")
            paths[setting] = dest
            continue

        logger.info(f"Downloading CA {setting.upper()} ICD-10 data for {ca_year}")
        download_file(url, dest, description=f"CA {setting.upper()} {ca_year}")
        paths[setting] = dest

    return paths
