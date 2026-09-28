import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from src.excel_export import REQUIRED_SHEETS
from src.documentation import findings_text
from src.visualizations import FIGURES


def test_required_outputs():
    for path in ['README.md','docs/DATA_SOURCES.md','docs/DATA_DICTIONARY.md','docs/METHODOLOGY.md',
                 'report/report.md','report/report.html','R/validation_analysis.R','app.py',
                 'data/processed/city_year_data.csv','data/results/regression_sensitivity.csv']:
        assert Path(path).is_file() and Path(path).stat().st_size>100
    assert len(FIGURES)>=6
    for slug,*_ in FIGURES:
        assert (Path('figures')/(slug+'.png')).stat().st_size>10000


def test_workbook_sheets_tables_charts_and_formula_values():
    path='excel/MarketLens_Analysis.xlsx'
    formulas=load_workbook(path,data_only=False)
    values=load_workbook(path,data_only=True)
    assert formulas.sheetnames==REQUIRED_SHEETS
    assert formulas['City-Year Data'].freeze_panes=='C2'
    assert 'CityYearData' in formulas['City-Year Data'].tables
    assert len(formulas['Dashboard']._charts)==3
    d=pd.read_csv('data/processed/city_year_data.csv')
    derived=['annual_rent_to_income_pct','home_value_to_income','vacancy_rate','housing_units_per_1000',
             'unemployment_rate','direct_rent_burden_pct','median_household_income_real','median_gross_rent_real','median_home_value_real']
    for i,row in d.iterrows():
        for j,col in enumerate(derived,3):
            assert formulas['Affordability Metrics'].cell(i+7,j).value.startswith('=IF(')
            actual=values['Affordability Metrics'].cell(i+7,j).value
            if pd.isna(row[col]):
                assert actual in [None,'']
            else:
                np.testing.assert_allclose(actual,row[col],rtol=1e-12)
    for ws in values:
        for row in ws:
            assert all(c.data_type!='e' for c in row)
    formulas.close()
    values.close()


def test_numerical_claims_match_source_results():
    d=pd.read_csv('data/processed/city_year_data.csv')
    f=json.loads(Path('data/results/findings.json').read_text())
    for city, metrics in f.items():
        for col,values in metrics.items():
            actual=d[d.city==city][col].dropna()
            np.testing.assert_allclose(values['first_value'],actual.iloc[0])
            np.testing.assert_allclose(values['latest_value'],actual.iloc[-1])
            np.testing.assert_allclose(values['period_change_pct'],100*(actual.iloc[-1]/actual.iloc[0]-1))
    claims=json.loads(Path('data/results/headline_claims.json').read_text())
    assert claims==findings_text(f)
    for claim in claims:
        assert claim in Path('README.md').read_text(encoding='utf-8')
        assert claim in Path('report/report.md').read_text(encoding='utf-8')


def test_report_local_links():
    for file in [Path('README.md'),Path('report/report.md')]:
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
            if not link.startswith(('https://','http://','#')):
                assert (file.parent/link).exists(), (file,link)


def test_regression_and_r_status():
    info=json.loads(Path('data/results/regression_info.json').read_text())
    assert info['n']==28 and info['design_rank']==4
    assert 0<=info['r_squared']<=1
    coefficients=pd.read_csv('data/results/regression_coefficients.csv')
    assert coefficients.robust_se.gt(0).all()
    assert coefficients.p_value.between(0,1).all()
    status=json.loads(Path('data/results/r_validation.json').read_text())
    assert status['status'] in ['passed','unavailable']
    if status['status']=='passed':
        r=pd.read_csv('data/results/r_regression_coefficients.csv')
        np.testing.assert_allclose(r.coefficient,coefficients.coefficient,atol=1e-8)
        np.testing.assert_allclose(r.robust_se,coefficients.robust_se,atol=1e-8)
