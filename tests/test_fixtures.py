import json

from model_drift_observatory.cli import main, load_inputs
from model_drift_observatory.fixtures import fixture_data
from datetime import date


def test_fixtures_labelled_synthetic(tmp_path):
    assert main(['fixtures', '--out', str(tmp_path)]) == 0
    for path in tmp_path.iterdir():
        content = json.loads(path.read_text(encoding='utf-8'))
        assert content['synthetic'] is True
        assert 'SYNTHETIC' in content['_comment']
    records, sources = load_inputs(tmp_path, date(2026, 9, 30))
    assert len(records) == 200
    assert all(r['synthetic'] is True for r in records)
    assert len(sources) == 1


def test_fixture_generation_is_deterministic():
    assert fixture_data() == fixture_data()
