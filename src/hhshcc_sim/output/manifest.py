"""Write a reproducibility manifest (JSON sidecar) for each simulation run."""

import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from hhshcc_sim.config import SimulatorConfig

logger = logging.getLogger(__name__)


def _get_git_commit() -> str | None:
    """Return the current git commit hash, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _get_package_version() -> str | None:
    """Return the installed package version, or None if not installed."""
    try:
        from importlib.metadata import version

        return version("hhshcc-sim")
    except Exception:
        return None


def write_manifest(
    config: SimulatorConfig,
    output_paths: dict[str, Path],
    row_counts: dict[str, int],
    validation_errors: list[str],
    elapsed: float,
) -> Path:
    """Write manifest.json alongside the output files.

    Args:
        config: Simulator configuration used for this run.
        output_paths: Dict mapping file type -> output Path (from write_all_output_files).
        row_counts: Dict mapping file type -> row count (e.g. {"person": 1234, ...}).
        validation_errors: List of validation error messages (empty if all passed).
        elapsed: Total elapsed time in seconds.

    Returns:
        Path to the written manifest.json file.
    """
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": _get_git_commit(),
        "package_version": _get_package_version(),
        "python_version": sys.version,
        "config": {
            "meps_years": config.meps_years,
            "benefit_year": config.benefit_year,
            "random_seed": config.random_seed,
            "dx_mode": config.dx_mode,
            "n_simulations": config.n_simulations,
            "age_min": config.age_min,
            "age_max": config.age_max,
            "output_prefix": config.output_prefix,
        },
        "output_files": {
            name: {
                "path": str(path),
                "size_bytes": path.stat().st_size if path.exists() else None,
                "row_count": row_counts.get(name),
            }
            for name, path in output_paths.items()
        },
        "validation": {
            "passed": len(validation_errors) == 0,
            "error_count": len(validation_errors),
            "errors": validation_errors,
        },
        "elapsed_seconds": round(elapsed, 2),
    }

    manifest_path = config.output_dir / f"{config.output_prefix}manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    logger.info(f"Wrote {config.output_prefix}manifest.json -> {manifest_path}")
    return manifest_path
