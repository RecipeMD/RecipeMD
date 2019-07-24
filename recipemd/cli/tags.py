import argparse
import glob
import os
import sys

from argcomplete import FilesCompleter
from boolean import boolean, AND, OR, NOT, Symbol

from recipemd.data import RecipeParser

__all__ = ['main']


def main():
    parser = argparse.ArgumentParser(description='List and edit recipemd tags')

    parser.add_argument(
        'folder', type=dir_path, nargs='?', default='.', help='Path to a folder containing recipemd files. Works '
                                                              'recursively for all *.md files. '
    ).completer = FilesCompleter()

    parser.add_argument('-f', '--filter', type=filter_string, help='Filter recipes by tags. Expects a boolean string, '
                                                                   'e.g. "cake and vegan"')

    subparsers = parser.add_subparsers(metavar="action", required=True)

    parser_recipes = subparsers.add_parser('recipes', help='list recipe paths')
    parser_list = subparsers.add_parser('list', help="list used tags")
    # parser_edit = subparsers.add_parser('edit', help='edit tags')

    parser_recipes.set_defaults(func=recipes)
    parser_list.set_defaults(func=list_tags)

    args = parser.parse_args()
    args.func(args)


def recipes(args):
    for recipe, path in get_filtered_recipes(args):
        print(path)


def list_tags(args):
    result = set()
    for recipe, path in get_filtered_recipes(args):
        result.update(recipe.tags)
    result = list(result)
    result.sort()
    print(result)


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
            print(f"An error occurred, skipping {os.path.relpath(path, args.folder)}: "+e.args[0], file=sys.stderr)
    return result


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
        raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")


def filter_string(filter_expr):
    try:
        algebra = boolean.BooleanAlgebra()
        return algebra.parse(filter_expr)
    except boolean.ParseError:
        raise argparse.ArgumentTypeError(f"\"{filter_expr}\" is not a valid boolean string")


if __name__ == "__main__":
    main()
