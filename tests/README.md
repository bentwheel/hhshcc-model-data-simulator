# Test Suite

This document describes the unit test suite for the HHS-HCC Model Data Simulator. All tests use [pytest](https://docs.pytest.org/) and run against mock data fixtures defined in `conftest.py` &mdash; no network access or real MEPS data is required.

## Running Tests

```bash
# Run all tests
pytest

# Verbose output
pytest -v

# Run a specific test file
pytest tests/test_hcpcs.py

# Run a single test
pytest tests/test_hcpcs.py::test_build_rxc_crosswalk
```

## Shared Fixtures (`conftest.py`)

| Fixture | Description |
|---------|-------------|
| `mock_fyc_df` | Small FYC-like DataFrame with 5 persons, varying ages/sex/coverage/income, using MEPS 2022 variable naming conventions |
| `mock_cond_df` | 5 condition records with known 3-character ICD-10 codes and care setting flags |
| `mock_pmed_df` | 5 prescription records with known NDC codes (including one missing-data sentinel) |
| `mock_ca_freq_df` | ICD-10 frequency table for testing code expansion (9 rows across 5 prefixes) |
| `mock_prob_tables` | Pre-built probability tables derived from `mock_ca_freq_df` |
| `simulator_config` | A `SimulatorConfig` with `meps_years=[2022]`, `benefit_year=2025`, `random_seed=42`, and temporary directories |

## Test Files

### `test_demographics.py` &mdash; Demographics Processor (5 tests)

Tests the extraction and transformation of person-level fields from the MEPS Full-Year Consolidated (FYC) file.

| Test | What it verifies |
|------|-----------------|
| `test_process_demographics_basic` | Mock FYC data produces persons with all required output columns (`ENROLID`, `SEX`, `DOB`, `AGE_LAST`, `POVLEV`, `ENROLLED_MONTHS`); `SEX` is 1 or 2; `DOB` is a valid 8-digit date; ages fall within 0&ndash;64 |
| `test_process_demographics_age_based_on_benefit_year` | `AGE_LAST` is calculated relative to the benefit year (2025), not the MEPS data year (2022) &mdash; a person born in 1985 is age 40, not 37 |
| `test_process_demographics_age_filter` | Setting `age_min=21` correctly excludes persons under 21 as of the benefit year |
| `test_process_demographics_deterministic` | Identical config and seed produce identical `DOB` values across two runs |
| `test_process_demographics_different_seed` | Different random seeds produce different simulated birth days |

### `test_enrollment.py` &mdash; Enrollment Processor (6 tests)

Tests the simulation of metal level, CSR indicator, and enrollment duration from MEPS coverage and income data.

| Test | What it verifies |
|------|-----------------|
| `test_simulate_metal_level_under_30` | Catastrophic metal level is possible for persons under age 30 |
| `test_simulate_metal_level_over_30` | Catastrophic metal level is excluded for persons aged 30 and older |
| `test_simulate_metal_level_low_income_silver_bias` | Low-income persons (below 200% FPL) receive silver plans at a higher rate than higher-income persons |
| `test_simulate_csr_indicator_non_silver` | Non-silver plans always receive `CSR_INDICATOR=1` (no cost-sharing reduction) |
| `test_simulate_csr_indicator_silver_low_income` | Silver plans with income 100&ndash;150% FPL receive CSR indicator values greater than 1 |
| `test_process_enrollment` | End-to-end enrollment processing produces correct output columns and valid value ranges |

### `test_hcpcs.py` &mdash; HCPCS Processor / RXC Crosswalk (6 tests)

Tests the generation of HCPCS procedure codes from NDC drug codes using the RXC (Prescription Drug Category) crosswalk derived from CMS DIY Tables 10a and 10b.

| Test | What it verifies |
|------|-----------------|
| `test_build_rxc_crosswalk` | NDC&rarr;RXC and RXC&rarr;HCPCS lookup tables are correctly built from mock Table 10a/10b data (4 NDC mappings across 3 RXC groups) |
| `test_process_hcpcs_basic` | Two persons with NDCs mapping to different RXCs each receive HCPCS codes drawn from the correct RXC group |
| `test_process_hcpcs_no_matching_ndcs` | NDCs not present in the crosswalk produce an empty HCPCS DataFrame with correct columns |
| `test_process_hcpcs_empty_input` | An empty NDC DataFrame produces an empty HCPCS DataFrame |
| `test_process_hcpcs_deterministic` | Identical config and seed produce identical HCPCS selections across two runs |
| `test_process_hcpcs_deduplicates` | When two NDCs for the same person map to the same single HCPCS code, the result is deduplicated to one row |

### `test_icd10_expansion.py` &mdash; ICD-10 Code Expansion (6 tests)

Tests the probabilistic expansion of 3-character truncated ICD-10-CM codes to full specificity using California hospital frequency data.

| Test | What it verifies |
|------|-----------------|
| `test_build_expansion_probabilities` | California frequency data builds per-prefix probability tables with correct care setting columns |
| `test_expand_icd10_code_known_prefix` | A known 3-character prefix (`E11`) expands to one of its valid full codes (`E1110`, `E1165`, or `E119`) |
| `test_expand_icd10_code_unknown_prefix` | An unknown prefix not in the frequency data falls back to the 3-character code as-is |
| `test_expand_icd10_code_single_expansion` | A prefix with only one full code (`I10`) always expands to that code |
| `test_expand_icd10_code_deterministic` | Same seed produces the same expansion result |
| `test_expand_icd10_codes_mode` | Mode-based expansion across N simulations returns the most frequently occurring diagnosis profile |

### `test_prescriptions.py` &mdash; Prescription Processor (7 tests)

Tests the extraction and cleaning of 11-digit NDC codes from the MEPS Prescribed Medicines file.

| Test | What it verifies |
|------|-----------------|
| `test_clean_ndc_valid` | A valid 11-digit NDC passes through unchanged |
| `test_clean_ndc_with_dashes` | Dashes are stripped (`5430-0100-01` &rarr; `54300010001`) |
| `test_clean_ndc_short_padded` | Short NDC strings are zero-padded to 11 digits |
| `test_clean_ndc_missing` | `NaN` and negative MEPS missing-data sentinel values (`-9`) return `None` |
| `test_clean_ndc_all_zeros` | An all-zeros NDC is rejected |
| `test_clean_ndc_with_decimal` | Stata numeric conversion artifacts (`.0` suffix) are handled correctly |
| `test_process_prescriptions` | End-to-end processing: filters to target population, cleans NDCs, and deduplicates `(ENROLID, NDC)` pairs |

### `test_validators.py` &mdash; Output Validators (4 tests)

Tests the post-pipeline validation of output CSV files against the HHS-HCC DIY input specification.

| Test | What it verifies |
|------|-----------------|
| `test_validate_valid_outputs` | A complete set of correctly formatted output files passes all validation checks with zero errors |
| `test_validate_missing_file` | Missing CSV files are detected and reported |
| `test_validate_invalid_sex` | An invalid `SEX` value (3) is flagged as a validation error |
| `test_validate_orphan_enrolid` | A `DIAG.csv` ENROLID not present in `PERSON.csv` is caught as a referential integrity violation |

### `test_writers.py` &mdash; Output File Writers (4 tests)

Tests the writing of the four HHS-HCC DIY input CSV files.

| Test | What it verifies |
|------|-----------------|
| `test_write_person_file` | `PERSON.csv` has the correct column order per the DIY spec (`ENROLID`, `SEX`, `DOB`, `AGE_LAST`, `METAL`, `CSR_INDICATOR`, `ENROLDURATION`) and correct values |
| `test_write_hcpcs_file_empty` | An empty HCPCS DataFrame produces a header-only CSV |
| `test_write_hcpcs_file_with_data` | A HCPCS DataFrame with records writes correct columns and values |
| `test_write_all_output_files` | All four output files (`PERSON.csv`, `DIAG.csv`, `NDC.csv`, `HCPCS.csv`) are created and exist on disk |
