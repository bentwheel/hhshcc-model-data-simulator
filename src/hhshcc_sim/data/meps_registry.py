"""Registry mapping MEPS data years to HC file numbers and download URLs."""

# Maps MEPS data year -> { file_type: HC file identifier }
# Sources: https://meps.ahrq.gov/mepsweb/data_stats/download_data_files.jsp
MEPS_FILES: dict[int, dict[str, str]] = {
    2016: {"fyc": "h192", "cond": "h190", "pmed": "h188a"},
    2017: {"fyc": "h201", "cond": "h199", "pmed": "h197a"},
    2018: {"fyc": "h209", "cond": "h207", "pmed": "h206a"},
    2019: {"fyc": "h216", "cond": "h214", "pmed": "h213a"},
    2020: {"fyc": "h224", "cond": "h222", "pmed": "h220a"},
    2021: {"fyc": "h233", "cond": "h231", "pmed": "h229a"},
    2022: {"fyc": "h243", "cond": "h241", "pmed": "h239a"},
    2023: {"fyc": "h251", "cond": "h249", "pmed": "h248a"},
}

SUPPORTED_YEARS = sorted(MEPS_FILES.keys())

# MEPS variable names embed a 2-digit year suffix (e.g., PRIJA22 for Jan 2022 private ins.)
MEPS_YEAR_SUFFIX: dict[int, str] = {year: str(year)[-2:] for year in MEPS_FILES}

# Month abbreviations used in MEPS FYC variable names (January-December)
MEPS_MONTH_ABBREVS = ["JA", "FE", "MA", "AP", "MY", "JU", "JL", "AU", "SE", "OC", "NO", "DE"]


def get_meps_download_url(hc_id: str) -> str:
    """Construct the AHRQ download URL for a MEPS Stata (.dta) zip file."""
    return f"https://meps.ahrq.gov/mepsweb/data_files/pufs/{hc_id}/{hc_id}dta.zip"


def get_hc_ids(year: int) -> dict[str, str]:
    """Get HC file identifiers for a given MEPS year.

    Returns dict with keys 'fyc', 'cond', 'pmed'.
    Raises ValueError if year is not supported.
    """
    if year not in MEPS_FILES:
        raise ValueError(
            f"MEPS year {year} is not supported. Supported years: {SUPPORTED_YEARS}"
        )
    return MEPS_FILES[year]
