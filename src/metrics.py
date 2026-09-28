"""Economic calculations. Missing or nonpositive denominators stay missing."""
import numpy as np


def ratio(numerator, denominator, scale=1):
    numerator, denominator = np.asarray(numerator, dtype=float), np.asarray(denominator, dtype=float)
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(denominator > 0, numerator / denominator * scale, np.nan)


def real_value(nominal, cpi, reference_cpi):
    return ratio(nominal, cpi, reference_cpi)


def calculate(frame):
    d = frame.sort_values(['city', 'year']).copy()
    reference_year = int(d.loc[d.acs_available, 'year'].max())
    reference_cpi = d.loc[d.year == reference_year, 'cpi'].iloc[0]
    d['real_dollar_base_year'] = reference_year
    for field in ['median_household_income', 'median_gross_rent', 'median_home_value']:
        d[field + '_real'] = real_value(d[field + '_nominal'], d.cpi, reference_cpi)
    d['annual_rent_to_income_pct'] = ratio(d.median_gross_rent_nominal, d.median_household_income_nominal, 1200)
    d['home_value_to_income'] = ratio(d.median_home_value_nominal, d.median_household_income_nominal)
    d['housing_units_per_1000'] = ratio(d.housing_units, d.population, 1000)
    d['vacancy_rate'] = ratio(d.vacant_housing_units, d.total_housing_units, 100)
    d['unemployment_rate'] = ratio(d.unemployed, d.civilian_labor_force, 100)
    d['rent_burden_computable_units'] = d.renter_units_total - d.renter_units_not_computed
    d['rent_burden_30_plus_units'] = d[['renter_units_30_34', 'renter_units_35_39',
                                      'renter_units_40_49', 'renter_units_50_plus']].sum(axis=1, min_count=4)
    d['direct_rent_burden_pct'] = ratio(d.rent_burden_30_plus_units, d.rent_burden_computable_units, 100)
    d['rent_burden_excluded_pct'] = ratio(d.renter_units_not_computed, d.renter_units_total, 100)
    for column in ['population', 'housing_units', 'median_household_income_real',
                   'median_gross_rent_real', 'median_home_value_real']:
        d[column + '_yoy_pct'] = d.groupby('city')[column].pct_change(fill_method=None) * 100
        contiguous = d.groupby('city').year.diff().eq(1)
        d.loc[~contiguous, column + '_yoy_pct'] = np.nan
    return d
