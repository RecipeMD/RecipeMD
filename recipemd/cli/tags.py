# PYTHON_ARGCOMPLETE_OK

import argparse
import glob
import os
import shutil
import sys
import unicodedata
from math import floor

import argcomplete
from argcomplete import FilesCompleter
from boolean import boolean, AND, OR, NOT, Symbol

from recipemd.data import RecipeParser

__all__ = ['main']


def main():
    parser = argparse.ArgumentParser(description='List and edit recipemd tags')

    parser.add_argument(
        '-f', '--filter', type=filter_string,
        help='Filter recipes by tags. Expects a boolean string, e.g. "cake and vegan"'
    )
    parser.add_argument('-s', '--no-messages', action='store_true', default=False, help='suppress error messages')
    parser.add_argument(
        '-1', action='store_true', dest='one_per_line', default=False,
        help=' Force output to be one entry per line. This is the default when output is not to a terminal.'
    )

    subparsers = parser.add_subparsers(metavar="action", required=True)

    # recipes
    parser_recipes = subparsers.add_parser('recipes', help='list recipe paths')
    parser_recipes.set_defaults(func=recipes)

    parser_recipes.add_argument(
        'folder', type=dir_path, nargs='?', default='.', help='Path to a folder containing recipemd files. Works '
                                                              'recursively for all *.md files.'
        # very unlikely file extension so completer only returns folders
    ).completer = FilesCompleter(allowednames="*.7CA0B927-3B02-48EA-97A9-CB557E061992")

    # list tags
    parser_list = subparsers.add_parser('list', help="list used tags")
    parser_list.set_defaults(func=list_tags)

    parser_list.add_argument(
        'folder', type=dir_path, nargs='?', default='.', help='Path to a folder containing recipemd files. Works '
                                                              'recursively for all *.md files.'
        # very unlikely file extension so completer only returns folders
    ).completer = FilesCompleter(allowednames="*.7CA0B927-3B02-48EA-97A9-CB557E061992")

    # TODO edit
    # parser_edit = subparsers.add_parser('edit', help='edit tags')

    # completions
    argcomplete.autocomplete(parser)

    args = parser.parse_args()
    args.func(args)


def recipes(args):
    print_result([path for recipe, path in get_filtered_recipes(args)], args.one_per_line)


def list_tags(args):
    result = set()
    for recipe, path in get_filtered_recipes(args):
        result.update(recipe.tags)
    result = list(result)
    result.sort()
    print_result(result, args.one_per_line)


def get_filtered_recipes(args):
    rp = RecipeParser()
    result = []
    for path in glob.glob(os.path.join(args.folder, '**/*.md'), recursive=True):
        try:
            with open(path, 'r', encoding='UTF-8') as file:
                recipe = rp.parse(file.read())
            tags = recipe.tags
            if evaluate(args.filter, tags):
                result.append((recipe, os.path.relpath(path, args.folder)))
        except Exception as e:
            if not args.no_messages:
                print(f"An error occurred, skipping {os.path.relpath(path, args.folder)}: {e.args[0]}", file=sys.stderr)
    return result


def print_result(items, one_per_line):
    if os.isatty(sys.stdout.fileno()) and not one_per_line:
        print_columns(items)
    else:
        print("\n".join(items))


def print_columns(items):
    if not items:
        return
    items = [unicodedata.normalize('NFKC', item).strip() for item in items]
    max_item_width = max(len(item) for item in items)
    column_width = max_item_width + 2
    line_width, _ = shutil.get_terminal_size((80, 20))
    items_per_line = floor(line_width / column_width)
    matrix = [items[i:i+items_per_line] for i in range(0, len(items), items_per_line)]
    for row in matrix:
        padded_row = [val.ljust(column_width) for val in row[0:-1]]
        padded_row.append(row[-1])
        print("".join(padded_row))


def evaluate(expr, tags):
    if expr is None:
        return True
    elif isinstance(expr, AND):
        b = True
        for e in expr.args:
            b = b and evaluate(e, tags)
        return b
    elif isinstance(expr, OR):
        b = True
        for e in expr.args:
            b = b or evaluate(e, tags)
        return b
    elif isinstance(expr, NOT):
        return not evaluate(expr.args[0], tags)
    elif isinstance(expr, Symbol):
        return expr.obj in tags
    else:
        raise RecursionError('something went horribly wrong')


def dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f'"{path}" is not a valid folder')


def filter_string(filter_expr):
    try:
        algebra = boolean.BooleanAlgebra()
        return algebra.parse(filter_expr)
    except boolean.ParseError:
        raise argparse.ArgumentTypeError(f'"{filter_expr}" is not a valid boolean string')


if __name__ == "__main__":
    main()
