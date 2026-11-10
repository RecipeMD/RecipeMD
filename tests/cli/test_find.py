"""Regression tests for recipemd-find --count on empty/no-match folders."""

from io import StringIO
from unittest import mock

import pytest

from recipemd.cli import find as find_cli


def run_find(*argv):
    with mock.patch("sys.argv", ["recipemd-find", *argv]):
        with mock.patch("sys.stdout", new_callable=StringIO) as out:
            find_cli.main()
    return out.getvalue()


@pytest.mark.parametrize("subcommand", ["tags", "ingredients", "units"])
def test_count_empty_folder_prints_nothing(tmp_path, subcommand):
    """--count with no recipes must print nothing, not crash with ValueError."""
    assert run_find("-1", subcommand, "--count", str(tmp_path)) == ""
