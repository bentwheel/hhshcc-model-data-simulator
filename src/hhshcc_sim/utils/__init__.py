"""Utility functions."""

import logging


def tqdm_disabled() -> bool:
    """Return True if tqdm progress bars should be disabled (non-verbose mode)."""
    return logging.getLogger().getEffectiveLevel() > logging.INFO
