import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from model_drift_observatory.cli import main, atomic_write
from model_drift_observatory.fixtures import fixture_data
from model_drift_observatory.report import json_text


def setup_input(tmp_path):
    directory = tmp_path / 'input'
    main(['fixtures', '--out', str(directory)])
    return directory


def test_run_completes_on_fixture(tmp_path):
    directory = setup_input(tmp_path)
    start = time.perf_counter()
    results = tmp_path / 'results.json'
    assert main(['run', '--input', str(directory), '--results', str(results)]) == 0
    assert main(['report', '--results', str(results), '--out', str(tmp_path / 'report.md')]) == 0
    assert time.perf_counter() - start < 5


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    assert main(['compare', '--input', str(tmp_path)]) == 0
    assert 'Records: 0; changed: 0; unchanged: 0.' in capsys.readouterr().out


def test_malformed_input_named_error(tmp_path, capsys):
    path = tmp_path / 'bad.json'
    path.write_text('{\n broken}', encoding='utf-8')
    assert main(['run', '--input', str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert 'ParseError' in error and 'bad.json' in error and 'line 2' in error


def test_determinism_byte_identical(tmp_path):
    directory = setup_input(tmp_path)
    outputs = []
    for i in range(2):
        result = tmp_path / f'result-{i}.json'
        report = tmp_path / f'report-{i}.md'
        assert main(['run', '--input', str(directory), '--results', str(result)]) == 0
        assert main(['report', '--results', str(result), '--out', str(report)]) == 0
        outputs.append((result.read_bytes(), report.read_bytes()))
    assert outputs[0] == outputs[1]


def test_cli_smoke_all_subcommands(tmp_path):
    directory = setup_input(tmp_path)
    results = tmp_path / 'results.json'
    for name in ('fixtures', 'run', 'report', 'compare', 'validate'):
        process = subprocess.run([sys.executable, '-m', 'model_drift_observatory.cli', name, '--help'], capture_output=True, text=True)
        assert process.returncode == 0 and 'Example:' in process.stdout
    assert main(['validate', '--input', str(directory)]) == 0
    assert main(['compare', '--input', str(directory), '--format', 'json']) == 0
    assert main(['run', '--input', str(directory), '--results', str(results)]) == 0
    assert main(['report', '--results', str(results), '--format', 'json']) == 0


def test_missing_input_named_error(tmp_path, capsys):
    assert main(['run', '--input', str(tmp_path / 'absent')]) == 2
    assert 'MissingInput' in capsys.readouterr().err


def test_report_write_failure_no_partial_files(tmp_path, capsys):
    directory = setup_input(tmp_path)
    target = tmp_path / 'target'
    target.mkdir()
    before = set(tmp_path.iterdir())
    assert main(['compare', '--input', str(directory), '--out', str(target)]) == 2
    assert 'FileError' in capsys.readouterr().err
    assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize('mutation', ['mismatch', 'duplicate', 'unknown'])
def test_input_schema_errors_name_file_and_field(tmp_path, capsys, mutation):
    data = fixture_data()
    if mutation == 'mismatch':
        data['records'][0]['synthetic'] = False
        expected = 'synthetic'
    elif mutation == 'duplicate':
        data['records'][1]['id'] = data['records'][0]['id']
        expected = 'duplicate id'
    else:
        data['records'][0]['amount'] = -1
        expected = 'amount'
    (tmp_path / 'input.json').write_text(json_text(data), encoding='utf-8')
    assert main(['validate', '--input', str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert 'input.json' in error and 'line' in error and expected in error


def test_hand_written_five_record_example(tmp_path):
    root = Path(__file__).resolve().parents[1]
    assert main(['run', '--input', str(root / 'examples' / 'tiny'), '--results', str(tmp_path / 'result.json')]) == 0
    result = json.loads((tmp_path / 'result.json').read_text(encoding='utf-8'))
    assert result['total_records'] == 5 and result['changed_records'] == 4


def test_duplicate_json_keys_rejected(tmp_path, capsys):
    (tmp_path / 'bad.json').write_text('{"synthetic": true, "synthetic": false}', encoding='utf-8')
    assert main(['validate', '--input', str(tmp_path)]) == 2
    assert 'duplicate JSON field' in capsys.readouterr().err


def test_invalid_saved_result_named_error(tmp_path, capsys):
    path = tmp_path / 'result.json'
    path.write_text('{}', encoding='utf-8')
    assert main(['report', '--results', str(path)]) == 2
    assert 'ResultError' in capsys.readouterr().err


def test_cli_unicode_round_trip(tmp_path, capsys):
    data = fixture_data()
    data['records'][0]['api'] = '漢字 café C:\\Users\\henry'
    (tmp_path / 'unicode.json').write_text(json_text(data), encoding='utf-8')
    assert main(['compare', '--input', str(tmp_path), '--format', 'json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['findings'][0]['api'] == data['records'][0]['api']
