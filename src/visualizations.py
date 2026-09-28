"""Question-driven figures with explicit missing-year breaks."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter, MaxNLocator
from pathlib import Path

COLORS = {'Madison': '#176b87', 'Minneapolis': '#b65b2a'}
FIGURES = [
    ('real_income', 'median_household_income_real', 'Has household purchasing power increased?', 'Annual household income'),
    ('real_rent', 'median_gross_rent_real', 'How much has rent risen after inflation?', 'Monthly gross rent'),
    ('rent_income_proxy', 'annual_rent_to_income_pct', 'Has annual rent kept pace with household income?', 'Annualized rent-to-income proxy (%)'),
    ('real_home_value', 'median_home_value_real', 'Have home values risen in real terms?', 'Owner-occupied median home value'),
    ('home_income_ratio', 'home_value_to_income', 'How large are home values relative to incomes?', 'Home-value-to-income ratio (times annual income)'),
    ('population_growth', 'population_yoy_pct', 'How quickly is each city growing?', 'Population change from prior calendar year (%)'),
    ('housing_supply', 'housing_units_per_1000', 'Has housing stock kept pace with population?', 'Housing units per 1,000 residents'),
    ('vacancy', 'vacancy_rate', 'How much housing stock is vacant?', 'All vacant units / all housing units (%)'),
    ('direct_rent_burden', 'direct_rent_burden_pct', 'How common is renter cost burden?', 'Rent >=30% of income among computable renter units (%)'),
    ('unemployment', 'unemployment_rate', 'How has the local labor market changed?', 'Unemployed / civilian labor force (%)'),
]


def style(ax, title, ylabel, source, gap=True):
    ax.set_title(title, loc='left', fontsize=15, weight='bold', pad=20)
    ax.set_xlabel('Year')
    ax.set_ylabel(ylabel, labelpad=12)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=8))
    ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.1f}' if '%' in ylabel or 'ratio' in ylabel else '{x:,.0f}'))
    ax.grid(axis='y', color='#dfe4e8', linewidth=.7)
    ax.spines[['top', 'right']].set_visible(False)
    if gap:
        ax.axvspan(2019.65, 2020.35, color='#d9dfe4', alpha=.45)
    ax.figure.text(.10, .035, source, fontsize=8, color='#475569')
    ax.figure.subplots_adjust(left=.12, right=.96, top=.86, bottom=.20)


def generate(d):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.labelcolor': '#263445'})
    base_year = int(d.real_dollar_base_year.iloc[0])
    for slug, metric, title, ylabel in FIGURES:
        fig, ax = plt.subplots(figsize=(10.5, 5.6))
        for city, group in d.groupby('city'):
            ax.plot(group.year, group[metric], marker='o', markersize=4, linewidth=2, color=COLORS[city], label=city)
        if metric.endswith('_real'):
            ylabel += f' ({base_year} USD)'
        source = 'Source: U.S. Census Bureau, ACS 1-year; BLS CPI-U via FRED for real dollars.\n2020 ACS unavailable; no interpolation. Annual estimates have sampling error.'
        if slug == 'population_growth':
            source += ' 2021 growth also unavailable.'
        style(ax, title, ylabel, source)
        ax.legend(frameon=False)
        fig.savefig(Path('figures') / f'{slug}.png', dpi=170)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    national = d.drop_duplicates('year')
    ax.plot(national.year, national.mortgage_rate, marker='o', color='#334155', linewidth=2)
    style(ax, 'How has national mortgage financing changed?', '30-year fixed mortgage rate (annual average, %)',
          'Source: Freddie Mac, MORTGAGE30US via FRED; mean of weekly observations.\nNational context, not a city-specific borrowing rate. PMMS method changed November 2022.', gap=False)
    fig.savefig('figures/mortgage_context.png', dpi=170)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    for city, group in d.groupby('city'):
        ax.scatter(group.housing_units_per_1000, group.annual_rent_to_income_pct, label=city, color=COLORS[city], s=38)
        for _, row in group[group.year.isin([d.year.min(), d.year.max()])].iterrows():
            ax.annotate(str(int(row.year)), (row.housing_units_per_1000, row.annual_rent_to_income_pct), xytext=(5, 5), textcoords='offset points')
    style(ax, 'Does greater housing availability coincide with affordability?', 'Annualized rent-to-income proxy (%)',
          'Source: U.S. Census Bureau, ACS 1-year. One point per observed city-year.\nAssociation only; income composition and shared trends can affect both measures.', gap=False)
    ax.set_xlabel('Housing units per 1,000 residents')
    ax.legend(frameon=False)
    fig.savefig('figures/supply_affordability.png', dpi=170)
    plt.close(fig)
