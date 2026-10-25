import builtins
from contextlib import ExitStack
from io import StringIO
from unittest import mock

import pytest
import recipemd.cli.main as cli
from recipemd.cli.main import main, run

MAIN_RECIPE = """# Main

*2 servings*

---

{ingredients}

---

Main step
"""

SUB_RECIPE = """# Sub

*1 serving*

---

- 1 egg

---

Sub step
"""

# Every test in this file demonstrates a suspected bug and is marked as xfail(strict=True). Once a bug is fixed the test
# starts passing, which makes pytest report it as a failure, and the xfail marker has to be removed.


# export links

@pytest.mark.xfail(strict=True, reason='default --export-links folder is derived with rsplit on the whole path')
@pytest.mark.parametrize('relative_path', ['recipes/foo.d/recipe', 'recipe', './recipe'])
def test_export_links_default_folder_for_file_without_extension(tmp_path, monkeypatch, relative_path):
    monkeypatch.chdir(tmp_path)
    recipe_file = tmp_path / relative_path
    recipe_file.parent.mkdir(parents=True, exist_ok=True)
    recipe_file.write_text(MAIN_RECIPE.format(ingredients='- [egg](sub.md)'), encoding='UTF-8')
    (recipe_file.parent / 'sub.md').write_text(SUB_RECIPE, encoding='UTF-8')

    # note: --export-links takes an optional value, so the file has to come first
    run_cli(relative_path, '--export-links')

    exported = [p for p in tmp_path.rglob('sub.md') if p.parent != recipe_file.parent]
    assert len(exported) == 1
    assert not (tmp_path / 'recipes' / 'foo').exists()


@pytest.mark.xfail(strict=True, reason='Created message is printed before the file is written')
def test_export_links_success_message_after_write(tmp_path):
    recipe_file = write_recipes(tmp_path)
    output_dir = tmp_path / 'out'
    seen_at_message = []

    class SpyStderr(StringIO):
        def write(self, s):
            if s.startswith('Created'):
                target = output_dir / 'sub.md'
                seen_at_message.append(target.read_text(encoding='UTF-8') if target.exists() else '')
            return super().write(s)

    with ExitStack() as stack:
        stack.enter_context(mock.patch('sys.argv', ['', recipe_file, '--export-links', str(output_dir)]))
        stack.enter_context(mock.patch('sys.stdout', new_callable=StringIO))
        stack.enter_context(mock.patch('sys.stderr', SpyStderr()))
        run()

    assert seen_at_message
    assert all(content != '' for content in seen_at_message)


@pytest.mark.xfail(strict=True, reason='exported files are named by basename only and overwrite each other')
def test_export_links_with_same_basename_do_not_overwrite_each_other(tmp_path):
    for name in ('a', 'b'):
        folder = tmp_path / name
        folder.mkdir()
        (folder / 'x.md').write_text(SUB_RECIPE.replace('Sub step', f'Step from {name}'), encoding='UTF-8')
    recipe_file = write_recipes(tmp_path, ingredients='- [one](a/x.md)\n- [two](b/x.md)')
    output_dir = tmp_path / 'out'

    run_cli(recipe_file, '--export-links', str(output_dir))

    contents = ''.join(p.read_text(encoding='UTF-8') for p in output_dir.rglob('*') if p.is_file())
    assert 'Step from a' in contents
    assert 'Step from b' in contents


@pytest.mark.xfail(strict=True, reason='a link ending in / produces an empty file name (IsADirectoryError)')
def test_export_links_with_trailing_slash_url_does_not_crash(tmp_path):
    recipe_file = write_recipes(tmp_path, ingredients='- [egg](sub/)')
    output_dir = tmp_path / 'out'

    with mock.patch('urllib.request.urlopen', return_value=FakeResponse(SUB_RECIPE)):
        run_cli(recipe_file, '--export-links', str(output_dir))

    # either a usable file name is chosen or the link is rejected
    assert not output_dir.is_dir() or all(p.is_file() for p in output_dir.iterdir())


@pytest.mark.xfail(strict=True, reason='--export-links honors --title and writes title-only files')
def test_export_links_ignores_display_format_options(tmp_path):
    recipe_file = write_recipes(tmp_path)
    output_dir = tmp_path / 'out'

    _, _, error = run_cli(recipe_file, '-t', '--export-links', str(output_dir))

    exported = list(output_dir.glob('*')) if output_dir.is_dir() else []
    # either the combination is rejected, or the exported files are still full recipes
    assert error is not None or (exported and all('Sub step' in p.read_text(encoding='UTF-8') for p in exported))


# flatten

@pytest.mark.xfail(strict=True, reason='identical link ingredients append the linked instructions twice')
def test_flatten_duplicate_link_ingredients_adds_instructions_once(tmp_path):
    recipe_file = write_recipes(tmp_path, ingredients='- [egg](sub.md)\n- [egg](sub.md)')

    stdout, _, _ = run_cli('-f', recipe_file)

    assert stdout.count('Sub step') == 1


@pytest.mark.xfail(strict=True, reason='heading bump regex rewrites lines inside fenced code blocks')
def test_flatten_does_not_bump_headings_in_fenced_code_blocks(tmp_path):
    recipe_file = write_recipes(tmp_path, sub=SUB_RECIPE + '\n```\n# shell comment\n```\n')

    stdout, _, _ = run_cli('-f', recipe_file)

    assert '\n# shell comment\n' in stdout
    assert '## shell comment' not in stdout


@pytest.mark.xfail(strict=True, reason='heading bump regex rewrites #hashtag, which is not an ATX heading')
def test_flatten_does_not_bump_hashtags(tmp_path):
    recipe_file = write_recipes(tmp_path, sub=SUB_RECIPE + '\n#hashtag\n\n#3 pan\n')

    stdout, _, _ = run_cli('-f', recipe_file)

    assert '\n#hashtag\n' in stdout
    assert '\n#3 pan\n' in stdout


@pytest.mark.xfail(strict=True, reason='heading bump regex ignores setext headings')
def test_flatten_bumps_setext_headings(tmp_path):
    recipe_file = write_recipes(tmp_path, sub=SUB_RECIPE + '\nSetext\n======\n')

    stdout, _, _ = run_cli('-f', recipe_file)

    # a level 1 setext heading becomes level 2, i.e. it is underlined with dashes or written as ATX level 2
    assert '\nSetext\n======\n' not in stdout


# error handling

@pytest.mark.xfail(strict=True, reason='main() uses the site builtin exit()')
def test_main_does_not_depend_on_site_exit_builtin(tmp_path):
    # `exit` is added by the site module and missing e.g. with `python -S` or in frozen apps
    recipe_file = write_recipes(tmp_path)

    with mock.patch.object(builtins, 'exit', side_effect=NameError("name 'exit' is not defined")):
        _, _, error = run_cli('-y', 'cheese', recipe_file, entry_point=main)

    assert isinstance(error, SystemExit)
    assert error.code not in (0, None)


@pytest.mark.xfail(strict=True, reason='bare except in _process_scaling swallows KeyboardInterrupt/SystemExit')
@pytest.mark.parametrize('exception', [KeyboardInterrupt(), SystemExit(5)])
@pytest.mark.parametrize('arguments', [['-y', '2 servings'], ['-m', '2']])
def test_scaling_does_not_swallow_base_exceptions(tmp_path, exception, arguments):
    recipe_file = write_recipes(tmp_path)

    with mock.patch('recipemd.cli.main.RecipeParser.parse_amount', side_effect=exception):
        try:
            _, _, error = run_cli(*arguments, recipe_file)
        except BaseException as e:
            error = e

    assert error is exception


@pytest.mark.xfail(strict=True, reason='invalid main recipe produces a raw traceback')
def test_invalid_main_recipe_does_not_produce_traceback(tmp_path):
    recipe_file = write_recipes(tmp_path, main='no title here\n')

    _, _, error = run_cli(recipe_file)

    assert error is not None
    assert error.code not in (0, None)


@pytest.mark.xfail(strict=True, reason='undecodable main recipe produces a raw traceback')
def test_undecodable_main_recipe_does_not_produce_traceback(tmp_path):
    recipe_file = tmp_path / 'main.md'
    recipe_file.write_bytes(b'# Title\n\xff\xfe\n')

    _, _, error = run_cli(str(recipe_file))

    assert error is not None
    assert error.code not in (0, None)


@pytest.mark.xfail(strict=True, reason='the cause of a failed fetch is dropped when printing')
def test_linked_recipe_error_includes_underlying_cause(tmp_path):
    recipe_file = write_recipes(tmp_path, ingredients='- [egg](does_not_exist.md)')

    _, stderr, _ = run_cli('-f', recipe_file)

    # urllib raises e.g. "<urlopen error [Errno 2] No such file or directory: ...>"
    assert 'No such file or directory' in stderr


@pytest.mark.xfail(strict=True, reason='the cause of a failed linked parse is dropped when printing')
def test_linked_recipe_parse_error_includes_underlying_cause(tmp_path):
    recipe_file = write_recipes(tmp_path, sub='no title here\n')

    _, stderr, _ = run_cli('-f', recipe_file)

    assert "Couldn't parse linked recipe" in stderr
    assert 'title' in stderr.split("Couldn't parse linked recipe", 1)[1].lower()


@pytest.mark.xfail(strict=True, reason='StopIteration is used as control flow and misreported')
def test_stop_iteration_leaking_from_scaling_is_not_reported_as_missing_yield(tmp_path):
    recipe_file = write_recipes(tmp_path)

    with mock.patch('recipemd.data.multiply_recipe', side_effect=StopIteration):
        with pytest.raises(StopIteration):
            run_cli('-y', '4 servings', recipe_file)


# network

@pytest.mark.xfail(strict=True, reason='urlopen is called without a timeout')
def test_linked_recipe_requests_use_a_timeout(tmp_path):
    recipe_file = write_recipes(tmp_path)

    with mock.patch('urllib.request.urlopen', return_value=FakeResponse(SUB_RECIPE)) as urlopen:
        run_cli('-f', recipe_file)

    assert urlopen.call_count == 1
    assert urlopen.call_args.kwargs.get('timeout') is not None


# command line interface

@pytest.mark.xfail(strict=True, reason='the input file is never closed')
def test_input_file_is_closed_after_run(tmp_path):
    recipe_file = write_recipes(tmp_path)
    namespaces = []
    real_parse_args = cli.parser.parse_args

    def capture(*args, **kwargs):
        result = real_parse_args(*args, **kwargs)
        namespaces.append(result)
        return result

    with mock.patch.object(cli.parser, 'parse_args', side_effect=capture):
        run_cli('-t', recipe_file)

    assert namespaces
    assert namespaces[0].file.closed


@pytest.mark.xfail(strict=True, reason='--round uses a lambda that shows up in error messages')
def test_round_error_message_does_not_mention_lambda(tmp_path):
    recipe_file = write_recipes(tmp_path)

    _, stderr, _ = run_cli('-r', 'abc', recipe_file)

    assert '<lambda>' not in stderr
    assert '-r/--round' in stderr


@pytest.mark.xfail(strict=True, reason='the yield completer prints exceptions to stdout')
def test_yield_completer_does_not_print_to_stdout_on_errors():
    parsed_args = mock.Mock()
    parsed_args.file.read.side_effect = OSError('boom')

    with mock.patch('sys.stdout', new_callable=StringIO) as stdout:
        result = cli._yield_completer('2', None, None, parsed_args)

    assert result == []
    assert stdout.getvalue() == ''


class FakeResponse:
    """Stands in for the object returned by urllib.request.urlopen"""

    def __init__(self, body: str):
        self._body = body.encode('UTF-8')

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def info(self):
        return mock.Mock(get_content_charset=lambda: 'UTF-8')

    def read(self):
        return self._body


def write_recipes(tmp_path, *, ingredients='- [egg](sub.md)', main=None, sub=SUB_RECIPE) -> str:
    """Writes main.md, which links to sub.md, and returns the path of main.md"""
    recipe_file = tmp_path / 'main.md'
    recipe_file.write_text(MAIN_RECIPE.format(ingredients=ingredients) if main is None else main, encoding='UTF-8')
    (tmp_path / 'sub.md').write_text(sub, encoding='UTF-8')
    return str(recipe_file)


def run_cli(*arguments: str, entry_point=run):
    """Runs the cli with the given arguments and returns (stdout, stderr, SystemExit or None)"""
    with ExitStack() as stack:
        stack.enter_context(mock.patch('sys.argv', [''] + list(arguments)))
        stdout = stack.enter_context(mock.patch('sys.stdout', new_callable=StringIO))
        stderr = stack.enter_context(mock.patch('sys.stderr', new_callable=StringIO))
        try:
            entry_point()
        except SystemExit as e:
            return stdout.getvalue(), stderr.getvalue(), e
        return stdout.getvalue(), stderr.getvalue(), None
