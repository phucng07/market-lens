"""Read public endpoint status and directory links while validating source access."""
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def probe(url):
    try:
        with urllib.request.urlopen(url, timeout=45) as response:
            body = response.read().decode('utf-8', errors='replace')
            links = [x for x in re.findall(r'href="([^"]+)"', body) if not x.startswith(('http', '/', '?'))]
            return url, response.status, response.url, (links if links else body[:1200])
    except Exception as error:
        return url, str(error)


if __name__ == '__main__':
    for result in ThreadPoolExecutor(max_workers=4).map(probe, sys.argv[1:]):
        print(result, flush=True)
