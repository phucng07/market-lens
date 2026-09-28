"""Parsimonious observational OLS with HC3 uncertainty and sensitivity checks."""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from .config import RESULTS, START_YEAR

LIMITATION = ('Exploratory association, not a causal effect. ACS sampling error is not propagated. '
              'HC3 handles heteroskedasticity but not serial or shared-year dependence. '
              'Two cities are insufficient for reliable city-clustered inference. '
              'Common trends, omitted variables and endogenous vacancy limit interpretation.')


def design(d, interaction=False):
    x = pd.DataFrame({'const': 1.0, 'vacancy_rate': d.vacancy_rate,
                      'minneapolis': d.city.eq('Minneapolis').astype(float),
                      'time_trend': d.year - START_YEAR}, index=d.index)
    if interaction:
        x['minneapolis_trend'] = x.minneapolis * x.time_trend
    return x.astype(float)


def fit_models(d):
    eligible = d[d.acs_available]
    sample = eligible.dropna(subset=['annual_rent_to_income_pct', 'vacancy_rate']).copy()
    x = design(sample)
    if len(sample) <= 3 * x.shape[1] or np.linalg.matrix_rank(x) != x.shape[1]:
        raise ValueError('Insufficient observations or rank for exploratory model')
    y = sample.annual_rent_to_income_pct
    ordinary = sm.OLS(y, x).fit()
    model = ordinary.get_robustcov_results(cov_type='HC3', use_t=True)
    intervals = model.conf_int()
    coefficients = pd.DataFrame({'term': x.columns, 'coefficient': model.params,
        'robust_se': model.bse, 'p_value': model.pvalues, 'ci_95_low': intervals[:, 0], 'ci_95_high': intervals[:, 1]})
    coefficients.to_csv(RESULTS / 'regression_coefficients.csv', index=False)
    vif = pd.DataFrame({'term': x.columns[1:], 'vif': [variance_inflation_factor(x.to_numpy(), i) for i in range(1, x.shape[1])]})
    vif.to_csv(RESULTS / 'regression_vif.csv', index=False)
    influence = ordinary.get_influence()
    diagnostics = sample[['city', 'year']].copy()
    diagnostics['observed'] = y
    diagnostics['fitted'] = model.fittedvalues
    diagnostics['residual'] = model.resid
    diagnostics['leverage'] = influence.hat_matrix_diag
    diagnostics['cooks_distance'] = influence.cooks_distance[0]
    diagnostics.to_csv(RESULTS / 'regression_diagnostics.csv', index=False)
    sensitivity = []
    alt_x = design(sample, interaction=True)
    alt = sm.OLS(y, alt_x).fit(cov_type='HC3', use_t=True)
    sensitivity.append(dict(specification='City-specific trends', vacancy_coefficient=alt.params['vacancy_rate'],
                            robust_se=alt.bse['vacancy_rate'], n=int(alt.nobs), r_squared=alt.rsquared))
    for year in sorted(sample.year.unique()):
        subset = sample[sample.year != year]
        fit = sm.OLS(subset.annual_rent_to_income_pct, design(subset)).fit(cov_type='HC3', use_t=True)
        sensitivity.append(dict(specification=f'Exclude {year}', vacancy_coefficient=fit.params['vacancy_rate'],
                               robust_se=fit.bse['vacancy_rate'], n=int(fit.nobs), r_squared=fit.rsquared))
    pd.DataFrame(sensitivity).to_csv(RESULTS / 'regression_sensitivity.csv', index=False)
    info = dict(formula='annual_rent_to_income_pct ~ vacancy_rate + Minneapolis indicator + (year - 2010)',
                n=int(model.nobs), parameters=x.shape[1], r_squared=model.rsquared, adjusted_r_squared=model.rsquared_adj,
                covariance='HC3', interval_method='Student t with residual degrees of freedom',
                excluded_missing=int(len(eligible) - len(sample)), design_rank=int(np.linalg.matrix_rank(x)),
                condition_number=float(np.linalg.cond(x)), max_vif=float(vif.vif.max()), limitation=LIMITATION)
    (RESULTS / 'regression_info.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    return info
