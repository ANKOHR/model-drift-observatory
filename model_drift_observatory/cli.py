"""Local file CLI. All writes use atomic replacement."""

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import os

from .core import SchemaError, compare, fields, validate_record
from .fixtures import fixture_data, expectations
from .report import json_text, render


class InputError(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON field {key!r}')
        result[key] = value
    return result


def atomic_write(path, content):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n', dir=path.parent, delete=False) as handle:
            temporary = handle.name
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if temporary and Path(temporary).exists():
            Path(temporary).unlink()


def load_inputs(directory, as_of):
    directory = Path(directory)
    if not directory.is_dir():
        raise InputError(f'MissingInput: {directory}: use --input with an existing directory')
    records, sources, seen = [], [], set()
    for path in sorted(directory.iterdir()):
        if path.name == 'expectations.json' or not path.is_file():
            continue
        if path.suffix.lower() != '.json':
            raise InputError(f'SchemaError: {path}: line 1: unsupported input format; use JSON envelopes')
        raw = path.read_bytes()
        try:
            content = raw.decode('utf-8')
            envelope = json.loads(content, object_pairs_hook=unique_object,
                                  parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f'nonfinite {value}')))
        except json.JSONDecodeError as exc:
            raise InputError(f'ParseError: {path}: line {exc.lineno}: {exc.msg}') from None
        except (UnicodeError, ValueError) as exc:
            raise InputError(f'ParseError: {path}: line 1: {exc}') from None
        try:
            fields(envelope, ['_comment', 'synthetic', 'records'], 'envelope')
            if type(envelope['synthetic']) is not bool or not isinstance(envelope['_comment'], str):
                raise SchemaError('synthetic/_comment: expected boolean/string')
            if envelope['synthetic'] and 'synthetic' not in envelope['_comment'].lower():
                raise SchemaError('_comment: synthetic envelope must carry SYNTHETIC label')
            if not isinstance(envelope['records'], list):
                raise SchemaError('records: expected list')
            for index, record in enumerate(envelope['records']):
                try:
                    validate_record(record, as_of)
                    if record['synthetic'] != envelope['synthetic']:
                        raise SchemaError('synthetic: record/envelope mismatch')
                    if record['id'] in seen:
                        raise SchemaError(f"id: duplicate id {record['id']!r}")
                    seen.add(record['id'])
                except SchemaError as exc:
                    raise SchemaError(f'records[{index}]: {exc}') from None
                records.append(record)
        except SchemaError as exc:
            raise InputError(f'SchemaError: {path}: line 1 (JSON document), {exc}') from None
        sources.append({'file': path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
                        'synthetic': envelope['synthetic'], 'declaration': envelope['_comment']})
    return records, sources


def parser():
    root = argparse.ArgumentParser(description='Measure changes in supplied API observation pairs. Local files only.')
    sub = root.add_subparsers(dest='command', required=True)
    fixtures = sub.add_parser('fixtures', help='Generate 200 labelled synthetic pairs', epilog='Example: mdo fixtures --out demo')
    fixtures.add_argument('--out', required=True)
    for name, help_text in [('run', 'Compute and save a drift analysis'), ('compare', 'Compare observations and render directly'), ('validate', 'Validate observation schema and IDs')]:
        command = sub.add_parser(name, help=help_text, epilog=f'Example: mdo {name} --input demo')
        command.add_argument('--input', required=True)
        command.add_argument('--as-of', type=date.fromisoformat, default=date(2026, 9, 30), help='Latest allowed observation date (default: 2026-09-30)')
        command.add_argument('--latency-threshold-ms', default='100', help='Absolute delta must exceed this nonnegative decimal (default: 100)')
        if name == 'run':
            command.add_argument('--results', default='.mdo/results.json')
        if name == 'compare':
            command.add_argument('--format', choices=['md', 'json'], default='md')
            command.add_argument('--out')
    report = sub.add_parser('report', help='Render saved results with provenance', epilog='Example: mdo report --format md')
    report.add_argument('--format', choices=['md', 'json'], default='md')
    report.add_argument('--results', default='.mdo/results.json')
    report.add_argument('--out')
    return root


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    args = parser().parse_args(argv)
    try:
        if args.command == 'fixtures':
            atomic_write(Path(args.out) / 'observations.json', json_text(fixture_data()))
            atomic_write(Path(args.out) / 'expectations.json', json_text(expectations()))
            print('Generated 200 SYNTHETIC paired records and hand-computed expectations.')
            return 0
        if args.command == 'report':
            path = Path(args.results)
            if not path.is_file():
                raise InputError(f'MissingResults: {path}: first use mdo run --input <dir>')
            try:
                result = json.loads(path.read_text(encoding='utf-8'))
                output = render(result, args.format)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise InputError(f'ResultError: {path}: invalid saved result: {exc}') from None
        else:
            records, sources = load_inputs(args.input, args.as_of)
            result = compare(records, args.as_of, args.latency_threshold_ms)
            result['sources'] = sources
            if args.command == 'validate':
                print(f"Valid: {len(records)} paired records. Synthetic: {result['provenance']['synthetic_records']}; user-declared real: {result['provenance']['real_records']}.")
                return 0
            if args.command == 'run':
                atomic_write(args.results, json_text(result))
                print(f"Computed {result['total_records']} records; {result['changed_records']} changed. Synthetic: {result['provenance']['synthetic_records']}; user-declared real: {result['provenance']['real_records']}. Results: {args.results}".replace('\u2014', '\\u2014'))
                return 0
            output = render(result, args.format)
        if args.out:
            atomic_write(args.out, output)
        else:
            sys.stdout.write(output)
        return 0
    except (InputError, SchemaError, OSError) as exc:
        label = 'FileError' if isinstance(exc, OSError) else type(exc).__name__
        print(f'{label}: {exc}'.replace('\u2014', '\\u2014'), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
