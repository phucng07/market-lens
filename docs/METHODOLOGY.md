# Methodology

## Scope and identification

The research unit is an incorporated city-year. There are 28 observed city-years and two explicit 2020 gap rows over 2010–2024. Official annual geography files identify the cities by name and supply their FIPS codes. Each selected estimate and its 90% margin of error is validated against the same year's table metadata. Sequence offsets are taken from official lookup files, not guessed from a different release. Occupied plus vacant units reconcile to total units; employed plus unemployed reconcile to the civilian labor force.

## Cleaning and annualization

Negative ACS sentinel values and nonnumeric suppressed cells become missing. Raw bytes stay unchanged and are checked against SHA-256 sidecars whenever reused. No missing value is replaced with zero. B23025 labor data are unavailable in 2010. Standard 2020 ACS estimates are unavailable. National data remain observed in 2020.

CPI is the mean of 12 monthly CPIAUCSL observations. Mortgage rates are the unweighted mean of 52/53 weekly dated observations, with holiday shifts respected. These are annual averages, not December levels. Both are national measures. The reference year is 2024, the latest complete common analysis year.

## Formulas and interpretation

- Real value = nominal value × CPI_2024 / CPI_year.
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

annual_rent_to_income_pct ~ vacancy_rate + Minneapolis indicator + (year - 2010)

OLS uses 28 city-years and 4 coefficients including an intercept, with HC3 heteroskedasticity-robust standard errors and Student-t confidence intervals using residual degrees of freedom. Vacancy is selected as one economically interpretable housing-market covariate; city intercepts and a common linear time trend absorb baseline differences and broad drift. Income is not added as a predictor because it is already the dependent variable's denominator. Supply, unemployment and mortgage rates remain descriptive to avoid overfitting a two-city panel or stacking highly trending variables.

The design matrix has rank 4; maximum non-intercept VIF is 2.59, and the unscaled condition number is 50.35. Complete-case exclusions among available ACS rows: 0. Diagnostics retain fitted values, residuals, leverage and Cook's distances. A city-specific trend model and exclusion of each observed year assess sensitivity, without selecting whichever specification yields the smallest p-value.

Exploratory association, not a causal effect. ACS sampling error is not propagated. HC3 handles heteroskedasticity but not serial or shared-year dependence. Two cities are insufficient for reliable city-clustered inference. Common trends, omitted variables and endogenous vacancy limit interpretation. A high R-squared does not solve these problems. P-values and intervals are conditional model summaries and should not support strong population inference. No policy treatment or instrument supplies causal identification.

## Uncertainty and reproducibility

The published 90% MOEs are retained, but full survey covariance information is unavailable. Derived-ratio uncertainty and changes in medians are not formally tested. Annual point-estimate changes can reflect survey noise, migration, household composition or changing housing quality. ACS population controls and boundary changes add comparability limitations.

Run from the repository root. The default acquisition uses immutable cached files and discovers a latest release only when no selection exists. `--offline` forbids downloading. To study a newer vintage, preserve or rename the entire existing `data/raw` directory before starting a new acquisition; do not overwrite its files. Downstream outputs will be regenerated. Requirements are bounded in requirements.txt and exact executed versions in requirements-lock.txt.

R independently recomputes the rent proxy, real income, OLS coefficients and HC3 covariance using base R, and creates a separate figure. Execution status: **passed**. Details are in `data/results/r_validation.json`.
