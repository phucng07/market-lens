"""Run `python -m src.pipeline [--offline]` from the repository root."""
import argparse
import json
from datetime import datetime, timezone
from . import acquire_census, acquire_fred, clean, analysis, regression, visualizations, documentation, excel_export, validate_r
from .config import make_directories, RESULTS


def run(offline=False):
    make_directories()
    status_path = RESULTS/'pipeline_run.json'
    status_path.write_text(json.dumps({'status': 'incomplete', 'offline': offline}), encoding='utf-8')
    census, latest = acquire_census.acquire(offline)
    national = acquire_fred.acquire(latest, offline)
    d = clean.clean(census, national, latest)
    analysis.analyze(d)
    model = regression.fit_models(d)
    visualizations.generate(d)
    rstatus = validate_r.run()
    dictionary, sources = documentation.generate(d, rstatus)
    workbook = excel_export.export(d, dictionary, sources)
    status = dict(status='completed', completed_utc=datetime.now(timezone.utc).isoformat(), first_year=int(d.year.min()),
                  latest_year=latest, rows=len(d), observed_city_years=int(d.acs_available.sum()),
                  r_validation=rstatus['status'], model_observations=model['n'], workbook=workbook.as_posix(), offline=offline)
    status_path.write_text(json.dumps(status, indent=2), encoding='utf-8')
    print(json.dumps(status, indent=2), flush=True)
    return d


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Read verified cached raw files only; never access the network.')
    run(parser.parse_args().offline)
