import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.clean import validate
from src.config import VARIABLES


def test_city_year_integrity():
    d=pd.read_csv('data/processed/city_year_data.csv')
    validate(d, int(d.year.max()))
    assert len(d)==30 and d.acs_available.sum()==28
    assert d.loc[d.year==2020,[name for name,_ in VARIABLES.values()]].isna().all().all()
    assert d.loc[d.year==2010,'unemployment_rate'].isna().all()
    assert d.loc[(d.year>=2011)&(d.year!=2020),'unemployment_rate'].notna().all()


def test_official_geographies_and_metadata():
    d=pd.read_csv('data/processed/city_year_data.csv',dtype={'state_fips':str,'place_fips':str})
    assert set(d[d.city=='Madison'].geoid)=={'1600000US5548000'}
    assert set(d[d.city=='Minneapolis'].geoid)=={'1600000US2743000'}
    meta=pd.read_csv('data/processed/validated_census_variables.csv')
    for year in sorted(d.loc[d.acs_available,'year'].unique()):
        expected={code+'E' for code in VARIABLES if not (year==2010 and code.startswith('B23025'))}
        assert set(meta.loc[meta.year==year,'code'])==expected


def test_raw_checksums():
    for sidecar in Path('data/raw').rglob('*.metadata.json'):
        info=json.loads(sidecar.read_text())
        path=Path(str(sidecar).removesuffix('.metadata.json'))
        assert path.stat().st_size==info['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==info['sha256']
        assert info['url'].startswith(('https://api.census.gov/','https://www2.census.gov/','https://fred.stlouisfed.org/'))


def test_derived_values_from_source_estimates():
    d=pd.read_csv('data/processed/city_year_data.csv').query('acs_available')
    np.testing.assert_allclose(d.annual_rent_to_income_pct,1200*d.median_gross_rent_nominal/d.median_household_income_nominal)
    np.testing.assert_allclose(d.home_value_to_income,d.median_home_value_nominal/d.median_household_income_nominal)
    np.testing.assert_allclose(d.vacancy_rate,100*d.vacant_housing_units/d.total_housing_units)
    np.testing.assert_allclose(d.housing_units_per_1000,1000*d.housing_units/d.population)
    np.testing.assert_allclose(d.unemployment_rate,100*d.unemployed/d.civilian_labor_force,equal_nan=True)
    expected=100*(d.renter_units_30_34+d.renter_units_35_39+d.renter_units_40_49+d.renter_units_50_plus)/(d.renter_units_total-d.renter_units_not_computed)
    np.testing.assert_allclose(d.direct_rent_burden_pct,expected)
    for field in ['median_household_income','median_gross_rent','median_home_value']:
        base=d[d.year==d.year.max()].cpi.iloc[0]
        np.testing.assert_allclose(d[field+'_real'],d[field+'_nominal']*base/d.cpi)


def test_annual_fred_means():
    annual=pd.read_csv('data/processed/national_annual_data.csv')
    for series,col in [('CPIAUCSL','cpi'),('MORTGAGE30US','mortgage_rate')]:
        raw=pd.read_csv(f'data/raw/fred/{series}_2010_2024.csv',parse_dates=[0])
        expected=raw.groupby(raw.observation_date.dt.year)[series].mean()
        np.testing.assert_allclose(annual[col],expected.loc[annual.year])


def test_dictionary_is_exhaustive():
    data=pd.read_csv('data/processed/city_year_data.csv')
    dictionary=pd.read_csv('data/processed/data_dictionary.csv')
    assert list(dictionary.variable)==list(data.columns)
    assert dictionary.description.notna().all()
