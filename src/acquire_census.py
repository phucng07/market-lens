"""Acquire ACS 1-year summary files and validate every selected variable/year."""
import argparse
import csv
import io
import json
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import requests
from .config import CITIES, TABLES, VARIABLES, RAW, PROCESSED, SF, START_YEAR, make_directories
from .fetch import fetch, links


def discover_latest(offline=False):
    selection = RAW / 'release_selection.json'
    if selection.exists():
        return json.loads(selection.read_text())['latest_year']
    if offline:
        raise FileNotFoundError('No cached release selection. Run online acquisition first.')
    candidates = sorted([int(u.rstrip('/').split('/')[-1]) for u in links(SF, 'catalog.html')
                         if re.search(r'/20\d\d/$', u)], reverse=True)
    checked = []
    for year in candidates:
        if year > datetime.now().year - 1 or year < 2022:
            continue
        url = f'{SF}{year}/table-based-SF/data/'
        try:
            children = links(url, f'census/{year}/data_index.html')
        except requests.HTTPError as error:
            if error.response.status_code != 404:
                raise
            checked.append({'year': year, 'one_year_files_listed': False})
            continue
        checked.append({'year': year, 'one_year_files_listed': any(u.endswith('/1YRData/') for u in children)})
        if checked[-1]['one_year_files_listed']:
            available = links(url + '1YRData/', f'census/{year}/tables_index.html')
            required = [f'{url}1YRData/acsdt1y{year}-{t.lower()}.dat' for t in TABLES]
            if all(u in available for u in required):
                selection.write_text(json.dumps({'latest_year': year, 'checked': checked,
                    'checked_utc': datetime.now(timezone.utc).isoformat(),
                    'rule': 'Newest listed complete ACS 1-year table set. Existing selection is frozen for reproducibility.'}, indent=2))
                return year
    raise RuntimeError('No complete recent ACS 1-year release discovered.')


def validate_metadata(year, offline=False):
    records = []
    for table in TABLES:
        if year == 2010 and table == 'B23025':
            continue  # Table introduced in 2011; retain missing labor values in 2010.
        url = f'https://api.census.gov/data/{year}/acs/acs1/groups/{table}.json'
        path = fetch(url, f'census/{year}/metadata/{table}.json', offline)
        variables = json.loads(path.read_text())['variables']
        for code, (name, expected) in VARIABLES.items():
            if not code.startswith(table + '_'):
                continue
            item = variables[code + 'E']
            terminal = item['label'].split('!!')[-1].strip(': ').lower()
            if expected.lower() not in terminal:
                raise ValueError(f'Unexpected Census definition {year} {code}: {item}')
            if code in ['B23025_004', 'B23025_005'] and terminal != expected.lower():
                raise ValueError(f'Incorrect employment category {year} {code}: {terminal}')
            if code + 'M' not in variables:
                raise ValueError(f'Missing margin-of-error field {year} {code}')
            records.append(dict(year=year, code=code + 'E', variable=name, label=item['label'],
                                concept=item.get('concept', table), metadata_url=url))
    return records


def sequence_year(year, offline=False):
    prefix = f'{SF}{year}/' + ('sequence-based-SF/' if year == 2021 else '')
    lookup_url = prefix + ('documentation/1_year/user_tools/' if year <= 2012 else 'documentation/user_tools/')
    choices = links(lookup_url, f'census/{year}/lookup_index.html', offline)
    matches = [u for u in choices if 'lookup' in u.lower() and u.lower().endswith('.txt')]
    if year >= 2013:
        matches = [u for u in matches if '1yr' in u.lower()]
    if len(matches) != 1:
        raise ValueError(f'Cannot uniquely identify sequence lookup: {matches}')
    path = fetch(matches[0], f'census/{year}/sequence_lookup.txt', offline)
    lookup = pd.read_csv(path, encoding='cp1252', dtype=str, na_values=['.']).fillna('')
    lookup = lookup.rename(columns={'seq': 'Sequence Number', 'position': 'Start Position'})
    lookup = lookup.apply(lambda column: column.str.strip())
    records = []
    for city, (state, abbrev) in CITIES.items():
        base = prefix + f'data/1_year_seq_by_state/{state}/'
        geo = fetch(base + f'g{year}1{abbrev}.csv', f'census/{year}/{abbrev}/geography.csv', offline)
        geo_rows = list(csv.reader(io.StringIO(geo.read_text(encoding='utf-8-sig', errors='replace'))))
        matches = [r for r in geo_rows if len(r) > 4 and r[2] == '160' and r[3] == '00'
                   and any(x in (f'{city} city', f'{city} city, {state}') for x in r)]
        if len(matches) != 1:
            raise ValueError(f'Expected one whole-city geography for {city} {year}, got {len(matches)}')
        geo_row = matches[0]
        geoid = next(x for x in geo_row if re.fullmatch(r'16000(?:00)?US\d{7}', x))
        digits = geoid.split('US')[1]
        record = dict(city=city, state=state, year=year, state_fips=digits[:2], place_fips=digits[2:],
                      geoid='1600000US' + digits, acs_available=True)
        sequences = {}
        for code, (name, _) in VARIABLES.items():
            table, line = code.split('_')
            header = lookup[(lookup['Table ID'] == table) & (lookup['Start Position'] != '')]
            if year == 2010 and table == 'B23025' and header.empty:
                record[name] = None
                record[name + '_moe'] = None
                continue
            if len(header) != 1:
                raise ValueError(f'Unexpected split or missing table {table} {year}')
            header = header.iloc[0]
            seq = int(header['Sequence Number'])
            index = int(header['Start Position']) - 1 + int(line) - 1
            if seq not in sequences:
                filename = f'{year}1{abbrev}{seq:04d}000.zip'
                archive = fetch(base + filename, f'census/{year}/{abbrev}/{filename}', offline)
                content = {}
                with zipfile.ZipFile(archive) as z:
                    for kind in ('e', 'm'):
                        member = next(n for n in z.namelist() if Path(n).name.startswith(f'{kind}{year}'))
                        rows = csv.reader(io.StringIO(z.read(member).decode('utf-8-sig')))
                        found = [r for r in rows if r[5].zfill(7) == geo_row[4].zfill(7)]
                        if len(found) != 1:
                            raise ValueError(f'Invalid sequence/geography join {filename} {city}')
                        content[kind] = found[0]
                sequences[seq] = content
            record[name] = sequences[seq]['e'][index]
            record[name + '_moe'] = sequences[seq]['m'][index]
        records.append(record)
    return records


def table_year(year, offline=False):
    base = f'{SF}{year}/table-based-SF/'
    geo = fetch(base + f'documentation/Geos{year}1YR.txt', f'census/{year}/geography.txt', offline)
    geography = pd.read_csv(geo, sep='|', dtype=str, encoding='utf-8-sig')
    records = []
    for city, (state, _) in CITIES.items():
        match = geography[(geography['NAME'] == f'{city} city, {state}') & (geography.SUMLEVEL == '160')
                          & (geography.COMPONENT == '00')]
        if len(match) != 1:
            raise ValueError(f'Expected unique whole-city record: {city}, {year}')
        row = match.iloc[0]
        records.append(dict(city=city, state=state, year=year, state_fips=row.STATE, place_fips=row.PLACE,
                            geoid=row.GEO_ID, acs_available=True))
    for table in TABLES:
        url = base + f'data/1YRData/acsdt1y{year}-{table.lower()}.dat'
        path = fetch(url, f'census/{year}/{table}.dat', offline)
        frame = pd.read_csv(path, sep='|', dtype=str).set_index('GEO_ID')
        if not frame.index.is_unique:
            raise ValueError(f'Duplicate GEO_ID in {path}')
        for record in records:
            for code, (name, _) in VARIABLES.items():
                if code.startswith(table + '_'):
                    number = code.split('_')[1]
                    record[name] = frame.loc[record['geoid'], f'{table}_E{number}']
                    record[name + '_moe'] = frame.loc[record['geoid'], f'{table}_M{number}']
    return records


def acquire(offline=False):
    make_directories()
    latest = discover_latest(offline)
    years = [y for y in range(START_YEAR, latest + 1) if y != 2020]

    def one(year):
        metadata = validate_metadata(year, offline)
        records = table_year(year, offline) if year >= 2022 else sequence_year(year, offline)
        print(f'Validated and extracted ACS {year}', flush=True)
        return records, metadata

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, years))
    rows = [r for records, _ in results for r in records]
    metadata = [r for _, records in results for r in records]
    pd.DataFrame(metadata).to_csv(PROCESSED / 'validated_census_variables.csv', index=False)
    frame = pd.DataFrame(rows).sort_values(['city', 'year'])
    frame.to_csv(PROCESSED / 'census_extracted.csv', index=False)
    return frame, latest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true')
    acquire(parser.parse_args().offline)
