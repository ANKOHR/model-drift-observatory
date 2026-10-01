"""Deterministic report rendering and provenance statements."""

import json


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).replace('\u2014', '\\u2014') + '\n'


def banner(result):
    p = result['provenance']
    return (f"Data provenance: {p['synthetic_records']} synthetic fixture records; "
            f"{p['real_records']} user-declared real records. {p['real_label']}")


def render(result, format='md'):
    if format == 'json':
        return json_text({'banner': banner(result), **result})
    lines = ['# Model Drift Observatory', '', banner(result), '',
             'Computed from supplied paired observations only. No API-wide inference or prediction.', '',
             f"As of: {result['as_of']}. Absolute latency threshold: {result['latency_threshold_ms']} ms (strictly greater).", '',
             f"Records: {result['total_records']}; changed: {result['changed_records']}; unchanged: {result['unchanged_records']}.", '',
             '| Change | Records |', '| --- | ---: |']
    lines += [f'| {key} | {value} |' for key, value in result['counts'].items()]
    lines += ['', result['savings'], '', '## Input traceability', '',
              'Input files and SHA-256 hashes:']
    lines += [f"- {json_text(source).strip()}" for source in result.get('sources', [])]
    lines += ['', '## Findings', '', 'Each finding includes supplied before/after observations. Categories may overlap.']
    lines += ['```json\n' + json_text(finding).rstrip() + '\n```' for finding in result['findings']]
    return '\n'.join(lines).replace('\u2014', '\\u2014') + '\n'
