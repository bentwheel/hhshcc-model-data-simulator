"""Date simulation and age calculation utilities."""

import calendar
import hashlib
from datetime import date


def simulate_birth_day(dobmm: int, dobyy: int, person_id: str, seed: int = 42) -> int:
    """Simulate a plausible birth day given month and year.

    Uses a deterministic hash of person_id + seed so the same person always
    gets the same simulated day across runs with the same seed.

    Returns an integer day (1-28/29/30/31 depending on month/year).
    """
    max_day = calendar.monthrange(dobyy, dobmm)[1]
    # Deterministic hash -> day
    hash_input = f"{person_id}:{seed}:dob".encode()
    hash_val = int(hashlib.sha256(hash_input).hexdigest(), 16)
    return (hash_val % max_day) + 1


def make_dob(dobyy: int, dobmm: int, dobdd: int) -> int:
    """Format a date of birth as YYYYMMDD integer."""
    return dobyy * 10000 + dobmm * 100 + dobdd


def calculate_age(dob: date, as_of: date) -> int:
    """Calculate age in completed years as of a given date."""
    age = as_of.year - dob.year
    if (as_of.month, as_of.day) < (dob.month, dob.day):
        age -= 1
    return age


def dob_int_to_date(dob_int: int) -> date:
    """Convert YYYYMMDD integer to a date object."""
    year = dob_int // 10000
    month = (dob_int % 10000) // 100
    day = dob_int % 100
    return date(year, month, day)


def simulate_service_date(
    enrollment_year: int,
    enrolled_months: list[int],
    person_id: str,
    condition_index: int,
    seed: int = 42,
) -> date:
    """Simulate a plausible service date within enrolled months of the benefit year.

    Args:
        enrollment_year: The benefit year (e.g., 2022).
        enrolled_months: List of month numbers (1-12) when the person was enrolled.
        person_id: Unique person identifier for deterministic hashing.
        condition_index: Index of the condition (for uniqueness across conditions).
        seed: Random seed.

    Returns a date within one of the enrolled months.
    """
    if not enrolled_months:
        # Fallback: use June 15 of the enrollment year
        return date(enrollment_year, 6, 15)

    # Deterministic month and day selection
    hash_input = f"{person_id}:{seed}:{condition_index}:svcdate".encode()
    hash_val = int(hashlib.sha256(hash_input).hexdigest(), 16)

    month = enrolled_months[hash_val % len(enrolled_months)]
    max_day = calendar.monthrange(enrollment_year, month)[1]
    day = (hash_val // 100 % max_day) + 1

    return date(enrollment_year, month, day)
