# PYTHON_ARGCOMPLETE_OK
"""
Implements :ref:`cli_recipemd`
"""

import argparse
import decimal
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from dataclasses import replace
from typing import Dict, Optional, Set

import argcomplete
import recipemd
from argcomplete.completers import ChoicesCompleter, FilesCompleter
from recipemd.data import (Amount, Ingredient, IngredientGroup, IngredientList,
                           Recipe, RecipeParser, RecipeSerializer,
                           get_recipe_with_yield, multiply_recipe)
from yarl import URL

__all__ = ['main']


def main():
    # completions
    argcomplete.autocomplete(parser)

    # parse args
    args = parser.parse_args()

    # initialize
    rp = RecipeParser()
    rs = RecipeSerializer()

    # read and parse recipe
    src = args.file.read()
    r = rp.parse(src)

    # scale recipe
    r = _process_scaling(r, args)

    # base url for late use
    recipe_url = URL(Path(args.file.name).absolute().as_uri())

    # export linked recipes
    if args.export_links:
        _export_links(r, args, recipe_url, rp, rs)
        return

    # flatten recipe
    if args.flatten:
        r = _get_flattened_recipe(r, recipe_url=recipe_url, parser=rp)

    # create output depending on arguments
    print(_create_recipe_output(r, rs, args))


def _yield_completer(prefix, action, parser, parsed_args):
    try:
        src = parsed_args.file.read()
        r = RecipeParser().parse(src)

        parsed_yield = RecipeParser.parse_amount(prefix)
        if parsed_yield is None or parsed_yield.factor is None:
            return [RecipeSerializer._serialize_amount(a) for a in r.yields]

        return [RecipeSerializer._serialize_amount(Amount(parsed_yield.factor, a.unit)) for a in r.yields
                if parsed_yield.unit is None or (a.unit is not None and a.unit.startswith(parsed_yield.unit))]
    except Exception as e:
        print(e)
        return []


def _process_scaling(r, args):
    """Returns recipes scaled according to --multiply or --yield"""
    if args.required_yield is not None:
        required_yield = RecipeParser.parse_amount(args.required_yield)
        if required_yield is None or required_yield.factor is None:
            print(f'Given yield is not valid', file=sys.stderr)
            raise Exit()
        try:
            r = get_recipe_with_yield(r, required_yield)
        except StopIteration:
            print(_make_missing_yield_warning(r, required_yield), file=sys.stderr)
            raise Exit()
    elif args.multiply is not None:
        multiply = RecipeParser.parse_amount(args.multiply)
        if multiply is None or multiply.factor is None:
            print(f'Given multiplier is not valid', file=sys.stderr)
            raise Exit()
        if multiply.unit is not None:
            print(f'A recipe can only be multiplied with a unitless amount', file=sys.stderr)
            raise Exit()
        r = multiply_recipe(r, multiply.factor)
    return r


def _make_missing_yield_warning(recipe: Recipe, required_yield: Amount):
    warning = f'Recipe "{recipe.title}" does not specify a yield in the unit "{required_yield.unit}".'
    if recipe.yields:
        warning += ' The following units can be used: ' + ", ".join(f'"{y.unit}"' for y in recipe.yields if y.unit)
    return warning


def _export_links(r, args, recipe_url, parser, serializer):
    if type(args.export_links) == bool:
        folder = args.file.name.rsplit('.', 1)[0]
    else:
        folder = args.export_links
    os.makedirs(folder, exist_ok=True)
    print(f'Writing to {folder}', file=sys.stderr)
    link_ingredients, ingr_to_recipe = _get_linked_recipes(r, recipe_url=recipe_url, parser=parser, flatten=True)
    for ingredient in link_ingredients:
        try:
            recipe = ingr_to_recipe[ingredient]
        except KeyError:
            continue
        url = recipe_url.join(URL(ingredient.link))
        filename = os.path.join(folder, url.parts[-1])
        with open(filename, 'w', encoding="utf-8") as f:
            print(f'Created {filename} for "{recipe.title}"', file=sys.stderr)
            f.write(_create_recipe_output(recipe, serializer, args))


def _create_recipe_output(recipe, serializer, args):
    """Serializes a recipes according to formatting options"""
    if args.title:
        return recipe.title
    elif args.ingredients:
        return "\n".join(_ingredient_to_string(ingr, rounding=args.round) for ingr in recipe.leaf_ingredients)
    elif args.json:
        return recipe.to_json()
    else:
        return serializer.serialize(recipe, rounding=args.round)


def _get_flattened_recipe(recipe: Recipe, *, recipe_url: URL, parser: RecipeParser, exclude_urls: Set[URL] = frozenset()) -> Recipe:
    """Creates a new recipe with linked recipes recursively flattened"""

    exclude_urls |= {recipe_url}
    link_ingredients, ingr_to_recipe = _get_linked_recipes(recipe, recipe_url=recipe_url, parser=parser, exclude_urls=exclude_urls)

    # recipes that contain no links need not be processed
    if not ingr_to_recipe:
        return recipe

    # ingredients
    recipe = _create_flattened_substituted_ingredients(recipe, ingr_to_recipe)

    # instructions
    instruction_sections = []
    for ingredient in link_ingredients:
        try:
            link_recipe = ingr_to_recipe[ingredient]
        except KeyError:
            pass
        else:
            if link_recipe.instructions:
                instruction_sections.append((_link_ingredient_title(ingredient, link_recipe), link_recipe.instructions, False))

    if recipe.instructions:
        instruction_sections.append((recipe.title, recipe.instructions, True))

    instructions = []
    if len(instruction_sections) == 1 and instruction_sections[0][2]:
        instructions.append(instruction_sections[0][1])
    else:
        for heading, body, is_main_instructions in instruction_sections:
            # find headings (see https://spec.commonmark.org/0.29/#atx-heading) and increase level by one
            # note that only up to level 6 is allowed, so we will do 5 -> 6 but not 6 -> 7
            new_body = re.sub(r'^( {0,3})(#{1,5}.*)$', r'\1#\2', body, flags=re.MULTILINE)
            instructions.append(f'## {heading}\n\n{new_body}')

    recipe = replace(recipe, instructions='\n\n'.join(instructions))

    return recipe


def _get_linked_recipes(recipe: Recipe, *, recipe_url: URL, parser: RecipeParser, flatten: bool = True, exclude_urls: Set[URL] = frozenset()):
    """Gets all ingredients that have a link and a dict of the ingredient to recipe instance"""
    link_ingredients = [i for i in recipe.leaf_ingredients if i.link is not None]
    ingr_to_recipe = dict()
    for ingredient in link_ingredients:
        try:
            ingr_to_recipe[ingredient] = _get_linked_recipe(ingredient, recipe_url=recipe_url, parser=parser,
                                                            flatten=flatten, exclude_urls=exclude_urls)
        except Exception as e:
            print(f'{e}', file=sys.stderr)
    return link_ingredients, ingr_to_recipe


def _get_linked_recipe(ingredient: Ingredient, *, recipe_url: URL, parser: RecipeParser, flatten: bool = True, exclude_urls: Set[URL] = frozenset()) -> Recipe:
    url = recipe_url.join(URL(ingredient.link))

    if url in exclude_urls:
        raise RuntimeError(f'''Skipping ingredient "{ingredient.name}" to prevent infinite recursion''')

    try:
        with urllib.request.urlopen(str(url)) as req:
            encoding = req.info().get_content_charset() or 'UTF-8'
            src = req.read().decode(encoding)
    except Exception as e:
        raise RuntimeError(f'''Couldn't find linked recipe for ingredient "{ingredient.name}"''') from e

    try:
        link_recipe = parser.parse(src)
    except Exception as e:
        raise RuntimeError(f'''Couldn't parse linked recipe for ingredient "{ingredient.name}"''') from e

    if flatten:
        link_recipe = _get_flattened_recipe(link_recipe, recipe_url=url, parser=parser, exclude_urls=exclude_urls)

    if ingredient.amount:
        try:
            link_recipe = get_recipe_with_yield(link_recipe, ingredient.amount)
        except StopIteration:
            print(_make_missing_yield_warning(link_recipe, ingredient.amount), file=sys.stderr)

    return link_recipe


def _create_flattened_substituted_ingredients(ingredient_list: IngredientList,
                                              ingr_to_recipe: Dict[Ingredient, Recipe]) -> IngredientList:
    result_ingredients = []
    result_groups = []

    for ingr in ingredient_list.ingredients:
        if ingr in ingr_to_recipe and ingr_to_recipe[ingr] is not None:
            link_recipe = ingr_to_recipe[ingr]
            new_group = IngredientGroup(
                title=_link_ingredient_title(ingr, link_recipe),
                ingredients=link_recipe.ingredients,
                ingredient_groups=link_recipe.ingredient_groups,
            )
            result_groups.append(new_group)
        else:
            result_ingredients.append(ingr)

    for ingr in ingredient_list.ingredient_groups:
        flattened_ingr = _create_flattened_substituted_ingredients(ingr, ingr_to_recipe)
        new_group = replace(
            ingr,
            ingredients=flattened_ingr.ingredients,
            ingredient_groups=flattened_ingr.ingredient_groups,
        )
        result_groups.append(new_group)

    return replace(
        ingredient_list,
        ingredients=result_ingredients,
        ingredient_groups=result_groups,
    )


def _link_ingredient_title(ingr: Ingredient, link_recipe: Recipe) -> str:
    if ingr.name == link_recipe.title:
        title = f'[{ingr.name}]({ingr.link})'
    else:
        title = f'[{ingr.name}: {link_recipe.title}]({ingr.link})'
    return title


def _ingredient_to_string(ingr: Ingredient, *, rounding: Optional[int] = None) -> str:
    if ingr.amount is not None:
        return f'{RecipeSerializer._serialize_amount(ingr.amount, rounding=rounding)} {ingr.name}'
    return ingr.name


class Exit(Exception):
    pass


# parser is on module level for sphinx-autoprogram
parser = argparse.ArgumentParser(description='Read and process recipemd recipes')

parser.add_argument(
    'file', type=argparse.FileType('r', encoding='UTF-8'), help='A recipemd file'
).completer = FilesCompleter(allowednames='*.md')

parser.add_argument('-v', '--version', action='version', version=f"%(prog)s ({recipemd.__version__})")

display_parser = parser.add_mutually_exclusive_group()
display_parser.add_argument('-t', '--title', action='store_true', help='Display recipe title')
display_parser.add_argument('-i', '--ingredients', action='store_true', help='Display recipe ingredients')
display_parser.add_argument('-j', '--json', action='store_true', help='Display recipe as JSON')

parser.add_argument(
    '-r', '--round', type=lambda s: None if s.lower() == 'no' else int(s), metavar='n', default=2,
    help='Round amount to n digits after decimal point. Default is "2", use "no" to disable rounding.'
).completer = ChoicesCompleter(('no', *range(0, decimal.getcontext().prec + 1)))

scale_parser = parser.add_mutually_exclusive_group()
scale_parser.add_argument('-m', '--multiply', type=str, help='Multiply recipe by N', metavar='N')
scale_parser.add_argument(
    '-y', '--yield', type=str, help='Scale the recipe for yield Y, e.g. "5 servings"',
    metavar='Y', dest='required_yield'
).completer = _yield_completer

flatten_parser = parser.add_mutually_exclusive_group()
flatten_parser.add_argument(
    '-f', '--flatten', action='store_true',
    help='Flatten ingredients and instructions of linked recipes into main recipe'
)
flatten_parser.add_argument(
    '--export-links', type=str, metavar='DIR', nargs='?', default=False, const=True,
    help='Export flattened linked recipes as required for the main recipe to DIR (DIR defaults to recipe file name)'
)


if __name__ == "__main__":
    try:
        main()
    except Exit:
        exit(1)
