"""Labelled planted fixtures. No random numbers; no seed is required."""

from copy import deepcopy


def fixture_data():
    records = []
    for i in range(200):
        baseline = {'date': '2026-09-01', 'status': 200, 'response': 'ok',
                    'fields': ['answer'], 'latency_ms': '100'}
        current = deepcopy(baseline)
        current['date'] = '2026-09-15'
        if i < 20:
            current['status'] = 503
        elif i < 40:
            current['response'] = 'changed'
        elif i < 60:
            current['fields'] = ['answer', 'version']
        elif i < 80:
            current['latency_ms'] = '201'
        records.append({'id': f'case-{i:03}', 'api': 'example-api', 'synthetic': True,
                        'baseline': baseline, 'current': current})
    return {'_comment': 'SYNTHETIC fixture: planted observations, not external API measurements.',
            'synthetic': True, 'records': records}


def expectations():
    # Hand calculation: four disjoint blocks of 20, followed by 120 controls.
    return {'_comment': 'SYNTHETIC hand-computed expectations, not measured production accuracy.',
            'synthetic': True, 'total_records': 200, 'changed_records': 80,
            'unchanged_records': 120, 'counts': {'status': 20, 'response': 20, 'schema': 20, 'latency': 20},
            'changed_ids': [f'case-{i:03}' for i in range(80)]}
