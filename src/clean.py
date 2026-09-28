"""Clean Census sentinel codes, preserve gaps, and merge national annual data."""
import numpy as np
import pandas as pd
from .config import CITIES, VARIABLES, START_YEAR, PROCESSED
from .metrics import calculate


def clean(census, national, latest):
    d = census.copy()
    for variable, _ in VARIABLES.values():
        for col in [variable, variable + '_moe']:
            d[col] = pd.to_numeric(d[col], errors='coerce')
            d.loc[d[col] < 0, col] = np.nan
    # Explicit missing rows prevent lines and growth rates from crossing 2020.
    grid = pd.MultiIndex.from_product([CITIES, range(START_YEAR, latest + 1)], names=['city', 'year'])
    d = d.set_index(['city', 'year']).reindex(grid).reset_index()
    for col in ['state', 'state_fips', 'place_fips', 'geoid']:
        d[col] = d.groupby('city')[col].transform(lambda s: s.ffill().bfill())
    d['acs_available'] = d.year.ne(2020)
    d['data_note'] = np.where(d.year == 2020, 'Standard ACS 1-year estimates not released',
                            np.where(d.year == 2010, 'B23025 unavailable in 2010', ''))
    d = calculate(d.merge(national, on='year', how='left', validate='many_to_one'))
    validate(d, latest)
    d.to_csv(PROCESSED / 'city_year_data.csv', index=False)
    return d


def validate(d, latest):
    assert set(d.city) == set(CITIES), 'Unexpected city'
    assert not d.duplicated(['city', 'year']).any(), 'Duplicate city-year'
    assert len(d) == 2 * (latest - START_YEAR + 1), 'Incomplete year grid'
    assert d.year.between(START_YEAR, latest).all()
    assert not np.isinf(d.select_dtypes(include='number').to_numpy()).any()
    for col in ['population', 'housing_units', 'median_household_income_nominal',
                'median_gross_rent_nominal', 'median_home_value_nominal', 'cpi']:
        assert d[col].dropna().gt(0).all(), col
        assert d.loc[d.acs_available, col].notna().all(), f'Missing core data: {col}'
    for col in ['vacancy_rate', 'unemployment_rate', 'direct_rent_burden_pct', 'rent_burden_excluded_pct']:
        assert d[col].dropna().between(0, 100).all(), col
    assert d.annual_rent_to_income_pct.dropna().ge(0).all()
    available = d[d.acs_available]
    assert np.allclose(available.housing_units, available.total_housing_units)
    assert np.allclose(available.total_housing_units, available.occupied_housing_units + available.vacant_housing_units)
    labor = d[d.civilian_labor_force.notna()]
    assert np.allclose(labor.civilian_labor_force, labor.employed + labor.unemployed)
    assert d.loc[d.year == 2020, 'population'].isna().all()
