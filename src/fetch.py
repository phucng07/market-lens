"""Immutable, checksummed public downloads with explicit offline operation."""
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urljoin
from urllib.request import urlopen
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .config import RAW

SESSION = requests.Session()
SESSION.headers['User-Agent'] = 'MarketLens academic public-data analysis'
SESSION.mount('https://', HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])))


def fetch(url, relative, offline=False):
    path = RAW / relative
    meta = path.with_suffix(path.suffix + '.metadata.json')
    if path.exists():
        if not meta.exists():
            raise FileNotFoundError(f'Cached source is missing its checksum sidecar: {meta}. Restore the matching sidecar or move the incomplete cached file aside and rerun online.')
        record = json.loads(meta.read_text(encoding='utf-8'))
        if record['url'] != url or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'Cached source does not match manifest: {path}')
        return path
    if offline:
        raise FileNotFoundError(f'Offline cache missing {path}; run acquisition with network access.')
    if 'fred.stlouisfed.org/' in url:
        # FRED's edge service responds reliably to the standard-library client.
        with urlopen(url, timeout=45) as response:
            body, resolved_url = response.read(), response.url
    else:
        response = SESSION.get(url, timeout=(20, 60))
        response.raise_for_status()
        body, resolved_url = response.content, response.url
    if 'missing_key' in resolved_url.lower() or b'<title>Missing Key</title>' in body[:500]:
        raise RuntimeError('Census data API requires a key; use official summary files.')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    record = dict(url=url, resolved_url=resolved_url, retrieved_utc=datetime.now(timezone.utc).isoformat(),
                  sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
    meta.write_text(json.dumps(record, indent=2), encoding='utf-8')
    return path


def links(url, relative, offline=False):
    body = fetch(url, relative, offline).read_text(encoding='utf-8', errors='replace')
    return [urljoin(url, h) for h in re.findall(r'href="([^"]+)"', body) if not h.startswith(('?', '/','http'))]
