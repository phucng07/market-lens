from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_app_controls_and_missing_year():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert len(app.tabs)==6
    app.sidebar.radio[0].set_value('Nominal USD').run()
    assert not app.exception
    app.sidebar.multiselect[0].set_value(['Madison']).run()
    assert not app.exception
    app.sidebar.slider[0].set_value((2020,2020)).run()
    assert not app.exception
    assert any('No standard ACS' in item.value for item in app.info)
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any('Select at least one city' in item.value for item in app.info)


def test_app_missing_workbook(monkeypatch):
    is_file = Path.is_file
    monkeypatch.setattr(Path, 'is_file', lambda path: False if path.as_posix() == 'excel/MarketLens_Analysis.xlsx' else is_file(path))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert any('Analysis files are missing' in item.value for item in app.error)


def test_app_incomplete_pipeline(monkeypatch):
    read_text = Path.read_text

    def read_status(path, *args, **kwargs):
        if path.as_posix() == 'data/results/pipeline_run.json':
            return '{"status":"incomplete"}'
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read_status)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert any('last pipeline run did not finish' in item.value for item in app.error)
