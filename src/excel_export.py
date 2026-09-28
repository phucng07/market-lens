"""Reproducible analytical workbook with visible formulas and cached results."""
from pathlib import Path
import json
import pandas as pd
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name
from openpyxl import load_workbook
from .config import RESULTS

REQUIRED_SHEETS = ['Dashboard', 'City-Year Data', 'Madison', 'Minneapolis', 'Affordability Metrics',
                   'Summary Statistics', 'Regression Results', 'Data Sources', 'Data Dictionary']


def export(d, dictionary, sources):
    path = Path('excel/MarketLens_Analysis.xlsx')
    with xlsxwriter.Workbook(path) as book:
        book.set_properties({'title': 'MarketLens housing affordability', 'author': 'MarketLens',
                             'comments': 'Official ACS and FRED data. Exploratory economic analysis.'})
        body = book.add_format({'font_name': 'Arial', 'font_size': 10, 'valign': 'vcenter'})
        title = book.add_format({'font_name': 'Arial', 'font_size': 16, 'bold': True, 'font_color': '#23374d'})
        header = book.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True, 'bg_color': '#23374d',
                                'font_color': 'white', 'text_wrap': True, 'valign': 'vcenter'})
        numeric = book.add_format({'font_name': 'Arial', 'font_size': 10, 'num_format': '#,##0.00', 'valign': 'vcenter'})
        dollar = book.add_format({'font_name': 'Arial', 'font_size': 10, 'num_format': '$#,##0', 'valign': 'vcenter'})
        count = book.add_format({'font_name': 'Arial', 'font_size': 10, 'num_format': '#,##0'})
        note = book.add_format({'font_name': 'Arial', 'font_size': 10, 'font_color': '#526173', 'text_wrap': True, 'valign': 'top'})
        sheets = {name: book.add_worksheet(name) for name in REQUIRED_SHEETS}
        for sheet in sheets.values():
            sheet.hide_gridlines(2)
            sheet.set_default_row(20)
            sheet.set_column(0, 20, 18, body)

        def table(sheet, frame, start=0, name=None):
            data = frame.astype(object).where(frame.notna(), None).values.tolist()
            sheet.add_table(start, 0, start + len(frame), len(frame.columns)-1,
                            {'name': name or sheet.name.replace(' ', '').replace('-', '') + 'Table',
                             'columns': [{'header': str(c) if sheet.name=='City-Year Data' else str(c).replace('_',' '), 'header_format': header} for c in frame],
                             'data': data, 'style': 'Table Style Medium 2'})
            sheet.set_row(start, 46)
            for i, column in enumerate(frame):
                fmt = dollar if 'median_' in column and ('nominal' in column or 'real' in column) and not column.endswith('_pct') else numeric
                if column in ['year', 'real_dollar_base_year']:
                    fmt = book.add_format({'num_format': '0', 'font_name': 'Arial', 'font_size': 10})
                if column in ['population', 'housing_units', 'n'] or column.endswith('_units'):
                    fmt = count
                if sheet.name == 'Regression Results':
                    fmt = book.add_format({'font_name':'Arial','font_size':10,'num_format':'0.0000E+00' if column=='p_value' else '0.0000'})
                width = 22 if len(column) > 18 else 18
                if sheet.name=='City-Year Data':
                    width = max(width, min(48, len(column)+2))
                if frame[column].dtype.kind == 'b':
                    fmt = body
                if frame[column].dtype.kind in 'biufc':
                    sheet.set_column(i, i, width, fmt)
                else:
                    sheet.set_column(i, i, min(65, max(18, max([len(str(x)) for x in frame[column].head(40)] + [len(column)]) + 2)), body)
            sheet.freeze_panes(start + 1, min(2, len(frame.columns)))

        table(sheets['City-Year Data'], d, name='CityYearData')
        fields = ['year', 'median_household_income_real', 'median_gross_rent_real', 'median_home_value_real',
                  'annual_rent_to_income_pct', 'home_value_to_income', 'housing_units_per_1000', 'vacancy_rate',
                  'direct_rent_burden_pct', 'population', 'housing_units']
        findings = json.loads((RESULTS / 'findings.json').read_text())
        for city in ['Madison', 'Minneapolis']:
            ws = sheets[city]
            ws.write('A2', f'{city}: housing and income trends', title)
            ws.merge_range('A4:D5', f"Real income changed {findings[city]['median_household_income_real']['period_change_pct']:.1f}% over the study period.", note)
            ws.set_row(3, 32)
            table(ws, d[d.city == city][fields], start=6)
            note_row = 8 + len(d[d.city == city])
            ws.merge_range(note_row, 0, note_row+1, 5, 'Real dollars use the latest complete study year. Blank 2020 values are intentional.', note)
            ws.set_row(note_row, 35)
        ws = sheets['Affordability Metrics']
        ws.write('A2', 'Affordability calculations', title)
        ws.merge_range('A4:K4', 'Percent values use 20 for 20%. Formulas link to City-Year Data; blank inputs stay blank.', note)
        ws.set_row(3, 34)
        derived = ['annual_rent_to_income_pct', 'home_value_to_income', 'vacancy_rate', 'housing_units_per_1000',
                   'unemployment_rate', 'direct_rent_burden_pct', 'median_household_income_real',
                   'median_gross_rent_real', 'median_home_value_real']
        table(ws, d[['city', 'year'] + derived], start=5)
        lookup = {col: xl_col_to_name(i) for i, col in enumerate(d.columns)}
        for i, row in d.iterrows():
            sr = i + 2
            def ref(col):
                return f"'City-Year Data'!{lookup[col]}{sr}"
            pairs = [('median_gross_rent_nominal', 'median_household_income_nominal', 1200),
                     ('median_home_value_nominal', 'median_household_income_nominal', 1),
                     ('vacant_housing_units', 'total_housing_units', 100), ('housing_units', 'population', 1000),
                     ('unemployed', 'civilian_labor_force', 100), ('rent_burden_30_plus_units', 'rent_burden_computable_units', 100)]
            for j, (num, den, scale) in enumerate(pairs):
                a, b = ref(num), ref(den)
                formula = f'=IF(OR({a}="",{b}="",{b}<=0),"",{a}/{b}*{scale})'
                value = row[derived[j]]
                ws.write_formula(i+6, j+2, formula, numeric, '' if pd.isna(value) else float(value))
            base_i = d.index[d.year == d.year.max()][0] + 2
            base = f"'City-Year Data'!${lookup['cpi']}${base_i}"
            for j, field in enumerate(['median_household_income', 'median_gross_rent', 'median_home_value']):
                a, cpi = ref(field+'_nominal'), ref('cpi')
                formula = f'=IF(OR({a}="",{cpi}="",{cpi}<=0),"",{a}*{base}/{cpi})'
                value = row[field+'_real']
                ws.write_formula(i+6, j+8, formula, dollar, '' if pd.isna(value) else float(value))
        ws.merge_range(len(d)+9, 0, len(d)+10, 6, 'Proxy = 12 × median monthly gross rent / median annual household income × 100. Different populations.', note)
        ws.merge_range(len(d)+12, 0, len(d)+13, 6, 'Direct burden = B25070 categories >=30% / (total minus not computed) × 100.', note)
        table(sheets['Summary Statistics'], pd.read_csv(RESULTS/'summary_statistics.csv'))
        ws = sheets['Regression Results']
        info = json.loads((RESULTS/'regression_info.json').read_text())
        ws.write('A2', 'Exploratory regression: annualized rent-to-income proxy', title)
        ws.write('A4', f"OLS with HC3 standard errors; n = {info['n']}; R-squared = {info['r_squared']:.3f}")
        table(ws, pd.read_csv(RESULTS/'regression_coefficients.csv'), start=6)
        ws.merge_range('A14:F17', info['limitation'], note)
        ws.merge_range('A19:F20', 'Vacancy coefficient: percentage-point proxy difference per 1 percentage-point vacancy difference.', note)
        table(ws, pd.read_csv(RESULTS/'regression_vif.csv'), start=22, name='VIFResults')
        table(sheets['Data Sources'], sources)
        sheets['Data Sources'].set_column('D:F', 60, note)
        for row in range(1, len(sources)+1):
            sheets['Data Sources'].set_row(row, 60)
        table(sheets['Data Dictionary'], dictionary)
        sheets['Data Dictionary'].set_column('C:C', 95, note)
        for row in range(1, len(dictionary)+1):
            sheets['Data Dictionary'].set_row(row, 32)
        ws = sheets['Dashboard']
        ws.set_tab_color('#23374d')
        ws.set_column('A:A', 33)
        ws.set_column('B:H', 16)
        ws.write('A2', 'MarketLens', title)
        ws.merge_range('A3:H4', f'Madison and Minneapolis | {int(d.year.min())}–{int(d.year.max())} | 2020 ACS gap', note)
        ws.set_row(2, 30)
        for col, value in enumerate(['Latest indicator', 'Madison', 'Minneapolis']):
            ws.write(5, col, value, header)
        dashboard_metrics = [('Annual income (USD)', 'median_household_income_nominal'),
                             ('Monthly gross rent (USD)', 'median_gross_rent_nominal'),
                             ('Home value (USD)', 'median_home_value_nominal'),
                             ('Annualized rent/income proxy (%)', 'annual_rent_to_income_pct'),
                             ('Home value / income (times)', 'home_value_to_income'),
                             ('Direct renter burden (%)', 'direct_rent_burden_pct')]
        for j, (label, metric) in enumerate(dashboard_metrics, 6):
            ws.write(j, 0, label, note)
            ws.set_row(j, 30)
            for k, city in enumerate(['Madison', 'Minneapolis'], 1):
                ix = d.index[(d.city == city) & (d.year == d.year.max())][0]
                ws.write_formula(j, k, f"='City-Year Data'!{lookup[metric]}{ix+2}", dollar if j<9 else numeric, float(d.loc[ix, metric]))
        ws.merge_range('E6:H12', 'The annualized rent-to-income proxy divides two medians for different populations. Direct burden measures renters with computable rent/income ratios. Home values do not measure mortgage payments. All figures are descriptive.', note)
        charts = [('Annualized rent-to-income proxy (%)', 4), ('Home value / income (times)', 5),
                  ('Real monthly gross rent (USD)', 2)]
        for ix, (label, col) in enumerate(charts):
            chart = book.add_chart({'type': 'line'})
            for city, color in [('Madison', '#176b87'), ('Minneapolis', '#b65b2a')]:
                n = len(d[d.city == city])
                chart.add_series({'name': city, 'categories': [city, 7, 0, 6+n, 0], 'values': [city, 7, col, 6+n, col],
                                  'line': {'color': color, 'width': 2}, 'marker': {'type': 'circle', 'size': 3}})
            chart.set_title({'name': label})
            chart.set_x_axis({'name': 'Year', 'num_font': {'size': 9}})
            chart.set_y_axis({'name': label, 'num_font': {'size': 9}})
            chart.set_legend({'position': 'bottom'})
            chart.show_blanks_as('gap')
            chart.set_size({'width': 690, 'height': 320})
            ws.insert_chart(14 + ix*17, 0, chart)
        ws.merge_range('A68:H70', 'Sources: ACS 1-year and FRED. See Data Sources and Data Dictionary. Rebuild with python -m src.pipeline --offline.', note)
        ws.set_landscape()
        ws.fit_to_pages(1, 0)
    loaded = load_workbook(path, read_only=False, data_only=False)
    assert loaded.sheetnames == REQUIRED_SHEETS
    assert loaded['City-Year Data'].tables
    assert len(loaded['Dashboard']._charts) == 3
    loaded.close()
    return path
