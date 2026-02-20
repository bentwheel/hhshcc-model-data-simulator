"""Download MEPS Public Use Files from AHRQ."""

import logging
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

from hhshcc_sim.config import SimulatorConfig
from hhshcc_sim.data.meps_registry import get_hc_ids, get_meps_download_url

logger = logging.getLogger(__name__)


def download_file(url: str, dest: Path, description: str = "") -> Path:
    """Download a file with a progress bar. Returns the destination path."""
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    total = int(response.headers.get("content-length", 0))

    with open(dest, "wb") as f, tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        desc=description or dest.name,
    ) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            pbar.update(len(chunk))

    return dest


def extract_dta_from_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Extract a .dta file from a MEPS zip archive. Returns the .dta path."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        dta_files = [n for n in zf.namelist() if n.lower().endswith(".dta")]
        if not dta_files:
            raise FileNotFoundError(f"No .dta file found in {zip_path}")
        # Extract the first (usually only) .dta file
        zf.extract(dta_files[0], dest_dir)
        return dest_dir / dta_files[0]


def download_meps_file(hc_id: str, raw_dir: Path, skip_if_exists: bool = True) -> Path:
    """Download and extract a single MEPS PUF.

    Returns path to the extracted .dta file.
    """
    # Check for already-extracted .dta file
    dta_path = raw_dir / f"{hc_id}.dta"
    if skip_if_exists and dta_path.exists():
        logger.info(f"Already cached: {dta_path}")
        return dta_path

    # Also check for case variations (MEPS sometimes uses uppercase in zip)
    for existing in raw_dir.glob(f"{hc_id}*.dta"):
        if skip_if_exists:
            logger.info(f"Already cached: {existing}")
            return existing

    url = get_meps_download_url(hc_id)
    zip_path = raw_dir / f"{hc_id}dta.zip"

    logger.info(f"Downloading {hc_id} from {url}")
    download_file(url, zip_path, description=f"MEPS {hc_id}")

    logger.info(f"Extracting {zip_path}")
    extracted = extract_dta_from_zip(zip_path, raw_dir)

    # Rename to a consistent lowercase name
    if extracted != dta_path and extracted.name.lower() != dta_path.name:
        extracted.rename(dta_path)
        extracted = dta_path

    # Clean up zip
    zip_path.unlink(missing_ok=True)

    return extracted


def download_meps_files(config: SimulatorConfig) -> dict[str, Path]:
    """Download all three MEPS PUFs (FYC, COND, PMED) for the configured year.

    Returns dict mapping file_type ('fyc', 'cond', 'pmed') -> local .dta path.
    """
    hc_ids = get_hc_ids(config.meps_year)
    raw_dir = config.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    paths = {}
    for file_type, hc_id in hc_ids.items():
        paths[file_type] = download_meps_file(
            hc_id, raw_dir, skip_if_exists=config.skip_download
        )

    return paths
