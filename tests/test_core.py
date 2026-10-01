from copy import deepcopy
from datetime import date

import pytest

from model_drift_observatory.core import SchemaError, compare
from model_drift_observatory.fixtures import fixture_data, expectations


def test_fixture_ground_truth_matches_hand_computed():
    result = compare(fixture_data()['records'])
    expected = expectations()
    for key in ('total_records', 'changed_records', 'unchanged_records', 'counts'):
        assert result[key] == expected[key]
    assert [item['id'] for item in result['findings']] == expected['changed_ids']


def test_report_zero_false_positives():
    result = compare(fixture_data()['records'])
    assert {f['id'] for f in result['findings']} == {f'case-{i:03}' for i in range(80)}


@pytest.mark.parametrize('field,value', [('latency_ms', '-1'), ('latency_ms', 'NaN'),
    ('latency_ms', 'Infinity'), ('latency_ms', '1000000001'), ('latency_ms', True),
    ('status', -1), ('status', True), ('date', '2099-01-01'), ('date', 'bad'),
    ('response', 'x' * 100001), ('fields', ['a', 'a'])], ids=[
        'negative', 'nan', 'infinity', 'too-large', 'boolean-latency', 'bad-status',
        'boolean-status', 'future', 'bad-date', 'long-response', 'duplicate-fields'])
def test_rejects_adversarial_values(field, value):
    record = deepcopy(fixture_data()['records'][0])
    record['current'][field] = value
    with pytest.raises(SchemaError, match=field):
        compare([record])


def test_duplicate_ids_rejected():
    record = fixture_data()['records'][0]
    with pytest.raises(SchemaError, match='duplicate id'):
        compare([record, record])


def test_corrupted_fixture_changes_computed_figures():
    records = fixture_data()['records']
    records[0]['current']['status'] = 200
    result = compare(records)
    assert result['changed_records'] == 79
    assert result['counts']['status'] == 19


def test_exact_threshold_and_overlapping_changes():
    record = fixture_data()['records'][0]
    record['current']['latency_ms'] = '200.0000'
    assert compare([record])['counts']['latency'] == 0
    record['current']['latency_ms'] = '200.0001'
    record['current']['response'] = 'different'
    result = compare([record])
    assert result['changed_records'] == 1
    assert result['counts'] == {'status': 1, 'response': 1, 'schema': 0, 'latency': 1}
    assert result['findings'][0]['latency_delta_ms'] == '100.0001'


def test_field_order_is_not_schema_drift():
    record = fixture_data()['records'][100]
    record['baseline']['fields'] = ['a', 'b']
    record['current']['fields'] = ['b', 'a']
    assert compare([record])['changed_records'] == 0


def test_handles_unicode_and_long_inputs():
    record = fixture_data()['records'][100]
    record['api'] = '测试 café C:\\Users\\henry\\observations'
    record['current']['response'] = '漢' * 100000
    assert compare([record])['findings'][0]['api'] == record['api']


def test_schema_drift_named():
    record = fixture_data()['records'][0]
    record['amount'] = -10
    with pytest.raises(SchemaError, match='amount'):
        compare([record])


def test_date_order():
    record = fixture_data()['records'][0]
    record['current']['date'] = '2026-08-01'
    with pytest.raises(SchemaError, match='precedes'):
        compare([record], date(2026, 9, 30))
