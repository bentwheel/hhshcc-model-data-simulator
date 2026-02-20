"""Registry of California CHHS ICD-10 diagnosis code frequency data URLs.

Data source: California Department of Health Care Access and Information (HCAI)
hosted on data.chhs.ca.gov. Three settings are available:
  - ED: Emergency Department
  - PDD: Patient Discharge Data (Inpatient)
  - AS: Ambulatory Surgery (Outpatient)
"""

# Maps (year, setting) -> direct XLSX download URL
CA_ICD10_URLS: dict[int, dict[str, str]] = {
    2016: {
        "ed": "https://data.chhs.ca.gov/dataset/0e43d826-14d2-4ee3-b4f7-4ef86b961b9c/resource/201e85b9-1425-44a3-9d2b-c6923f1392b6/download/2016_diagnosiscodefrequencies_rev_ed.xlsx",
        "ip": "https://data.chhs.ca.gov/dataset/d1ac90ad-d583-426f-8012-828743cf4ac1/resource/909c5223-430d-41d4-92fc-f130e468b8a0/download/2016diagnosiscodefrequenciespdd.xlsx",
        "op": "https://data.chhs.ca.gov/dataset/d84f8a92-24e2-401d-b789-6e208c264aea/resource/ca84dce7-b635-45e0-823c-2b8938562546/download/2016diagnosiscodefrequenciesas.xlsx",
    },
    2017: {
        "ed": "https://data.chhs.ca.gov/dataset/0e43d826-14d2-4ee3-b4f7-4ef86b961b9c/resource/09f54b1f-3065-43e3-b846-d8ef45dc1b08/download/2017diagnosiscodefrequenciesed.xlsx",
        "ip": "https://data.chhs.ca.gov/dataset/d1ac90ad-d583-426f-8012-828743cf4ac1/resource/4250a094-28a0-4015-a3b8-15a9c800ea31/download/2017diagnosiscodefrequenciespdd.xlsx",
        "op": "https://data.chhs.ca.gov/dataset/d84f8a92-24e2-401d-b789-6e208c264aea/resource/d811ce7b-9c34-4c42-b7d1-3e38ce995606/download/2017diagnosiscodefrequenciesas.xlsx",
    },
    2018: {
        "ed": "https://data.chhs.ca.gov/dataset/0e43d826-14d2-4ee3-b4f7-4ef86b961b9c/resource/a1cfe6fa-2a4c-4a2b-ad9a-0bae62875f8a/download/2018_diagnosiscodefrequencies_ed.xlsx",
        "ip": "https://data.chhs.ca.gov/dataset/d1ac90ad-d583-426f-8012-828743cf4ac1/resource/600b8009-6bd7-4cf9-8ed1-8722f5fbc29c/download/2018_diagnosiscodefrequencies_pdd.xlsx",
        "op": "https://data.chhs.ca.gov/dataset/d84f8a92-24e2-401d-b789-6e208c264aea/resource/11da89d3-ba37-4b7b-b3b4-6a993ca28edb/download/2018_diagnosiscodefrequencies_as.xlsx",
    },
    2019: {
        "ed": "https://data.chhs.ca.gov/dataset/0e43d826-14d2-4ee3-b4f7-4ef86b961b9c/resource/9cb3e590-408b-4ad6-87ea-f6cbe5315755/download/2019_diagnosiscodefrequencies_ed.xlsx",
        "ip": "https://data.chhs.ca.gov/dataset/d1ac90ad-d583-426f-8012-828743cf4ac1/resource/4ba178f4-a8eb-4a47-a18a-27ba4d78a60a/download/2019_diagnosiscodefrequencies_pdd.xlsx",
        "op": "https://data.chhs.ca.gov/dataset/d84f8a92-24e2-401d-b789-6e208c264aea/resource/eb261dbb-700c-4586-8ce7-db8c5598d98b/download/2019_diagnosiscodefrequencies_as.xlsx",
    },
    2020: {
        "ed": "https://data.chhs.ca.gov/dataset/0e43d826-14d2-4ee3-b4f7-4ef86b961b9c/resource/d1837662-3ea0-4624-ad6b-0cfaa6a59962/download/2020_diagnosiscodefrequencies_ed.xlsx",
        "ip": "https://data.chhs.ca.gov/dataset/d1ac90ad-d583-426f-8012-828743cf4ac1/resource/e15bdc87-520b-4e5c-a260-64cd1b89ffdf/download/2020_diagnosiscodefrequencies_pdd.xlsx",
        "op": "https://data.chhs.ca.gov/dataset/d84f8a92-24e2-401d-b789-6e208c264aea/resource/f6e6bf74-a969-4ae4-8a88-bbea7cd990cf/download/2020_diagnosiscodefrequencies_as.xlsx",
    },
    2021: {
        "ed": "https://data.chhs.ca.gov/dataset/0e43d826-14d2-4ee3-b4f7-4ef86b961b9c/resource/1de63074-3b1c-41a6-91e2-a3b412ac3cbb/download/2021_diagnosiscodefrequencies_ed.xlsx",
        "ip": "https://data.chhs.ca.gov/dataset/d1ac90ad-d583-426f-8012-828743cf4ac1/resource/c73a6f6b-99e5-4809-8eb9-58aa8ec0f8b5/download/2021_diagnosiscodefrequencies_pdd.xlsx",
        "op": "https://data.chhs.ca.gov/dataset/d84f8a92-24e2-401d-b789-6e208c264aea/resource/9af34427-c55f-4059-b73e-96f890631571/download/2021_diagnosiscodefrequencies_as.xlsx",
    },
    2022: {
        "ed": "https://data.chhs.ca.gov/dataset/0e43d826-14d2-4ee3-b4f7-4ef86b961b9c/resource/c654a87f-7419-4164-baa7-9b22586f2f1e/download/2022_diagnosiscodefrequencies_ed.xlsx",
        "ip": "https://data.chhs.ca.gov/dataset/d1ac90ad-d583-426f-8012-828743cf4ac1/resource/bade0b84-9c2a-49b2-8bf1-01edec1ade71/download/2022_diagnosiscodefrequencies_pdd.xlsx",
        "op": "https://data.chhs.ca.gov/dataset/d84f8a92-24e2-401d-b789-6e208c264aea/resource/679921ac-af6a-437f-9a00-9627380dbb2e/download/2022_diagnosiscodefrequencies_as.xlsx",
    },
    2023: {
        "ed": "https://data.chhs.ca.gov/dataset/0e43d826-14d2-4ee3-b4f7-4ef86b961b9c/resource/b35e8d82-d7ef-4229-95c6-cb8d3e36fcab/download/2023_diagnosiscodefrequencies_ed.xlsx",
        "ip": "https://data.chhs.ca.gov/dataset/d1ac90ad-d583-426f-8012-828743cf4ac1/resource/cd7c3480-e7b1-4724-b385-e7bb3b8e1af4/download/2023_diagnosiscodefrequencies_pdd.xlsx",
        "op": "https://data.chhs.ca.gov/dataset/d84f8a92-24e2-401d-b789-6e208c264aea/resource/d9bd6e3a-c50d-43b3-851d-e734d965e808/download/2023_diagnosiscodefrequencies_as.xlsx",
    },
}

SUPPORTED_YEARS = sorted(CA_ICD10_URLS.keys())


def get_ca_urls(year: int) -> dict[str, str]:
    """Get CA CHHS download URLs for a given year.

    Returns dict with keys 'ed', 'ip', 'op'.
    Raises ValueError if year is not supported.
    """
    if year not in CA_ICD10_URLS:
        raise ValueError(
            f"CA ICD-10 frequency data for year {year} is not available. "
            f"Supported years: {SUPPORTED_YEARS}"
        )
    return CA_ICD10_URLS[year]
