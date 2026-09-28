# Validation record

Final audit: 2026-09-26 UTC.

- Python 3.13.1; exact executed packages are pinned in requirements-lock.txt. The portfolio setup passed `pip check` with no broken requirements.
- Official acquisition completed for ACS 2010–2019 and 2021–2024 and FRED 2010–2024. All 322 raw-response checksums pass.
- Full offline pipeline successfully rebuilt cleaning, metrics, statistics, regressions, figures, Excel, R outputs and documentation.
- **20 pytest tests passed** with no failures, errors or skips. Evidence: data/results/pytest.xml.
- Tests cover formulas, inflation, cities, year uniqueness, accounting identities, positive values, percentage ranges, missing years, annual national averages, raw checksums, exhaustive dictionary, numerical headlines, local links and output integrity.
- Streamlit AppTest exercised all six tabs, nominal/real choice, city filtering, a 2020-only selection and an empty city selection without exceptions.
- A real headless localhost Streamlit server returned HTTP 200 with `ok`. It was stopped after validation. Evidence: data/results/streamlit_smoke.json.
- Excel reopened with openpyxl in formula and cached-value modes. All nine sheets, the CityYearData table, frozen identifiers/headers, three native charts, calculated metrics and missing-row handling pass. No Excel error cells were found.
- All nine Excel sheet opening views were rendered and inspected. Crowded headings and over-rounded regression cells were corrected. Twelve Python figures and the R figure were visually inspected, including the 2020 breaks.
- An independent spreadsheet engine imported and recalculated the workbook. Doubling the first rent input doubled the linked rent proxy from 20.1473033975 to 40.2946067950 in a disposable in-memory copy. The original workbook was unchanged. Microsoft Excel desktop recalculation was not tested.
- R validation **passed**. Actual execution output: null device            1  PASS: proxy error 3.55e-15; inflation error 1.46e-11; OLS coefficient error 9.44e-15; HC3 SE error 9.99e-16. Evidence: data/results/r_validation.json. The portfolio's executed R version was 4.4.1.
- Numerical claims were traced to findings.json, summary_statistics.csv, regression outputs and the underlying processed observations. The report discusses the different directions of the median-based proxy and direct renter burden explicitly.
- Repository scans for unfinished markers were reviewed. Remaining statistical terminology and unmodified official/instruction text are legitimate. No invented observations enter the analysis.

Re-run the evidence from the repository root:

```powershell
python -m src.pipeline --offline
python -m pytest -q --junitxml=data/results/pytest.xml
python -m src.smoke_test
python -m src.audit
```

The audit command checks saved execution evidence. Run the preceding commands to refresh that evidence after changes. Visual reviews are recorded human/agent inspections, not a claim of automated desktop-Excel testing.
