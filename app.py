"""MarketLens local research application. Launch with streamlit run app.py."""
import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from src.visualizations import COLORS
from src.regression import LIMITATION

st.set_page_config(page_title='MarketLens | Housing affordability', page_icon='🏘️', layout='wide')
st.title('MarketLens')
st.caption('Housing affordability in Madison and Minneapolis · An exploratory economics study')
required_files = ['data/processed/city_year_data.csv', 'data/processed/source_catalog.csv',
                  'data/processed/data_dictionary.csv', 'data/results/headline_claims.json',
                  'data/results/summary_statistics.csv', 'data/results/correlations.csv',
                  'data/results/regression_info.json', 'data/results/regression_coefficients.csv',
                  'data/results/regression_sensitivity.csv', 'docs/METHODOLOGY.md',
                  'excel/MarketLens_Analysis.xlsx', 'data/results/pipeline_run.json']
missing_files = [name for name in required_files if not Path(name).is_file()]
if missing_files:
    st.error('Analysis files are missing. Run python -m src.pipeline --offline from the repository root. Missing: ' + ', '.join(missing_files))
    st.stop()
if json.loads(Path('data/results/pipeline_run.json').read_text())['status'] != 'completed':
    st.error('The last pipeline run did not finish. Rerun python -m src.pipeline --offline before opening the analysis.')
    st.stop()


@st.cache_data
def load_data(version):
    return pd.read_csv('data/processed/city_year_data.csv', dtype={'state_fips': str, 'place_fips': str})


d = load_data(Path('data/processed/city_year_data.csv').stat().st_mtime_ns)
latest = int(d.year.max())
base_year = int(d.real_dollar_base_year.iloc[0])
st.sidebar.header('Explore the evidence')
cities = st.sidebar.multiselect('Cities', sorted(d.city.unique()), default=sorted(d.city.unique()))
years = st.sidebar.slider('Years', int(d.year.min()), latest, (int(d.year.min()), latest))
dollars = st.sidebar.radio('Dollar basis', [f'Real ({base_year} USD)', 'Nominal USD'])
st.sidebar.caption('2020 ACS is missing. Lines break at the gap; 2021 annual growth is also unavailable.')
if not cities:
    st.info('Select at least one city to view the study.')
    st.stop()
filtered = d[d.city.isin(cities) & d.year.between(*years)]
suffix = 'real' if dollars.startswith('Real') else 'nominal'
money_unit = f'{base_year} USD' if suffix == 'real' else 'current-year USD'


def chart(metric, title, unit, national=False):
    frame = filtered.drop_duplicates('year') if national else filtered
    fig = px.line(frame, x='year', y=metric, color=None if national else 'city', markers=True,
                  color_discrete_map=COLORS, labels={'year':'Year', metric:unit, 'city':'City'}, title=title)
    fig.update_traces(connectgaps=False)
    fig.update_layout(template='plotly_white', height=360, margin=dict(l=15,r=20,t=65,b=30), legend=dict(orientation='h',y=1.12))
    st.plotly_chart(fig, width='stretch')
    st.caption('Source: Freddie Mac via FRED, national annual averages.' if national else
               'Source: U.S. Census Bureau ACS 1-year; BLS CPI via FRED for real dollars. Annual point estimates have sampling error.')


overview, affordability, housing, context, statistics, methods = st.tabs(
    ['Overview','Affordability trends','Housing & population','Economic context','Statistical analysis','Methodology & sources'])
with overview:
    st.subheader('Did household resources keep pace with housing costs?')
    st.write('Compare rent, income and home values alongside housing availability. The study uses incorporated-city ACS estimates and national economic context. It describes associations and does not identify policy effects.')
    available = filtered[filtered.acs_available]
    if available.empty:
        st.info('No standard ACS observations exist in the selected period. National context remains available.')
    else:
        endpoint = int(available.year.max())
        st.caption(f'Latest observed year within selection: {endpoint}')
        for city in cities:
            row = available[(available.city==city) & (available.year==endpoint)].iloc[0]
            st.markdown(f'**{city}**')
            a,b,c,e = st.columns(4)
            a.metric(f'Monthly rent ({money_unit})', f"${row['median_gross_rent_'+suffix]:,.0f}")
            b.metric('Annualized rent-to-income proxy', f'{row.annual_rent_to_income_pct:.2f}%')
            c.metric('Home value / annual income', f'{row.home_value_to_income:.2f}×')
            e.metric('Direct renter burden', f'{row.direct_rent_burden_pct:.1f}%')
    st.subheader(f'Full-period findings: {int(d.year.min())}–{latest}')
    for claim in json.loads(Path('data/results/headline_claims.json').read_text()):
        st.write(claim)
    st.info('The annualized rent-to-income proxy divides two population medians. Direct renter burden is the share with rent at least 30% of income among cash-rent units with a computable ratio.')
    a,b = st.columns(2)
    a.download_button('Download city-year CSV', Path('data/processed/city_year_data.csv').read_bytes(), 'city_year_data.csv', 'text/csv')
    b.download_button('Download analytical workbook', Path('excel/MarketLens_Analysis.xlsx').read_bytes(), 'MarketLens_Analysis.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
with affordability:
    a,b = st.columns(2)
    with a:
        chart('median_household_income_'+suffix, 'Household income', f'Annual income ({money_unit})')
        chart('annual_rent_to_income_pct', 'Did rent outpace income?', 'Annualized rent-to-income proxy (%)')
        chart('home_value_to_income', 'Home values relative to income', 'Times annual household income')
    with b:
        chart('median_gross_rent_'+suffix, 'Gross rent', f'Monthly gross rent ({money_unit})')
        chart('median_home_value_'+suffix, 'Owner-occupied home values', f'Median asset value ({money_unit})')
        chart('direct_rent_burden_pct', 'Direct renter cost burden', 'Computable cash-rent units paying ≥30% of income (%)')
    st.caption('Ratios are unchanged by applying the same CPI conversion to numerator and denominator. Home values are not mortgage payments.')
with housing:
    a,b=st.columns(2)
    with a:
        chart('population','Population','Residents')
        chart('housing_units_per_1000','Did housing keep pace with residents?','Housing units per 1,000 residents')
        chart('population_yoy_pct','Population growth','Prior-calendar-year change (%)')
    with b:
        chart('housing_units','Housing stock','Housing units')
        chart('vacancy_rate','All-housing vacancy','Vacant / total housing units (%)')
        chart('housing_units_yoy_pct','Housing-stock growth','Prior-calendar-year change (%)')
    st.write('Housing stock includes occupied and vacant units. Vacancy includes multiple reasons and is not the rental vacancy rate. A larger stock per resident does not identify the effect of construction on prices.')
with context:
    a,b=st.columns(2)
    with a:
        chart('unemployment_rate','ACS labor-market conditions','Unemployed / civilian labor force (%)')
    with b:
        chart('mortgage_rate','National mortgage financing','30-year fixed mortgage annual average (%)',national=True)
    st.caption('B23025 is unavailable for 2010. Mortgage rates are national; the PMMS methodology changed in November 2022.')
    fig=px.scatter(filtered,x='housing_units_per_1000',y='annual_rent_to_income_pct',color='city',hover_data=['year'],color_discrete_map=COLORS,
                   labels={'housing_units_per_1000':'Housing units per 1,000 residents','annual_rent_to_income_pct':'Annualized rent-to-income proxy (%)','city':'City'})
    st.plotly_chart(fig,width='stretch')
    st.caption('Source: ACS 1-year. Association only; city differences, household composition and time trends can affect both measures.')
with statistics:
    st.subheader('Full-study statistics')
    st.caption('These tables use the complete study period and both cities, independent of sidebar filters. Re-estimating on short selections could create unstable results.')
    st.dataframe(pd.read_csv('data/results/summary_statistics.csv'),hide_index=True)
    scope=st.selectbox('Correlation scope',['Pooled','Madison','Minneapolis'])
    form=st.radio('Correlation form',['levels','annual_changes'],horizontal=True)
    correlations=pd.read_csv('data/results/correlations.csv')
    c=correlations[(correlations.scope==scope)&(correlations.form==form)]
    st.dataframe(c.pivot(index='variable_x',columns='variable_y',values='pearson_r').round(3))
    with st.expander('Pairwise observation counts'):
        st.dataframe(c.pivot(index='variable_x',columns='variable_y',values='n'))
    st.warning('Correlation is not causation. Pooled levels mix city differences with time trends. Ratios can share denominators mechanically.')
    info=json.loads(Path('data/results/regression_info.json').read_text())
    st.markdown('**Exploratory OLS with HC3 standard errors**')
    st.code(info['formula'],language=None)
    st.write(f"Observations: {info['n']} · R-squared: {info['r_squared']:.3f} · Maximum VIF: {info['max_vif']:.2f}")
    st.dataframe(pd.read_csv('data/results/regression_coefficients.csv'),hide_index=True)
    st.write(LIMITATION)
    with st.expander('Trend and year-exclusion sensitivity'):
        st.dataframe(pd.read_csv('data/results/regression_sensitivity.csv'),hide_index=True)
with methods:
    st.markdown(Path('docs/METHODOLOGY.md').read_text(encoding='utf-8'))
    st.subheader('Source catalog')
    st.dataframe(pd.read_csv('data/processed/source_catalog.csv'),hide_index=True)
    st.subheader('Processed variable definitions')
    st.dataframe(pd.read_csv('data/processed/data_dictionary.csv'),hide_index=True)
    st.caption('Exact download URLs and retrieval dates are recorded in data/processed/source_manifest.csv. Read report/report.html for the complete research narrative.')
