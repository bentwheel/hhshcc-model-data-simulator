# HHS-HCC Model Data Simulator

Simulate realistic input data files for the CMS HHS-HCC risk adjustment model using publicly available [Medical Expenditure Panel Survey (MEPS)](https://meps.ahrq.gov/mepsweb/) data.

## Background

CMS is releasing a Python-based implementation of the HHS-HCC risk adjustment model (the "DIY" software) for the ACA/marketplace population. The model requires four specific input CSV files &mdash; person-level enrollment, diagnosis codes, NDC drug codes, and HCPCS procedure codes &mdash; but there is no publicly available test dataset that conforms to the required input specification.

This tool fills that gap by constructing plausible, HIPAA-safe input files derived entirely from public-use survey microdata. The simulated data follows real-world demographic, diagnostic, and prescribing distributions observed in MEPS, making it far more useful for testing and development than purely random or hand-crafted fixtures.

## Use Cases

**Primary: IT and testing of the HHS-HCC DIY software.** Generate a complete set of input files that exercise the full breadth of the model &mdash; infant, child, and adult age groups across all five metal levels &mdash; without needing access to protected health information or real claims data. Useful for:

- Validating end-to-end pipeline correctness before running on production data
- Regression testing across model version updates
- Load and performance testing with realistic record volumes
- Training and onboarding new analysts on the HHS-HCC model

**Secondary: Supplementing MEPS analytics.** The intermediate outputs of this tool (expanded ICD-10 codes, NDC extracts, enrollment profiles) can support MEPS-based research in areas such as:

- Studying diagnosis code distributions across demographic subgroups
- Analyzing prescription drug utilization patterns in the privately insured under-65 population
- Exploring the relationship between income, plan metal level, and health conditions
- Prototyping risk adjustment methodologies on nationally representative survey data

## How It Works

The simulator runs a ten-stage pipeline:

1. **Download data** &mdash; Three MEPS Public Use Files (Full-Year Consolidated, Medical Conditions, Prescribed Medicines) are downloaded as Stata files from AHRQ for each specified MEPS year. California ICD-10 frequency tables and the CMS DIY Tables Excel file (containing RXC crosswalks) are also downloaded. Multiple MEPS years can be combined for a larger sample.
2. **Build expansion and crosswalk tables** &mdash; California ICD-10 frequency data is parsed into probability tables for code expansion. CMS DIY Tables 10a (NDC&rarr;RXC) and 10b (HCPCS&rarr;RXC) are parsed into crosswalk lookups for HCPCS generation.
3. **Process demographics** &mdash; For each MEPS year: extracts person-level fields from the FYC file, filters to ages 0&ndash;64 (as of the benefit year) with private insurance coverage, and simulates a birth day using deterministic hashing. Birth years are shifted by the difference between the benefit year and MEPS year to preserve the MEPS age distribution. The eligible population is then resampled to the target sample size (default 500) using MEPS survey weights, producing a representative sample. ENROLIDs are prefixed with the MEPS year to ensure uniqueness when combining years.
4. **Process enrollment** &mdash; Counts months of private coverage. Simulates metal level and CSR indicator informed by the person's income (poverty level relative to FPL) and age.
5. **Expand ICD-10 codes** &mdash; MEPS truncates all diagnosis codes to 3 characters for confidentiality. This stage uses California claims frequency data to probabilistically expand each truncated code to a plausible full ICD-10-CM code, weighted by the care setting (ED, inpatient, outpatient) in which the condition was observed.
6. **Process prescriptions** &mdash; Extracts 11-digit NDC codes from the MEPS Prescribed Medicines file.
7. **Generate HCPCS codes** &mdash; For each person with NDC codes that map to an RXC (Prescription Drug Category) via CMS Table 10a, a corresponding HCPCS procedure code is assigned from the same RXC via Table 10b. This simulates the scenario where a drug identified by NDC could also be identified via a HCPCS code (e.g., J-codes for drugs administered in clinical settings).
8. **Write output files** &mdash; Produces the four CSV files matching the CY2025 HHS-HCC DIY input specification. Diagnosis service dates are placed in the benefit year (not the MEPS data year) so they fall within the model's expected date range.
9. **Validate** &mdash; Checks output format, value ranges, and referential integrity across files.
10. **Report** &mdash; Writes a `manifest.json` reproducibility sidecar (config, versions, timestamps, row counts, validation results) and a `SUMMARY.txt` report with frequency tables by age group, metal level, CSR indicator, and per-member utilization.

### Output Files

| File | Description |
|------|-------------|
| `PERSON.csv` | One row per enrollee: ID, sex, date of birth, age, metal level, CSR indicator, enrollment duration |
| `DIAG.csv` | One row per diagnosis: enrollee ID, ICD-10-CM code (expanded), service date, age at diagnosis |
| `NDC.csv` | One row per drug: enrollee ID, 11-digit NDC code |
| `HCPCS.csv` | One row per procedure: enrollee ID, HCPCS code (derived from NDC&rarr;RXC&rarr;HCPCS crosswalk) |
| `SUMMARY.txt` | Human-readable run summary with configuration, row counts, frequency tables, and per-member utilization |
| `manifest.json` | Machine-readable reproducibility manifest with config, git commit, package version, row counts, and validation results |

### ICD-10 Code Expansion

MEPS truncates all ICD-10-CM codes to 3 characters (e.g., `E11` instead of `E11.65`). Since the HHS-HCC model requires full codes, this tool uses California hospital claims data to build frequency distributions for each 3-character prefix across ED, inpatient, and outpatient settings. Each truncated code is then expanded by drawing from this distribution, weighted by the care setting where the condition was observed in MEPS.

Two expansion modes are available:

- **`single`** (default): One random draw per condition. Fast and sufficient for most testing scenarios.
- **`mode`**: Generates N simulated diagnosis profiles per person (default 500) and selects the most frequently occurring combination. More computationally expensive but produces a "most likely" profile.

## Requirements

- Python 3.11 or later
- Internet access for initial data downloads (~200 MB per MEPS year, cached after first run)

## Installation

```bash
git clone https://github.com/bentwheel/hhshcc-model-data-simulator.git
cd hhshcc-model-data-simulator
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -e .
```

For development (includes pytest, ruff, mypy):

```bash
pip install -e ".[dev]"
```

## Usage

The tool requires two key arguments: **which MEPS year(s)** to derive data from, and **which benefit year** the output files are targeting.

```bash
# Generate 2025 benefit year input files from MEPS 2022 data
hhshcc-sim --meps-years 2022 --benefit-year 2025 -v

# Combine multiple MEPS years for a larger sample
hhshcc-sim --meps-years 2021 --meps-years 2022 --benefit-year 2025 -v

# Customize output location and random seed
hhshcc-sim --meps-years 2022 --benefit-year 2025 --output-dir ./my-output --seed 12345 -v

# Adults only (ages 21-64, as of the benefit year)
hhshcc-sim --meps-years 2022 --benefit-year 2025 --age-min 21 --age-max 64 -v

# Use mode-based ICD-10 expansion with 500 simulations per person
hhshcc-sim --meps-years 2022 --benefit-year 2025 --dx-mode mode --n-simulations 500 -v

# Prefix output filenames (e.g., sim_PERSON.csv, sim_DIAG.csv, ...)
hhshcc-sim --meps-years 2022 --benefit-year 2025 --output-prefix sim_ -v

# Generate a larger sample (1000 persons instead of default 500)
hhshcc-sim --meps-years 2022 --benefit-year 2025 --sample-size 1000 -v

# Use the full MEPS population (no resampling)
hhshcc-sim --meps-years 2022 --benefit-year 2025 --sample-size 0 -v

# Skip downloading if data is already cached
hhshcc-sim --meps-years 2022 --benefit-year 2025 --no-download -v
```

Output files are written to `./data/output/` by default.

### MEPS Years vs. Benefit Year

- **`--meps-years`**: The MEPS survey year(s) from which demographics, diagnoses, and prescriptions are sourced. Multiple years can be specified to increase sample size; ENROLIDs are prefixed with the MEPS year to prevent collisions.
- **`--benefit-year`**: The HHS-HCC model year the output is intended for (2023&ndash;2026). Diagnosis service dates are placed in this year, and `AGE_LAST` is calculated as of December 31 of this year. Birth years are shifted forward by the difference between the benefit year and the MEPS year so that the MEPS age distribution is preserved (e.g., an infant in MEPS 2022 remains an infant when the benefit year is 2025).

### Supported Years

- **MEPS data years**: 2018, 2019, 2020, 2021, 2022, 2023
- **Benefit years**: 2023, 2024, 2025, 2026

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--meps-years` | *(required)* | MEPS data year(s); repeat for multiple |
| `--benefit-year` | *(required)* | HHS-HCC model benefit year (2023&ndash;2026) |
| `--output-dir` | `./data/output` | Directory for output CSV files |
| `--data-dir` | `./data` | Directory for cached raw data |
| `--seed` | `42` | Random seed for reproducibility |
| `--dx-mode` | `single` | ICD-10 expansion mode (`single` or `mode`) |
| `--n-simulations` | `500` | Simulations per person (only with `--dx-mode mode`) |
| `--age-min` | `0` | Minimum age filter (based on benefit year) |
| `--age-max` | `64` | Maximum age filter (based on benefit year) |
| `--output-prefix` | `""` | Prefix for output filenames (e.g., `sim_` produces `sim_PERSON.csv`) |
| `--sample-size` | `500` | Persons to sample per MEPS year using survey weights (0 = full population) |
| `--no-download` | off | Skip downloads, use cached files only |
| `-v` / `-vv` | off | Verbosity (INFO / DEBUG); also enables progress bars |

### Running Tests

```bash
pytest
```

The test suite (61 tests) runs entirely against mock data fixtures &mdash; no network access or real MEPS data is required. See [`tests/README.md`](tests/README.md) for a detailed description of every test case.

## Data Sources

- **MEPS Public Use Files** &mdash; Annual survey microdata from the Agency for Healthcare Research and Quality (AHRQ). Includes demographics, insurance coverage, medical conditions (truncated ICD-10-CM codes), and prescribed medicines (NDC codes). Available at [meps.ahrq.gov](https://meps.ahrq.gov/mepsweb/).
- **California HCAI Diagnosis Code Frequencies** &mdash; Aggregate diagnosis code frequency counts from California hospital emergency department, inpatient, and ambulatory surgery settings. Used to build probability distributions for expanding 3-character truncated ICD-10 codes to their full specificity. Available at [data.chhs.ca.gov](https://data.chhs.ca.gov/).
- **CMS HHS-HCC DIY Tables** &mdash; The official CMS DIY software distribution includes Excel tables mapping NDC codes to RXC (Prescription Drug Category) values (Table 10a) and HCPCS codes to RXC values (Table 10b). These crosswalks are used to generate HCPCS records from MEPS NDC data. Available at [cms.gov](https://www.cms.gov/medicare/payment/medicare-advantage-rates-statistics/risk-adjustment).

## Related Projects

- [hcc-meps](https://github.com/bentwheel/hcc-meps) &mdash; The inspiration for this project. Applies the CMS-HCC risk adjustment model (for Medicare Advantage) to MEPS data using a similar probabilistic ICD-10 code expansion approach, implemented in R.

## Known Limitations

- **HCPCS codes are derived, not observed.** MEPS does not contain HCPCS procedure codes. The `HCPCS.csv` output is generated by crossing NDC codes through the CMS RXC crosswalk (Table 10a &rarr; Table 10b), which identifies plausible HCPCS codes for drugs in the same prescription drug category. Not all RXC-eligible drugs will have corresponding HCPCS codes in the crosswalk, and the simulated codes represent drug-administration procedures (e.g., J-codes) rather than observed claims.
- **ICD-10 codes are probabilistically expanded, not observed.** The expanded codes are plausible given the truncated code and care setting, but they are not the actual codes from the underlying medical encounters.
- **Metal level and CSR indicator are simulated.** MEPS does not include plan metal level or cost-sharing reduction information. These are assigned using income-informed probability distributions based on published ACA marketplace enrollment patterns.
- **Diagnosis service dates are simulated.** MEPS conditions do not include exact service dates; these are generated as random dates within enrolled months.
- **Birth day is simulated.** MEPS provides birth month and year but not birth day; a deterministic random day is assigned per person.
- **California frequency data is used as a national proxy.** The ICD-10 code expansion is based on California claims data, which may not perfectly represent national coding patterns.

## Disclaimer

This project was primarily written with AI assistance (Claude). The code has been reviewed and tested, but **no warranty is made regarding its correctness, completeness, or fitness for any particular purpose**. Use at your own risk.

This tool generates **simulated data for testing and development purposes only**. The output files do not represent real patient data and should not be used for clinical decision-making, regulatory reporting, or actuarial certification.

The authors are not affiliated with CMS. This project is not endorsed by or associated with the Centers for Medicare & Medicaid Services, AHRQ, or any government agency.

## License

[MIT](LICENSE)
