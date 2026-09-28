"""Synthetic inputs are confined to these unit tests."""
import numpy as np
import pandas as pd
import pytest
from src.metrics import calculate, ratio, real_value


@pytest.mark.parametrize('numerator,denominator,scale,expected', [
    (1000,60000,1200,20), (300000,60000,1,5), (50,1000,100,5),
    (10,200,100,5), (1000,2000,1000,500)])
def test_ratios(numerator, denominator, scale, expected):
    assert ratio(numerator, denominator, scale) == pytest.approx(expected)


def test_missing_and_zero_denominators():
    assert np.isnan(ratio(1,0))
    assert np.isnan(ratio(1,-1))
    assert np.isnan(ratio(np.nan,5))
    assert ratio(0,5) == 0


def test_inflation():
    assert real_value(100,200,300) == 150
    assert real_value(100,300,300) == 100
    assert np.isnan(real_value(100,0,300))


def test_growth_does_not_cross_gap():
    d = pd.read_csv('data/processed/city_year_data.csv')
    recomputed = calculate(d)
    columns = [c for c in d if c.endswith('_yoy_pct')]
    assert recomputed.loc[d.year.isin([2010,2020,2021]),columns].isna().all().all()
    row = recomputed[(d.city=='Madison') & (d.year==2012)].iloc[0]
    prior = d[(d.city=='Madison') & (d.year==2011)].iloc[0]
    assert row.population_yoy_pct == pytest.approx(100*(row.population/prior.population-1))
