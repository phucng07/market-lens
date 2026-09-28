import json
import os
from pathlib import Path
import subprocess
import pandas as pd
import pytest
from src import audit, validate_r
from src.clean import validate
from src.documentation import write_readme
from src.metrics import calculate


def test_readme_preserves_manual_edits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    original = ('# My project\n\nPersonal notes.\n'
                '<!-- findings:start -->\nOld findings\n<!-- findings:end -->\n'
                '<!-- r-status:start -->\nOld status\n<!-- r-status:end -->\n'
                '\nMore notes.\n')
    Path('README.md').write_text(original, encoding='utf-8')
    write_readme(['Updated finding'], {'status':'unavailable'})
    updated = Path('README.md').read_text(encoding='utf-8')
    assert 'Personal notes.' in updated and updated.endswith('More notes.\n')
    assert '- Updated finding' in updated and '**unavailable**' in updated
    assert 'Old findings' not in updated


def test_readme_missing_markers_does_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path('README.md').write_text('Personal notes.', encoding='utf-8')
    with pytest.raises(ValueError, match='marker pair'):
        write_readme([], {'status':'passed'})
    assert Path('README.md').read_text(encoding='utf-8') == 'Personal notes.'


def test_rent_proxy_can_exceed_100_percent():
    d = pd.read_csv('data/processed/city_year_data.csv')
    d.loc[d.acs_available, 'median_household_income_nominal'] = 1000
    d = calculate(d)
    assert d.loc[d.acs_available, 'annual_rent_to_income_pct'].gt(100).all()
    validate(d, int(d.year.max()))


def test_r_timeout_replaces_previous_success(tmp_path, monkeypatch):
    monkeypatch.setattr(validate_r, 'RESULTS', tmp_path)
    monkeypatch.setattr(validate_r.shutil, 'which', lambda name: 'Rscript')
    (tmp_path/'r_validation.json').write_text('{"status":"passed"}')

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired('Rscript', 120)

    monkeypatch.setattr(validate_r.subprocess, 'run', timeout)
    with pytest.raises(RuntimeError, match='R validation failed'):
        validate_r.run()
    assert json.loads((tmp_path/'r_validation.json').read_text())['status'] == 'failed'


def test_audit_rejects_incomplete_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'RESULTS', tmp_path)
    (tmp_path/'pipeline_run.json').write_text('{"status":"incomplete"}')
    with pytest.raises(AssertionError, match='pipeline successfully'):
        audit.run()


def test_audit_rejects_stale_tests(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'RESULTS', tmp_path)
    pipeline = tmp_path/'pipeline_run.json'
    pipeline.write_text('{"status":"completed"}')
    tests = tmp_path/'pytest.xml'
    tests.write_text('<testsuites/>')
    os.utime(tests, (1,1))
    os.utime(pipeline, (2,2))
    with pytest.raises(AssertionError, match='Rerun pytest.xml'):
        audit.run()
