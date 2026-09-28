"""Descriptive evidence and correlations, keeping levels and changes separate."""
import json
import pandas as pd
from .config import RESULTS

METRICS = ['population', 'housing_units', 'median_household_income_nominal', 'median_gross_rent_nominal',
           'median_home_value_nominal', 'median_household_income_real', 'median_gross_rent_real',
           'median_home_value_real', 'annual_rent_to_income_pct', 'home_value_to_income',
           'housing_units_per_1000', 'vacancy_rate', 'unemployment_rate', 'direct_rent_burden_pct',
           'mortgage_rate']
CORRELATES = ['annual_rent_to_income_pct', 'home_value_to_income', 'housing_units_per_1000',
              'vacancy_rate', 'unemployment_rate', 'mortgage_rate', 'population_yoy_pct']


def analyze(d):
    summary, findings = [], {}
    for city, group in d.groupby('city'):
        findings[city] = {}
        for col in METRICS:
            valid = group[['year', col]].dropna()
            first, last = valid.iloc[0], valid.iloc[-1]
            row = dict(city=city, variable=col, n=len(valid), mean=valid[col].mean(), median=valid[col].median(),
                       std=valid[col].std(ddof=1), min=valid[col].min(), max=valid[col].max(),
                       first_year=int(first.year), latest_year=int(last.year), first_value=first[col],
                       latest_value=last[col], period_change_pct=(last[col] / first[col] - 1) * 100,
                       level_change=last[col] - first[col])
            summary.append(row)
            findings[city][col] = {k: v for k, v in row.items() if k not in ['city', 'variable']}
    pd.DataFrame(summary).to_csv(RESULTS / 'summary_statistics.csv', index=False)
    (RESULTS / 'findings.json').write_text(json.dumps(findings, indent=2), encoding='utf-8')
    correlations = []
    for scope, group in [('Pooled', d[d.acs_available]), *list(d.groupby('city'))]:
        for form in ['levels', 'annual_changes']:
            values = group[CORRELATES].copy()
            if form == 'annual_changes':
                # Changes require consecutive calendar years in the original grid.
                group = group.sort_values(['city', 'year'])
                values = group.groupby('city')[CORRELATES].diff()
                contiguous = group.groupby('city').year.diff().eq(1)
                values.loc[~contiguous] = float('nan')
            for a in CORRELATES:
                for b in CORRELATES:
                    pair = values[[a, b]] if a != b else values[[a]]
                    pair = pair.dropna()
                    r = values[a].corr(values[b]) if len(pair) >= 3 else float('nan')
                    correlations.append(dict(scope=scope, form=form, variable_x=a, variable_y=b, n=len(pair), pearson_r=r))
    pd.DataFrame(correlations).to_csv(RESULTS / 'correlations.csv', index=False)
    latest = d[d.year == d.year.max()].set_index('city')[METRICS].T
    latest['Madison_minus_Minneapolis'] = latest.Madison - latest.Minneapolis
    latest.rename_axis('variable').to_csv(RESULTS / 'latest_city_comparison.csv')
    return findings
