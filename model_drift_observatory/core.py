"""Pure validation and comparison. No API calls or estimated figures."""

from datetime import date
from decimal import Decimal, InvalidOperation


class SchemaError(ValueError):
    """An explicit input field violates the observation contract."""


def fields(value, required, location):
    if not isinstance(value, dict):
        raise SchemaError(f"{location}: expected object")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required)
    if missing or extra:
        raise SchemaError(f"{location}: missing fields {sorted(missing)}; unknown fields {sorted(extra)}")


def number(value, location):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise SchemaError(f"{location}: expected finite nonnegative decimal")
    if len(str(value)) > 64:
        raise SchemaError(f"{location}: numeric text exceeds 64 characters")
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise SchemaError(f"{location}: expected finite nonnegative decimal") from None
    if not result.is_finite() or result < 0 or result > Decimal('1000000000'):
        raise SchemaError(f"{location}: must be finite and between 0 and 1000000000")
    if not -18 <= result.as_tuple().exponent <= 9:
        raise SchemaError(f"{location}: decimal exponent must be between -18 and 9")
    return result


def string(value, location, limit=100000):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise SchemaError(f"{location}: expected nonempty string of at most {limit} characters")


def validate_record(record, as_of):
    fields(record, ['id', 'api', 'synthetic', 'baseline', 'current'], 'record')
    string(record['id'], 'id', 256)
    string(record['api'], 'api', 4096)
    if type(record['synthetic']) is not bool:
        raise SchemaError('synthetic: expected boolean')
    for name in ('baseline', 'current'):
        obs = record[name]
        fields(obs, ['date', 'status', 'response', 'fields', 'latency_ms'], name)
        try:
            observed = date.fromisoformat(obs['date'])
            if observed.isoformat() != obs['date']:
                raise ValueError('noncanonical date')
        except (ValueError, TypeError):
            raise SchemaError(f'{name}.date: expected ISO date YYYY-MM-DD') from None
        if observed > as_of:
            raise SchemaError(f'{name}.date: future date relative to as_of {as_of}')
        if type(obs['status']) is not int or not 100 <= obs['status'] <= 599:
            raise SchemaError(f'{name}.status: expected integer HTTP status 100..599')
        if not isinstance(obs['response'], str) or len(obs['response']) > 100000:
            raise SchemaError(f'{name}.response: expected string of at most 100000 characters')
        if not isinstance(obs['fields'], list) or len(obs['fields']) > 1000:
            raise SchemaError(f'{name}.fields: expected list with at most 1000 entries')
        for item in obs['fields']:
            string(item, f'{name}.fields', 256)
        if len(set(obs['fields'])) != len(obs['fields']):
            raise SchemaError(f'{name}.fields: duplicate field names')
        number(obs['latency_ms'], f'{name}.latency_ms')
    if record['baseline']['date'] > record['current']['date']:
        raise SchemaError('current.date: precedes baseline.date')


def compare(records, as_of=date(2026, 9, 30), latency_threshold_ms='100'):
    """Count exact changes and absolute latency deltas strictly above threshold."""
    threshold = number(latency_threshold_ms, 'latency_threshold_ms')
    seen = set()
    findings = []
    counts = dict.fromkeys(['status', 'response', 'schema', 'latency'], 0)
    synthetic = 0
    for record in sorted(records, key=lambda r: str(r.get('id', '')) if isinstance(r, dict) else ''):
        validate_record(record, as_of)
        if record['id'] in seen:
            raise SchemaError(f"id: duplicate id {record['id']!r}")
        seen.add(record['id'])
        synthetic += int(record['synthetic'])
        before, after = record['baseline'], record['current']
        changes = []
        for category, changed in (
            ('status', before['status'] != after['status']),
            ('response', before['response'] != after['response']),
            ('schema', set(before['fields']) != set(after['fields'])),
            ('latency', abs(number(after['latency_ms'], 'latency_ms') - number(before['latency_ms'], 'latency_ms')) > threshold),
        ):
            if changed:
                counts[category] += 1
                changes.append(category)
        if changes:
            findings.append({'id': record['id'], 'api': record['api'], 'changes': changes,
                             'latency_delta_ms': str(number(after['latency_ms'], 'latency_ms') - number(before['latency_ms'], 'latency_ms')),
                             'baseline': before, 'current': after})
    return {'as_of': as_of.isoformat(), 'latency_threshold_ms': str(threshold),
            'total_records': len(records), 'changed_records': len(findings),
            'unchanged_records': len(records) - len(findings), 'counts': counts,
            'provenance': {'synthetic_records': synthetic, 'real_records': len(records) - synthetic,
                           'real_label': "User-declared real observations; authorship and collection are not independently verified."},
            'savings': 'Unmeasured: no time or money savings claimed.', 'findings': findings}
