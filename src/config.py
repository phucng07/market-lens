"""Study choices; paths are relative to the repository root."""
from pathlib import Path

START_YEAR = 2010
RAW = Path('data/raw')
PROCESSED = Path('data/processed')
RESULTS = Path('data/results')
SF = 'https://www2.census.gov/programs-surveys/acs/summary_file/'
CITIES = {'Madison': ('Wisconsin', 'wi'), 'Minneapolis': ('Minnesota', 'mn')}
# FIPS codes are discovered from Census geography files, never assumed here.
VARIABLES = {
    'B01003_001': ('population', 'Total'),
    'B19013_001': ('median_household_income_nominal', 'Median household income'),
    'B25064_001': ('median_gross_rent_nominal', 'Median gross rent'),
    'B25077_001': ('median_home_value_nominal', 'Median value'),
    'B25001_001': ('housing_units', 'Total'),
    'B25002_001': ('total_housing_units', 'Total'),
    'B25002_002': ('occupied_housing_units', 'Occupied'),
    'B25002_003': ('vacant_housing_units', 'Vacant'),
    'B23025_003': ('civilian_labor_force', 'Civilian labor force'),
    'B23025_004': ('employed', 'Employed'),
    'B23025_005': ('unemployed', 'Unemployed'),
    'B25070_001': ('renter_units_total', 'Total'),
    'B25070_007': ('renter_units_30_34', '30.0 to 34.9 percent'),
    'B25070_008': ('renter_units_35_39', '35.0 to 39.9 percent'),
    'B25070_009': ('renter_units_40_49', '40.0 to 49.9 percent'),
    'B25070_010': ('renter_units_50_plus', '50.0 percent or more'),
    'B25070_011': ('renter_units_not_computed', 'Not computed'),
}
TABLES = sorted({x.split('_')[0] for x in VARIABLES})


def make_directories():
    for folder in [RAW, PROCESSED, RESULTS, Path('figures'), Path('excel'), Path('report'), Path('docs')]:
        folder.mkdir(parents=True, exist_ok=True)
