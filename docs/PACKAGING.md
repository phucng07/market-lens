# Publication package verification

Prepared on 2026-09-28 from the existing MarketLens project. The original project was left unchanged.

## Included

Python source and tests, Streamlit app, R validation, dependency files, research documentation, Markdown and HTML reports, thirteen chart images, analytical Excel workbook, public raw and processed data, and statistical results. Working relative paths and the existing `report/` directory name were preserved.

## Excluded

Local Git history and remotes, the Python virtual environment, caches, temporary visual-review files, runtime logs, and personal university application documents.

## Checks at initial packaging

- The complete offline pipeline successfully rebuilt all analysis outputs from cached official responses.
- The rebuilt dataset contains 30 city-year grid rows, of which 28 have ACS observations; 2020 remains missing.
- Base R validation passed for the rent-to-income proxy, inflation calculation, OLS coefficients, and HC3 standard errors.
- All 20 pytest tests passed, including numerical claims, raw checksums, report links, workbook structure/formulas, and Streamlit application controls.
- A headless Streamlit server returned `ok` from its health endpoint and was stopped after the check.
- Automated scanning found no private local user paths or recognizable user credential patterns in authored files. Matches in preserved FRED source HTML are source-site chart link parameters, not locally supplied credentials.

These results describe the initial packaging run. Current checks are recorded in [VALIDATION.md](VALIDATION.md). Validation used an existing Python 3.13.1 environment, which is not included in this folder. A fresh dependency installation, new visual inspection, and Microsoft Excel desktop test were not part of packaging.

The package is the completed city-level study, not the earlier proposed student-budget scenario application. No new research findings or student-specific measurements were invented during packaging.
