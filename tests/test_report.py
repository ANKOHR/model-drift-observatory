import json

import pytest

from model_drift_observatory.core import compare
from model_drift_observatory.fixtures import fixture_data, expectations
from model_drift_observatory.report import render


def test_report_matches_ground_truth_exact():
    result = json.loads(render(compare(fixture_data()['records']), 'json'))
    for key in ('total_records', 'changed_records', 'unchanged_records', 'counts'):
        assert result[key] == expectations()[key]


@pytest.mark.parametrize('format', ['md', 'json'])
def test_report_carries_provenance_banner(format):
    output = render(compare(fixture_data()['records']), format)
    assert 'Data provenance: 200 synthetic fixture records; 0 user-declared real records.' in output


def test_real_and_mixed_provenance():
    records = fixture_data()['records'][:2]
    records[1]['synthetic'] = False
    output = render(compare(records))
    assert '1 synthetic fixture records; 1 user-declared real records' in output
    assert 'not independently verified' in output


def test_hypothetical_figures_labelled():
    output = render(compare([]))
    assert 'Unmeasured: no time or money savings claimed.' in output


def test_no_em_dashes_in_outputs():
    records = fixture_data()['records'][:1]
    records[0]['api'] = 'name' + chr(0x2014) + 'suffix'
    for format in ('md', 'json'):
        output = render(compare(records), format)
        assert chr(0x2014) not in output
        assert '\\u2014' in output
