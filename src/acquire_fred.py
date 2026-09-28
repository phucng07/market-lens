"""National annual context, using complete calendar-year observation sets."""
import pandas as pd
from .fetch import fetch
from .config import PROCESSED, START_YEAR

SERIES = {
    'CPIAUCSL': ('cpi', ['Consumer Price Index', 'Seasonally Adjusted', 'Monthly']),
    'MORTGAGE30US': ('mortgage_rate', ['30-Year Fixed Rate', 'Weekly', 'Freddie Mac']),
}


def acquire(latest, offline=False):
    result = pd.DataFrame({'year': range(START_YEAR, latest + 1)})
    for series, (name, tokens) in SERIES.items():
        url = f'https://fred.stlouisfed.org/series/{series}'
        page = fetch(url, f'fred/{series}_definition.html', offline).read_text(encoding='utf-8')
        if not all(token in page for token in tokens):
            raise ValueError(f'FRED series definition changed or response invalid: {series}')
        url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={START_YEAR}-01-01&coed={latest}-12-31'
        path = fetch(url, f'fred/{series}_{START_YEAR}_{latest}.csv', offline)
        frame = pd.read_csv(path, parse_dates=['observation_date'], na_values=['.'])
        frame = frame[frame.observation_date.dt.year.between(START_YEAR, latest)]
        if frame.observation_date.duplicated().any() or frame[series].isna().any():
            raise ValueError(f'Duplicate or missing FRED observations: {series}')
        frame['year'] = frame.observation_date.dt.year
        annual = frame.groupby('year')[series].agg(['mean', 'count'])
        if series == 'CPIAUCSL':
            months = frame.observation_date.dt.to_period('M')
            expected = pd.period_range(f'{START_YEAR}-01', f'{latest}-12', freq='M')
            complete = not months.duplicated().any() and set(months) == set(expected)
        else:
            complete = annual['count'].between(52, 53).all()
        # Holiday releases can fall on Wednesday, including across a year boundary.
        if series == 'MORTGAGE30US':
            for _, g in frame.groupby('year'):
                complete = complete and (g.observation_date.min().dayofyear <= 8)
                complete = complete and (g.observation_date.max().month == 12 and g.observation_date.max().day >= 24)
                complete = complete and g.observation_date.sort_values().diff().dropna().dt.days.between(1, 10).all()
        if not complete or set(annual.index) != set(result.year):
            raise ValueError(f'Incomplete calendar years for {series}: {annual}')
        annual = annual.rename(columns={'mean': name, 'count': name + '_observations'})
        result = result.merge(annual, on='year', validate='one_to_one')
    result.to_csv(PROCESSED / 'national_annual_data.csv', index=False)
    return result
