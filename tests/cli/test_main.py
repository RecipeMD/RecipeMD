import filecmp
import os
import shutil
import sys
from contextlib import ExitStack
from io import StringIO
from typing import List
from unittest import mock

import pytest
from recipemd.cli.main import Exit, main


@pytest.mark.parametrize(
    'type,dir,arguments',
    [
        ('valid', 'basic', []),
        ('valid', 'title', ['-t']),
        ('valid', 'ingredients', ['-i']),
        ('valid', 'json', ['-j']),
        ('valid', 'multiply', ['-m2']),
        ('valid', 'yield', ['-y', '10 servings']),
        ('valid', 'flatten', ['-f']),
        ('invalid', 'yield_no_matching', ['-y', '500 ml']),
        ('invalid', 'yield_required_invalid', ['-y', 'cheese']),
        ('invalid', 'multiply_unit', ['-m', '500 ml']),
        ('invalid', 'multiply_invalid', ['-m', 'cheese']),
    ]
)
def test_valid_args(type: str, dir: str, arguments: List[str]):
    test_dir = os.path.join(os.path.dirname(__file__), 'test_main', type, dir)
    input_file = os.path.join(test_dir, 'input.md')
    with ExitStack() as stack:
        stack.enter_context(mock.patch('sys.argv', [''] + arguments + [input_file]))
        stack.enter_context(mock.patch('sys.stdout', new_callable=StringIO))
        stack.enter_context(mock.patch('sys.stderr', new_callable=StringIO))
        if type == 'invalid':
            with pytest.raises(Exit):
                main()
        else:
            main()
        actual_stdout = sys.stdout.getvalue()  # type: ignore
        actual_stderr = sys.stderr.getvalue()  # type: ignore

    expected_stdout_file = os.path.join(test_dir, 'stdout')
    assert_equal_to_file_content(actual_stdout, expected_stdout_file)  # type: ignore

    expected_stderr_file = os.path.join(test_dir, 'stderr')
    assert_equal_to_file_content(actual_stderr, expected_stderr_file)  # type: ignore


def test_export_links():
    test_dir = os.path.join(os.path.dirname(__file__), 'test_main', 'export_links')
    input_file = os.path.join(test_dir, 'input.md')

    actual_output_dir = os.path.join(test_dir, 'actual')
    shutil.rmtree(actual_output_dir, ignore_errors=True)

    with ExitStack() as stack:
        actual_output_dir_relative = os.path.relpath(actual_output_dir, os.getcwd())
        stack.enter_context(mock.patch('sys.argv', ['', '--export-links', actual_output_dir_relative, input_file]))
        stack.enter_context(mock.patch('sys.stdout', new_callable=StringIO))
        stack.enter_context(mock.patch('sys.stderr', new_callable=StringIO))

        main()

        actual_stdout = sys.stdout.getvalue()  # type: ignore
        actual_stderr = sys.stderr.getvalue()  # type: ignore

    expected_stdout_file = os.path.join(test_dir, 'stdout')
    assert_equal_to_file_content(actual_stdout, expected_stdout_file)  # type: ignore

    expected_stderr_file = os.path.join(test_dir, 'stderr')
    if os.path.sep != '/':
        actual_stderr = actual_stderr.replace(os.path.sep, '/')  # type: ignore
    assert_equal_to_file_content(actual_stderr, expected_stderr_file)  # type: ignore

    expected_output_dir = os.path.join(test_dir, 'expected')
    files_to_compare = set(os.listdir(expected_output_dir) + os.listdir(actual_output_dir))
    (_, mismatch, errors) = filecmp.cmpfiles(expected_output_dir, actual_output_dir, files_to_compare, shallow=False)
    assert len(mismatch) == 0
    assert len(errors) == 0

    shutil.rmtree(actual_output_dir, ignore_errors=True)


def assert_equal_to_file_content(actual_str, expected_file):
    if os.environ.get('UPDATE_SNAPSHOTS'):
        if actual_str == '':
            try:
                os.remove(expected_file)
            except:
                pass
        else:
            with open(expected_file, 'w', encoding='UTF-8') as f:
                f.write(actual_str)

    try:
        with open(expected_file, 'r', encoding='UTF-8') as f:
            expected_str = f.read()
    except:
        expected_str = ''
    assert actual_str == expected_str
