"""Generate documentation and numerical prose directly from analytical outputs."""
import json
from pathlib import Path
import markdown
import pandas as pd
from .config import VARIABLES, RAW, RESULTS, PROCESSED
from .regression import LIMITATION


def dictionary_frame(d):
    metadata = pd.read_csv(PROCESSED/'validated_census_variables.csv')
    mapping = {r.variable: (r.code, r.label.replace(f'in {int(d.year.max())} inflation-adjusted dollars','in survey-year dollars')) for r in metadata.itertuples()}
    definitions = {
        'city': ('text', 'Census incorporated city name; Madison or Minneapolis.'),
        'state': ('text', 'State name; Wisconsin or Minnesota.'),
        'year': ('calendar year', 'ACS reference year and calendar year of national annual averages.'),
        'state_fips': ('identifier', 'Two-character Census state FIPS, discovered from geography file.'),
        'place_fips': ('identifier', 'Five-character Census place FIPS, discovered from geography file.'),
        'geoid': ('identifier', 'Census summary level 160, component 00, whole incorporated place GEO_ID.'),
        'acs_available': ('boolean', 'False for 2020, when standard ACS 1-year estimates were not released.'),
        'data_note': ('text', 'Specific availability limitation, otherwise blank.'),
        'real_dollar_base_year': ('year', 'Latest complete analysis year used as constant-dollar reference.'),
        'cpi': ('index, 1982–84=100', 'Arithmetic mean of 12 monthly CPIAUCSL observations; US city average, seasonally adjusted.'),
        'cpi_observations': ('months', 'Number of nonmissing monthly CPI observations in the annual average.'),
        'mortgage_rate': ('percent', 'Mean of weekly MORTGAGE30US observations dated in the calendar year; national 30-year fixed rate.'),
        'mortgage_rate_observations': ('weeks', 'Number of weekly mortgage observations in the annual mean; holidays can shift dates.'),
        'annual_rent_to_income_pct': ('percent', 'Annualized rent-to-income proxy = median monthly gross rent × 12 / median annual household income × 100. Not household rent burden.'),
        'home_value_to_income': ('times annual income', 'Median owner-occupied home value / median annual household income; not a mortgage-payment measure.'),
        'housing_units_per_1000': ('units per 1,000 residents', 'All housing units / population × 1,000. Includes occupied and vacant units.'),
        'vacancy_rate': ('percent', 'All vacant housing units / all housing units × 100; not the rental vacancy rate.'),
        'unemployment_rate': ('percent', 'ACS unemployed / civilian labor force × 100; residents age 16+; B23025 unavailable in 2010.'),
        'rent_burden_computable_units': ('renter-occupied units', 'B25070_001E minus B25070_011E. Excludes ratios not computed.'),
        'rent_burden_30_plus_units': ('renter-occupied units', 'Sum of B25070_007E through B25070_010E; gross rent at least 30% of household income.'),
        'direct_rent_burden_pct': ('percent', 'rent_burden_30_plus_units / rent_burden_computable_units × 100. Conditional on a computable ratio.'),
        'rent_burden_excluded_pct': ('percent', 'B25070_011E / B25070_001E × 100. Share excluded from direct-burden denominator.'),
    }
    records = []
    for col in d:
        if col in definitions:
            unit, description = definitions[col]
        elif col.endswith('_yoy_pct'):
            unit, description = 'percent', f'100 × ({col[:-8]} / its prior calendar-year value − 1). Missing unless both adjacent years observed.'
        elif col.endswith('_real'):
            unit, description = f'{int(d.real_dollar_base_year.iloc[0])} USD', f'{col.replace("_real", "_nominal")} × CPI_reference / CPI_year. Monthly for rent, annual for income, asset value for home.'
        else:
            original = col.removesuffix('_moe')
            code, label = mapping[original]
            unit = ('monthly USD' if 'gross_rent' in original else 'annual USD' if 'household_income' in original else 'USD asset value') if 'median_' in original else 'persons' if original in ['population','civilian_labor_force','employed','unemployed'] else 'housing units'
            description = f'ACS {code}: {label}.'
            if col.endswith('_moe'):
                description = f'ACS {code[:-1]}M: published 90% margin of error for {original}. Negative sentinels become missing.'
        records.append({'variable': col, 'unit': unit, 'description': description})
    frame = pd.DataFrame(records)
    frame.to_csv(PROCESSED/'data_dictionary.csv', index=False)
    return frame


def source_frame(d):
    latest = int(d.year.max())
    metadata = pd.read_csv(PROCESSED/'validated_census_variables.csv')
    records = []
    for code, (name, _) in VARIABLES.items():
        subset = metadata[metadata.variable == name]
        last = subset.iloc[-1]
        records.append(dict(source='U.S. Census Bureau', dataset=code.split('_')[0], variable=code+'E and M',
                            description=f"{last.concept}: {last.label.replace(f'in {int(d.year.max())} inflation-adjusted dollars', 'in survey-year dollars')}", url=last.metadata_url,
                            notes=f"{int(subset.year.min())}–{int(subset.year.max())}; 2020 excluded. ACS 1-year summary files; estimates and 90% MOEs."))
    records += [dict(source='U.S. Census Bureau', dataset='ACS 1-year public summary-file archive', variable='All selected ACS estimates and geography',
                     description='Original sequence archives, table-based files, geography records and table lookups. Concrete requests are recorded in source_manifest.csv.',
                     url='https://www2.census.gov/programs-surveys/acs/summary_file/', notes=f'2010–2019 and 2021–{latest}. Files cached with retrieval date and SHA-256; no API key needed.'),
                dict(source='BLS via Federal Reserve Bank of St. Louis', dataset='CPIAUCSL', variable='cpi',
                     description='All items CPI-U, U.S. city average, monthly, seasonally adjusted, 1982–84=100.',
                     url='https://fred.stlouisfed.org/series/CPIAUCSL', notes=f'2010–{latest}; arithmetic annual mean of 12 months. National index, subject to revisions.'),
                dict(source='Freddie Mac via Federal Reserve Bank of St. Louis', dataset='MORTGAGE30US', variable='mortgage_rate',
                     description='Primary Mortgage Market Survey, 30-year fixed mortgage rate, percent, weekly, not seasonally adjusted.',
                     url='https://fred.stlouisfed.org/series/MORTGAGE30US', notes=f'2010–{latest}; mean of 52/53 dated observations per calendar year. Method changed November 17, 2022. National, not city-specific. Freddie Mac copyright applies.')]
    frame = pd.DataFrame(records)
    frame['retrieval_dates_utc'] = ', '.join(sorted({json.loads(p.read_text())['retrieved_utc'][:10] for p in RAW.rglob('*.metadata.json')}))
    frame.to_csv(PROCESSED/'source_catalog.csv', index=False)
    return frame


def findings_text(f):
    lines = []
    for city in ['Madison', 'Minneapolis']:
        v = f[city]
        lines.append(f"{city}: real median income changed {v['median_household_income_real']['period_change_pct']:.1f}%, real median rent {v['median_gross_rent_real']['period_change_pct']:.1f}%, and real median home value {v['median_home_value_real']['period_change_pct']:.1f}% from {v['median_household_income_real']['first_year']} to {v['median_household_income_real']['latest_year']}.")
        lines.append(f"{city}'s annualized rent-to-income proxy changed from {v['annual_rent_to_income_pct']['first_value']:.2f}% to {v['annual_rent_to_income_pct']['latest_value']:.2f}%; its home-value-to-income ratio changed from {v['home_value_to_income']['first_value']:.2f} to {v['home_value_to_income']['latest_value']:.2f}.")
        lines.append(f"{city}'s direct renter cost-burden share changed from {v['direct_rent_burden_pct']['first_value']:.1f}% to {v['direct_rent_burden_pct']['latest_value']:.1f}% among cash-rent units with computable ratios.")
    return lines


def generate(d, rstatus):
    latest = int(d.year.max())
    observed_years = int(d.loc[d.acs_available, 'year'].nunique())
    dictionary, sources = dictionary_frame(d), source_frame(d)
    f = json.loads((RESULTS/'findings.json').read_text())
    info = json.loads((RESULTS/'regression_info.json').read_text())
    coef = pd.read_csv(RESULTS/'regression_coefficients.csv')
    slope = coef.set_index('term').loc['vacancy_rate']
    sensitivity = pd.read_csv(RESULTS/'regression_sensitivity.csv')
    statements = findings_text(f)
    (RESULTS/'headline_claims.json').write_text(json.dumps(statements, indent=2), encoding='utf-8')
    manifests = []
    for path in sorted(RAW.rglob('*.metadata.json')):
        record = json.loads(path.read_text())
        record['local_path'] = path.as_posix().removesuffix('.metadata.json')
        manifests.append(record)
    manifest = pd.DataFrame(manifests)
    manifest.to_csv(PROCESSED/'source_manifest.csv', index=False)
    dates = ', '.join(sorted({x['retrieved_utc'][:10] for x in manifests}))
    source_doc = f'''# Data sources

Retrieval dates (UTC): {dates}. The complete request URLs, local raw paths, byte lengths and SHA-256 checksums are in [source_manifest.csv](../data/processed/source_manifest.csv). Each raw file has its own immutable metadata sidecar. Source responses are never overwritten by cleaning.

## Census ACS 1-year detailed tables

Study observations: **2010–2019 and 2021–{latest}**, {observed_years} observed years per city. The primary CSV also contains explicit missing 2020 rows. Latest-release discovery selected {latest} from the complete table sets in the official summary-file catalog. This snapshot is fixed in `data/raw/release_selection.json`; it does not claim future releases will remain unavailable.

Official download root: https://www2.census.gov/programs-surveys/acs/summary_file/

2010–2019 use each year's `data/1_year_seq_by_state/STATE/` with official sequence/table lookups. 2021 adds `sequence-based-SF/`. 2022–{latest} use `table-based-SF/data/1YRData/acsdt1yYEAR-TABLE.dat` and matching geography files. Variable metadata come from `https://api.census.gov/data/YEAR/acs/acs1/groups/TABLE.json`. All concrete URLs used are saved in the manifest. The data API returned a Missing Key page, so acquisition uses the official public files without an API key.

Geographies were selected by whole-city names, summary level 160 and component 00, then checked annually. Madison city, Wisconsin: state 55, place 48000, GEO_ID 1600000US5548000. Minneapolis city, Minnesota: state 27, place 43000, GEO_ID 1600000US2743000. These are cities, not counties or metropolitan areas. Changing boundaries and population controls can affect comparisons.

{sources.to_markdown(index=False)}

## Availability and definitions

B23025 is absent from the 2010 sequence lookup and API metadata; labor force, employment and unemployment are missing in that year. No replacement population was substituted. All other selected variables were validated against their own year's Census metadata. The record of those checks is [validated_census_variables.csv](../data/processed/validated_census_variables.csv).

B25070's universe is renter-occupied housing units paying cash rent. Sum lines 007–010 for gross rent at least 30% of income, divided by line 001 minus line 011 (not computed). The excluded share is reported separately. This is different from a ratio of city medians and is not a measure of all residents.

Standard ACS 1-year estimates were not released for 2020. Experimental estimates are not comparable substitutes: [Census explanation](https://www.census.gov/programs-surveys/acs/data/experimental-data.html). No interpolation or 5-year substitution is used.

## FRED context and limitations

CPIAUCSL is produced by BLS and distributed by FRED. Take the mean of all 12 monthly observations in each calendar year. Constant-dollar values use {latest} as reference. A national price index does not measure local cost-of-living differences. Seasonal revisions can change historical CPI, so the downloaded vintage is preserved.

MORTGAGE30US is Freddie Mac's national PMMS series distributed by FRED. Average the weekly observations whose dates fall in each calendar year; holiday releases can fall on Wednesday. Verify 52/53 observations, beginning/end coverage and weekly gaps. Freddie Mac changed collection methodology on November 17, 2022, as documented on the series page. The rate is context, not a local rate or an estimate of any household's mortgage payment. Review Freddie Mac's terms on the source page before redistribution outside this portfolio.

Building permits and local administrative datasets are omitted: the ACS housing-stock series provides a consistent core without mixing permit-authority boundaries or equating permits with completed housing. No optional dataset is represented as acquired.
'''
    Path('docs/DATA_SOURCES.md').write_text(source_doc, encoding='utf-8')
    Path('docs/DATA_DICTIONARY.md').write_text('# Processed data dictionary\n\nOne row per city and calendar year, including explicit missing ACS rows for 2020. CSV blanks mean missing, never zero. Monetary estimates are nominal unless labeled real. Percentages are stored as percent values (20 means 20%), not fractions. Growth can be negative and the rent-to-income proxy can exceed 100%. MOEs apply to original estimates, not derived ratios.\n\n'+dictionary.to_markdown(index=False)+'\n', encoding='utf-8')
    methodology = f'''# Methodology

## Scope and identification

The research unit is an incorporated city-year. There are {int(d.acs_available.sum())} observed city-years and two explicit 2020 gap rows over 2010–{latest}. Official annual geography files identify the cities by name and supply their FIPS codes. Each selected estimate and its 90% margin of error is validated against the same year's table metadata. Sequence offsets are taken from official lookup files, not guessed from a different release. Occupied plus vacant units reconcile to total units; employed plus unemployed reconcile to the civilian labor force.

## Cleaning and annualization

Negative ACS sentinel values and nonnumeric suppressed cells become missing. Raw bytes stay unchanged and are checked against SHA-256 sidecars whenever reused. No missing value is replaced with zero. B23025 labor data are unavailable in 2010. Standard 2020 ACS estimates are unavailable. National data remain observed in 2020.

CPI is the mean of 12 monthly CPIAUCSL observations. Mortgage rates are the unweighted mean of 52/53 weekly dated observations, with holiday shifts respected. These are annual averages, not December levels. Both are national measures. The reference year is {latest}, the latest complete common analysis year.

## Formulas and interpretation

- Real value = nominal value × CPI_{latest} / CPI_year.
- Annualized rent-to-income proxy = median gross rent × 12 / median household income × 100.
- Home-value-to-income ratio = median owner-occupied home value / median household income.
- Housing units per 1,000 residents = all housing units / population × 1,000.
- Vacancy rate = vacant units / total units × 100. This includes all reasons for vacancy.
- ACS unemployment rate = unemployed / civilian labor force × 100.
- Direct renter burden = sum(B25070_007E:010E) / (B25070_001E − B25070_011E) × 100.
- Year-over-year change = 100 × (value_t / value_(t−1) − 1), only for adjacent observed calendar years. Both 2020 and 2021 growth are missing.

Rent is monthly and income annual. Home value is an asset-stock valuation, not an annual cost. Rent and income refer to different populations, so their ratio is a descriptive proxy. National inflation adjustment cancels in same-year ratios; it changes interpretation of dollar growth, not the ratios. ACS already expresses within-year income responses in that survey year's dollars; CPI conversion is an additional across-year adjustment, not a replacement for Census's within-year procedure.

## Descriptive evidence and correlations

Summary tables report count, mean, median, sample standard deviation, minimum, maximum, first/latest observed years and values, endpoint percent change and level difference. Rate differences should be read in percentage points, while endpoint percent changes are proportional changes. No endpoint change is annualized.

Pearson tables show pooled and separate-city levels and changes, with pairwise observation counts. Pooled levels mix between-city differences with within-city movement. Common trends can produce high correlation without a substantive relationship. Rent and home-value ratios share income denominators. Changes subtract adjacent observations; the change in population growth is a change of a growth rate. No correlation is a causal estimate, and the tables are not a multiple-hypothesis testing exercise.

## Exploratory regression

{info['formula']}

OLS uses {info['n']} city-years and {info['parameters']} coefficients including an intercept, with HC3 heteroskedasticity-robust standard errors and Student-t confidence intervals using residual degrees of freedom. Vacancy is selected as one economically interpretable housing-market covariate; city intercepts and a common linear time trend absorb baseline differences and broad drift. Income is not added as a predictor because it is already the dependent variable's denominator. Supply, unemployment and mortgage rates remain descriptive to avoid overfitting a two-city panel or stacking highly trending variables.

The design matrix has rank {info['design_rank']}; maximum non-intercept VIF is {info['max_vif']:.2f}, and the unscaled condition number is {info['condition_number']:.2f}. Complete-case exclusions among available ACS rows: {info['excluded_missing']}. Diagnostics retain fitted values, residuals, leverage and Cook's distances. A city-specific trend model and exclusion of each observed year assess sensitivity, without selecting whichever specification yields the smallest p-value.

{LIMITATION} A high R-squared does not solve these problems. P-values and intervals are conditional model summaries and should not support strong population inference. No policy treatment or instrument supplies causal identification.

## Uncertainty and reproducibility

The published 90% MOEs are retained, but full survey covariance information is unavailable. Derived-ratio uncertainty and changes in medians are not formally tested. Annual point-estimate changes can reflect survey noise, migration, household composition or changing housing quality. ACS population controls and boundary changes add comparability limitations.

Run from the repository root. The default acquisition uses immutable cached files and discovers a latest release only when no selection exists. `--offline` forbids downloading. To study a newer vintage, preserve or rename the entire existing `data/raw` directory before starting a new acquisition; do not overwrite its files. Downstream outputs will be regenerated. Requirements are bounded in requirements.txt and exact executed versions in requirements-lock.txt.

R independently recomputes the rent proxy, real income, OLS coefficients and HC3 covariance using base R, and creates a separate figure. Execution status: **{rstatus['status']}**. Details are in `data/results/r_validation.json`.
'''
    Path('docs/METHODOLOGY.md').write_text(methodology, encoding='utf-8')
    write_report(d, f, info, coef, slope, sensitivity, rstatus, statements)
    write_readme(statements, rstatus)
    return dictionary, sources


def write_report(d, f, info, coef, slope, sensitivity, rstatus, statements):
    latest = int(d.year.max())
    observed_years = int(d.loc[d.acs_available, 'year'].nunique())
    endpoint_rows = []
    for city, values in f.items():
        for variable in ['median_household_income_nominal','median_gross_rent_nominal','median_home_value_nominal',
                         'median_household_income_real','median_gross_rent_real','median_home_value_real']:
            v = values[variable]
            endpoint_rows.append({'City':city, 'Measure':variable.replace('_',' '), '2010':v['first_value'], str(latest):v['latest_value'], 'Change (%)':v['period_change_pct']})
    table = pd.DataFrame(endpoint_rows).to_markdown(index=False, floatfmt=',.1f')
    city_sections = []
    for city in ['Madison','Minneapolis']:
        v = f[city]
        city_sections.append(f'''### {city}

The annualized rent-to-income proxy changed from {v['annual_rent_to_income_pct']['first_value']:.2f}% in 2010 to {v['annual_rent_to_income_pct']['latest_value']:.2f}% in {latest}, a change of {v['annual_rent_to_income_pct']['level_change']:.2f} percentage points. This compares the rent charged for the median cash-rent unit with income for the median household across all tenures. A rise means rents outpaced this broad income benchmark; a fall means the reverse. Neither tracks the same renters or their budgets.

The home-value-to-income ratio moved from {v['home_value_to_income']['first_value']:.2f} to {v['home_value_to_income']['latest_value']:.2f}. The endpoint change in real home value was {v['median_home_value_real']['period_change_pct']:.1f}%, compared with {v['median_household_income_real']['period_change_pct']:.1f}% for real household income. Owner valuations and income therefore tell a different part of the affordability story from monthly rent. Existing owners can gain housing wealth while prospective buyers confront higher entry prices.

Population changed {v['population']['period_change_pct']:.1f}% and housing units changed {v['housing_units']['period_change_pct']:.1f}%. Housing units per 1,000 residents changed from {v['housing_units_per_1000']['first_value']:.1f} to {v['housing_units_per_1000']['latest_value']:.1f}. These stock measures are consistent with housing availability changing relative to population, but they do not isolate construction, demolitions, conversions or boundary changes. Household size and the group-quarters population also affect the ratio.

The all-housing vacancy rate changed from {v['vacancy_rate']['first_value']:.2f}% to {v['vacancy_rate']['latest_value']:.2f}%. This measure includes units held vacant for several reasons, so a higher value need not imply more rental listings available to a household searching today. Direct renter cost burden was {v['direct_rent_burden_pct']['first_value']:.1f}% in 2010 and {v['direct_rent_burden_pct']['latest_value']:.1f}% in {latest} among units with a computable rent/income ratio. That statistic concerns the distribution of actual renter ratios and should not be inferred from the city-median proxy.
''')
    corr = pd.read_csv(RESULTS/'correlations.csv')
    corr = corr[(corr.variable_x=='annual_rent_to_income_pct') & (corr.variable_y=='vacancy_rate')]
    report = f'''# MarketLens
## Housing affordability in Madison and Minneapolis, 2010–{latest}

### Abstract / Executive summary

This study asks how housing affordability changed in two Upper Midwest cities and which observed economic conditions moved with those changes. It combines U.S. Census Bureau American Community Survey 1-year estimates with national consumer prices and mortgage rates distributed by FRED. The analysis contains {observed_years} observed years for each city; 2020 is an explicit gap. Dollar values are compared in nominal terms and in {latest} purchasing power. The evidence distinguishes a city-median affordability proxy from a direct distributional measure of renter cost burden.

{' '.join(statements)} These are endpoint comparisons of annual point estimates, not tests of statistical significance. A small exploratory regression describes the association between vacancy and the rent-to-income proxy after city and trend controls. It does not identify the effect of additional housing or of any policy. 

### Research question

How has housing affordability changed in Madison and Minneapolis, and what economic factors are associated with those changes? The secondary questions distinguish three channels: housing costs relative to income, changes in the housing stock relative to population, and national financing conditions. A city can experience rising real incomes and still become less affordable under a cost-to-income measure if housing costs rise faster. Conversely, a larger housing stock does not guarantee that its location, quality or prices match the needs of lower-income households.

### Motivation

Housing absorbs resources that could otherwise finance consumption, saving or education. Renters face a recurring expense, while prospective homeowners face both an asset purchase and financing constraints. These are different economic decisions. A single price chart cannot capture them. Comparing rent and income growth asks whether the broad earnings environment kept pace with the cost of occupying rental housing. Comparing home values with income asks how large the housing asset is relative to household resources, while mortgage rates provide context for financing that asset.

Madison and Minneapolis offer a manageable city-level comparison. They are not a treatment and control group. Their household composition, housing mix, local institutions and surrounding metropolitan markets differ. City boundaries also do not enclose every job or housing alternative available to residents. The comparison is useful for describing distinct experiences and motivating further research, rather than evaluating one city's policy by treating the other as a counterfactual.

### Data

The core source is ACS 1-year detailed tables B01003, B19013, B25064, B25077, B25001, B25002, B23025 and B25070. Whole-city geography is identified from official files: Madison is state 55/place 48000; Minneapolis is state 27/place 43000. The observed years are 2010–2019 and 2021–{latest}. The cached release selection identifies {latest} as the latest complete table set found when the sources were downloaded. The 2010 B23025 labor-force fields are absent and left missing.

Population and housing counts are ACS estimates, not decennial Census enumerations. Income is median annual household income, gross rent is median monthly rent including the Census gross-rent concept, and home value is the median reported value of owner-occupied units. Those three monetary medians do not describe an identical household population. Original 90% margins of error are preserved alongside estimates. The current analysis uses point estimates and does not propagate survey uncertainty through derived statistics.

National CPI-U, all items, seasonally adjusted (CPIAUCSL) supplies the inflation adjustment. Freddie Mac's weekly 30-year fixed mortgage rate (MORTGAGE30US) supplies national financing context. CPI is averaged over all 12 months. Mortgage rates are averaged over all weekly observations dated in the calendar year, including holiday shifts. The PMMS methodology changed in November 2022, which limits a strict interpretation of small changes around that date.

### Methodology

All downloads are stored separately from processed data with their URL, retrieval timestamp and SHA-256 checksum. Census variable labels are checked for every year, and historical sequence-file columns are located using each release's official lookup. City geography is checked annually rather than inferred from a metropolitan label. Accounting checks reconcile occupied and vacant units to total units and employed and unemployed residents to the civilian labor force.

Real dollars equal nominal dollars multiplied by CPI in {latest} divided by CPI in the observation year. This removes broad national price inflation, but it does not measure the difference in living costs between these cities. Inflation cancels out of same-year ratios when both numerator and denominator are adjusted by the same index. The annualized rent-to-income proxy equals 12 times monthly median gross rent divided by annual median household income, expressed as a percentage. The home-value-to-income ratio divides the housing asset median by annual household income.

Direct renter burden uses B25070's categories: the count with gross rent at least 30% of income, divided by the total less ratios not computed. It is conditional on a computable ratio among renter-occupied units paying cash rent. Excluded households can differ systematically, so the dataset also reports the excluded share. Vacancy here means all vacant units divided by all housing units, not rental vacancy. Housing units per 1,000 residents is a stock-availability indicator, not a direct measure of units affordable to particular income groups.

Changes are computed only for adjacent observed calendar years. Standard ACS 1-year estimates were not released in 2020, and experimental estimates are not substituted. No graph interpolates the gap. Consequently, 2021 year-over-year growth is also unavailable. Endpoint changes compare 2010 with {latest} and are not annual growth rates. The statistical analysis separates levels from annual changes because trending series can correlate even without a stable economic relationship.

### Results

#### Nominal growth versus purchasing power

{table}

The nominal series answer how many dollars are reported in each year. The real series answer how much those dollars represent relative to a common national purchasing-power benchmark. Their difference matters when evaluating whether higher reported income represents greater household resources. These are changes in city medians, not average gains for residents who remained in the city. Migration, changes in household size, shifts in tenure and changes in the mix of available housing can all move medians.

![Real household income](../figures/real_income.png)

![Real monthly gross rent](../figures/real_rent.png)

{''.join(city_sections)}

![Annualized rent-to-income proxy](../figures/rent_income_proxy.png)

![Direct renter burden](../figures/direct_rent_burden.png)

#### Supply and financing context

Housing supply can ease price pressure in an economic model when other conditions are held fixed. The observed housing-stock-to-population ratio does not hold other conditions fixed. Developers can respond to strong demand at the same time that prices rise. The mix of new units, occupancy, household formation and income composition can also change. The supply scatterplot therefore supports a descriptive question about co-movement, not an estimate of a supply elasticity or of the effect of construction on rents.

![Housing units per resident](../figures/housing_supply.png)

The national mortgage average was {d.loc[d.year==2010,'mortgage_rate'].iloc[0]:.2f}% in 2010, {d.loc[d.year==2021,'mortgage_rate'].iloc[0]:.2f}% in 2021, and {d.loc[d.year==latest,'mortgage_rate'].iloc[0]:.2f}% in {latest}. A higher rate can raise the payment required to finance an otherwise identical purchase. This study does not construct a representative mortgage payment because down payments, taxes, insurance, credit quality and existing fixed-rate loans are not observed. A home-value-to-income ratio can therefore remain similar while conditions for a new financed purchase change materially.

### Statistical analysis

Descriptive tables report separate city distributions, counts, variability and endpoint changes. Full correlation tables distinguish pooled observations from city-specific relationships and levels from annual changes. The selected vacancy relationship is shown below. A pooled coefficient combines cross-city differences with changes over time. Differencing reduces simple level trends but amplifies measurement noise and does not remove omitted-variable or reverse-causality problems. Ratios sharing household income can also correlate mechanically.

{corr[['scope','form','n','pearson_r']].to_markdown(index=False, floatfmt='.3f')}

The primary model regresses the annualized rent-to-income proxy on the all-housing vacancy rate, an indicator for Minneapolis and a common linear trend beginning in 2010. It uses {info['n']} observations, {info['parameters']} parameters and HC3 standard errors. R-squared is {info['r_squared']:.3f}. Maximum non-intercept VIF is {info['max_vif']:.2f}; the design is full rank. The small panel favors one housing-market covariate rather than a large collection of supply, unemployment, mortgage-rate and trend variables. Model choice is based on interpretability and data size, not statistical significance.

{coef.to_markdown(index=False, floatfmt='.4f')}

The vacancy coefficient is {slope.coefficient:.3f} percentage points of the proxy per one percentage-point difference in vacancy, conditional on the city indicator and linear trend. Its HC3 standard error is {slope.robust_se:.3f}, and its 95% conditional interval is [{slope.ci_95_low:.3f}, {slope.ci_95_high:.3f}]. These estimates describe an association within this specification. They are not the change in affordability caused by making additional units vacant.

The interval {'includes' if slope.ci_95_low <= 0 <= slope.ci_95_high else 'does not include'} zero. The vacancy coefficient {'changes sign' if slope.coefficient * sensitivity.iloc[0].vacancy_coefficient < 0 else 'keeps its sign'} under the city-specific trend specification. These are conditional model results, not evidence of a causal effect.

Adding city-specific trends gives a vacancy coefficient of {sensitivity.iloc[0].vacancy_coefficient:.3f}. Excluding one observed year at a time gives coefficients ranging from {sensitivity.iloc[1:].vacancy_coefficient.min():.3f} to {sensitivity.iloc[1:].vacancy_coefficient.max():.3f}. These checks reveal dependence on trend assumptions and individual years. They are not independent replications. Residuals, leverage, Cook's distances, VIFs and the complete sensitivity table are saved with the model outputs for inspection.

{LIMITATION} In particular, consecutive estimates for the same city and observations in a common national year need not be independent. HC3 does not correct those forms of dependence. With only two cities, cluster-based inference is not reliable. The reported confidence intervals and p-values should be treated as conditional exploratory summaries rather than decisive hypothesis tests.

### Limitations

The strongest limitation is measurement alignment. Rent concerns cash-rent units, home values concern owner-occupied units and income concerns all households. Their medians are not matched observations. The median-based proxy can move differently from renter burden because the income distribution, tenure composition and joint distribution of rent and income change. None of these measures reveals which individual households were displaced, became owners or experienced financial distress.

Sampling uncertainty is another constraint. The project retains the Census margins of error but does not have the covariance information needed for a full treatment of derived ratios and longitudinal comparisons. Small annual changes should not be interpreted as precise economic shifts. Population-control updates and city boundary changes can also affect estimates. The 2020 gap prevents a direct annual account of the pandemic transition, and the absence of 2010 labor-force data shortens that context series.

The analysis also omits local housing quality, unit size, neighborhood access, taxes, transportation costs, wealth, credit constraints and commuting across municipal boundaries. National CPI is not a local price index, and a national mortgage average is not the rate offered to a particular borrower. Housing-unit counts do not describe construction flows or affordable-unit availability. No building-permit series is included. 

### Conclusion

The evidence shows why housing affordability should be examined through several measures. Real incomes and real housing costs can rise together, while their relative pace determines the median-based ratios. The direct renter burden measure adds distributional information that those ratios cannot supply. Housing availability and national mortgage rates help frame the economic setting, but this two-city annual panel cannot separate competing causal mechanisms.

A defensible extension would add more comparable cities, explicit housing-quality and tenure controls, and a research design tied to a clearly defined policy or supply shock. It would also incorporate survey uncertainty and distinguish new borrowers from existing owners. The current results support a descriptive portfolio study and motivate those questions; they do not establish that a specific policy improved or worsened affordability.

### Reproducibility and validation

Python produces the processed dataset, statistics, figures, formula-bearing Excel workbook and this report. Numerical prose is generated from the saved analytical results, with headline claims recorded in JSON. Unit and integration tests check formulas, accounting identities, missing years, raw checksums, Excel formulas and cached results, output files and application behavior. The final execution record is in [VALIDATION.md](../docs/VALIDATION.md).

R validation status: **{rstatus['status']}**. The R script independently recomputes the rent proxy, real income, OLS coefficients and HC3 standard errors and generates a separate chart. Its actual output is recorded in `data/results/r_validation.json`.

### Data sources

- [U.S. Census Bureau ACS summary files](https://www2.census.gov/programs-surveys/acs/summary_file/), ACS 1-year detailed tables, 2010–2019 and 2021–{latest}.
- [Census explanation of 2020 experimental data](https://www.census.gov/programs-surveys/acs/data/experimental-data.html).
- [BLS CPIAUCSL via FRED](https://fred.stlouisfed.org/series/CPIAUCSL), monthly observations, 2010–{latest}.
- [Freddie Mac MORTGAGE30US via FRED](https://fred.stlouisfed.org/series/MORTGAGE30US), weekly observations, 2010–{latest}.

Exact endpoints, retrieval dates, definitions and limitations appear in [DATA_SOURCES.md](../docs/DATA_SOURCES.md). This is a descriptive and exploratory student portfolio study; no peer review, causal identification or external supervision is claimed.
'''
    Path('report/report.md').write_text(report, encoding='utf-8')
    html = markdown.markdown(report, extensions=['tables','fenced_code'])
    css = 'body{font:16px/1.65 Georgia,serif;color:#243245;max-width:960px;margin:50px auto;padding:0 28px}h1,h2,h3,h4{font-family:Arial,sans-serif;line-height:1.25}h1{font-size:42px}h3{margin-top:42px}img{max-width:100%;height:auto}table{border-collapse:collapse;font:12px/1.5 Arial,sans-serif;width:100%;display:block;overflow:auto}th,td{padding:8px;border-bottom:1px solid #dde2e7;text-align:right}th{background:#edf2f5}a{color:#176b87}@media print{body{font-size:10pt;margin:0;max-width:none}h3{break-after:avoid}img{max-height:68mm;width:auto;display:block;margin:auto}table{font-size:8pt}p{orphans:3;widows:3}@page{size:A4;margin:17mm}}'
    Path('report/report.html').write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MarketLens research report</title><style>{css}</style></head><body>{html}</body></html>', encoding='utf-8')


def write_readme(statements, rstatus):
    path = Path('README.md')
    readme = path.read_text(encoding='utf-8')
    sections = {
        'findings': '\n'.join('- ' + line for line in statements),
        'r-status': f"Latest R validation: **{rstatus['status']}**.",
    }
    for name, content in sections.items():
        start, end = f'<!-- {name}:start -->', f'<!-- {name}:end -->'
        if readme.count(start) != 1 or readme.count(end) != 1:
            raise ValueError(f'README must contain one {name} marker pair.')
        before, rest = readme.split(start)
        _, after = rest.split(end)
        readme = before + start + '\n' + content + '\n' + end + after
    path.write_text(readme, encoding='utf-8')
