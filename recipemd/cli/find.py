# PYTHON_ARGCOMPLETE_OK
"""
Implements :ref:`cli_recipemd_find`
"""

import argparse
import collections
import glob
import itertools
import os
import re
import shutil
import sys
import unicodedata
from math import floor, ceil
from typing import Callable, Iterable

import argcomplete
import pyparsing
from argcomplete import FilesCompleter

import recipemd
from recipemd.data import RecipeParser, Recipe
from recipemd.filter import _FilterElement, FilterParser

__all__ = ['main']


def main():
    # completions
    argcomplete.autocomplete(parser)

    args = parser.parse_args()
    args.func(args)


def list_recipes(args):
    print_result([path for recipe, path in get_filtered_recipes(args)], args.output_multicol)


def list_tags(args):
    list_elements(args, lambda recipe: recipe.tags)


def list_ingredients(args):
    list_elements(args, lambda recipe: [ingr.name for ingr in recipe.leaf_ingredients if ingr.name is not None])


def get_units(recipe: Recipe) -> Iterable[str]:
    ingredient_units = (ingr.amount.unit for ingr in recipe.leaf_ingredients if
                        ingr.amount is not None and ingr.amount.unit is not None)
    yield_units = (yield_.unit for yield_ in recipe.yields if yield_.unit is not None)
    return itertools.chain(ingredient_units, yield_units)


def list_units(args):
    list_elements(args, lambda recipe: get_units(recipe))


def list_elements(args, extractor: Callable[[Recipe], Iterable[str]]):
    counter = collections.Counter()

    for recipe, path in get_filtered_recipes(args):
        counter.update(extractor(recipe))

    if args.count:
        result = list(counter.items())
        result.sort(key=lambda pair: pair[1], reverse=True)
        max_count_length = max(len(str(c)) for c in counter.values())
        result = [f'{count:>{max_count_length}} {tag}' for tag, count in result]
    else:
        result = list(counter)
        result.sort(key=lambda s: s.casefold())

    print_result(result, args.output_multicol)


def get_filtered_recipes(args):
    rp = RecipeParser()
    result = []
    for path in glob.glob(os.path.join(args.folder, '**/*.md'), recursive=True):
        try:
            with open(path, 'r', encoding='UTF-8') as file:
                recipe = rp.parse(file.read())
            if args.expression is None or args.expression.evaluate(recipe):
                result.append((recipe, os.path.relpath(path, args.folder)))
        except Exception as e:
            if not args.no_messages:
                print(f"An error occurred, skipping {os.path.relpath(path, args.folder)}: {e.args[0]}", file=sys.stderr)
    return result


def print_result(items, output_multicol):
    if output_multicol is None:
        if os.isatty(sys.stdout.fileno()):
            output_multicol = 'columns'
        else:
            output_multicol = 'no'

    if output_multicol == 'columns':
        print_columns(items)
    elif output_multicol == 'rows':
        print_columns(items, transpose=True)
    else:
        print("\n".join(items))


def print_columns(items, transpose=True):
    if not items:
        return

    # normalize items so decomposed unicode chars don't break lines
    items = [unicodedata.normalize('NFKC', item) for item in items]
    max_item_width = max(len(item) for item in items)
    column_width = max_item_width + 2
    line_width, _ = shutil.get_terminal_size((80, 20))

    # calculate column and line count
    column_count = floor(line_width / column_width)
    if column_count == 0:
        column_count = 1
    row_count = ceil(len(items) / column_count)

    if transpose:
        matrix = [items[i::row_count] for i in range(0, row_count)]
    else:
        matrix = [items[i:i+column_count] for i in range(0, len(items), column_count)]

    for row in matrix:
        padded_row = [val.ljust(column_width) for val in row[0:-1]]
        padded_row.append(row[-1])
        print("".join(padded_row))


def dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f'"{path}" is not a valid folder')


def create_filter_expr(filter_string) -> _FilterElement:
    try:
        return FilterParser().parse_filter_string(filter_string)
    except pyparsing.ParseBaseException as e:
        raise argparse.ArgumentTypeError(f'"{filter_string}" is not a valid filter: {e}')
    except re.error as e:
        raise argparse.ArgumentTypeError(f'"{filter_string}" contains the regular expression "{e.pattern}": {e}')


# parser is on module level for sphinx-autoprogram
parser = argparse.ArgumentParser(description='Find recipes, ingredients and units by filter expression')

parser.add_argument('-v', '--version', action='version', version=f"%(prog)s ({recipemd.__version__})")

parser.add_argument(
    '-e', '--expression', type=create_filter_expr,
    help='Filter expression. Expects a boolean string, e.g. "cake and vegan or ingr:cheese"'
)
parser.add_argument('-s', '--no-messages', action='store_true', default=False, help='suppress error messages')

matrix_parser = parser.add_mutually_exclusive_group()
matrix_parser.add_argument(
    '-1', dest='output_multicol', action='store_const', const='no',
    help='Force output to be one entry per line. This is the default when output is not to a terminal.'
)
matrix_parser.add_argument(
    '-C', dest='output_multicol', action='store_const', const='columns',
    help='Force multi-column output; this is the default when output is to a terminal.'
)
matrix_parser.add_argument(
    '-x', dest='output_multicol', action='store_const', const='rows',
    help='The same as -C, except that the multi-column output is produced with entries sorted across, rather than '
         'down, the columns.'
)

subparsers = parser.add_subparsers(metavar="action", required=True)

# recipes
parser_recipes = subparsers.add_parser('recipes', help='list recipe paths')
parser_recipes.set_defaults(func=list_recipes)

parser_recipes.add_argument(
    'folder', type=dir_path, nargs='?', default='.', help='path to a folder containing recipemd files. Works '
                                                          'recursively for all *.md files.'
    # very unlikely file extension so completer only returns folders
).completer = FilesCompleter(allowednames="*.7CA0B927-3B02-48EA-97A9-CB557E061992")

# list tags
parser_tags = subparsers.add_parser('tags', help="list used tags")
parser_tags.set_defaults(func=list_tags)

parser_tags.add_argument('-c', '--count', action='store_true', help="count number of uses per tag")
parser_tags.add_argument(
    'folder', type=dir_path, nargs='?', default='.', help='path to a folder containing recipemd files. Works '
                                                          'recursively for all *.md files.'
    # very unlikely file extension so completer only returns folders
).completer = FilesCompleter(allowednames="*.7CA0B927-3B02-48EA-97A9-CB557E061992")

# list ingredients
parser_ingredients = subparsers.add_parser('ingredients', help="list used ingredients")
parser_ingredients.set_defaults(func=list_ingredients)

parser_ingredients.add_argument('-c', '--count', action='store_true', help="count number of uses per ingredient")
parser_ingredients.add_argument(
    'folder', type=dir_path, nargs='?', default='.', help='path to a folder containing recipemd files. Works '
                                                          'recursively for all *.md files.'
    # very unlikely file extension so completer only returns folders
).completer = FilesCompleter(allowednames="*.7CA0B927-3B02-48EA-97A9-CB557E061992")

# list units
parser_units = subparsers.add_parser('units', help="list used units")
parser_units.set_defaults(func=list_units)

parser_units.add_argument('-c', '--count', action='store_true', help="count number of uses per unit")
parser_units.add_argument(
    'folder', type=dir_path, nargs='?', default='.', help='path to a folder containing recipemd files. Works '
                                                          'recursively for all *.md files.'
    # very unlikely file extension so completer only returns folders
).completer = FilesCompleter(allowednames="*.7CA0B927-3B02-48EA-97A9-CB557E061992")

# TODO edit
# parser_edit = subparsers.add_parser('edit', help='edit tags')


if __name__ == "__main__":
    main()
