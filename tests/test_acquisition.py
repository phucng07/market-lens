import pandas as pd
import pytest
import requests
from src import acquire_census, acquire_fred, fetch


def test_latest_release_skips_unpublished_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(acquire_census, 'RAW', tmp_path)
    base = acquire_census.SF

    def directory_links(url, relative, offline=False):
        if url == base:
            return [base+'2023/', base+'2024/']
        if '/2024/' in url:
            response = requests.Response()
            response.status_code = 404
            raise requests.HTTPError(response=response)
        if url.endswith('/1YRData/'):
            return [url+f'acsdt1y2023-{table.lower()}.dat' for table in acquire_census.TABLES]
        return [url+'1YRData/']

    monkeypatch.setattr(acquire_census, 'links', directory_links)
    assert acquire_census.discover_latest() == 2023


def test_cpi_requires_every_month(tmp_path, monkeypatch):
    definition = tmp_path/'definition.html'
    definition.write_text('Consumer Price Index Seasonally Adjusted Monthly')
    data = tmp_path/'cpi.csv'
    dates = ['2024-01-01', '2024-01-15'] + [f'2024-{month:02d}-01' for month in range(2,12)]
    pd.DataFrame({'observation_date': dates, 'CPIAUCSL': [300]*12}).to_csv(data,index=False)
    monkeypatch.setattr(acquire_fred, 'START_YEAR', 2024)
    monkeypatch.setattr(acquire_fred, 'fetch', lambda url, relative, offline=False: definition if relative.endswith('.html') else data)
    with pytest.raises(ValueError, match='Incomplete calendar years'):
        acquire_fred.acquire(2024, offline=True)


def test_missing_cache_sidecar_has_recovery_message(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, 'RAW', tmp_path)
    (tmp_path/'source.csv').write_text('value\n1\n')
    with pytest.raises(FileNotFoundError, match='checksum sidecar'):
        fetch.fetch('https://example.org/source.csv', 'source.csv', offline=True)
