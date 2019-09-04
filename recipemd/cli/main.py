# PYTHON_ARGCOMPLETE_OK

import argparse
import copy
import decimal
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import List, Union, Dict, Optional

import argcomplete
from argcomplete.completers import ChoicesCompleter, FilesCompleter
from yarl import URL

from recipemd.data import RecipeParser, RecipeSerializer, multiply_recipe, Ingredient, get_recipe_with_yield, \
    IngredientGroup, Recipe, Amount

__all__ = ['main']


def main():
    parser = argparse.ArgumentParser(description='Read and process recipemd recipes')

    parser.add_argument(
        'file', type=argparse.FileType('r', encoding='UTF-8'), help='A recipemd file'
    ).completer = FilesCompleter(allowednames='*.md')

    display_parser = parser.add_mutually_exclusive_group()
    display_parser.add_argument('-t', '--title', action='store_true', help='Display recipe title')
    display_parser.add_argument('-i', '--ingredients', action='store_true', help='Display recipe ingredients')

    parser.add_argument(
        '-f', '--flatten', action='store_true',
        help='Flatten ingredients and instructions of linked recipes into main recipe'
    )

    parser.add_argument(
        '--export-linked', action='store_true',
        help='Export linked recipes as required for the main recipe'
    )

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

    # completions
    argcomplete.autocomplete(parser)

    # parse args
    args = parser.parse_args()

    # read and parse recipe
    src = args.file.read()
    rp = RecipeParser()
    r = rp.parse(src)

    # scale recipe
    r = _process_scaling(r, args)

    # export linked recipes
    if args.export_linked:
        print('el')

    # flatten recipe
    if args.flatten:
        base_url = URL(f'file://{os.path.abspath(args.file.name)}')
        r = _get_flattened_ingredients_recipe(r, base_url=base_url, parser=rp)

    # create output depending on arguments
    if args.title:
        print(r.title)
    elif args.ingredients:
        for ingr in r.leaf_ingredients:
            print(_ingredient_to_string(ingr, rounding=args.round))
    else:
        rs = RecipeSerializer()
        print(rs.serialize(r, rounding=args.round))


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
    if args.required_yield is not None:
        required_yield = RecipeParser.parse_amount(args.required_yield)
        if required_yield is None or required_yield.factor is None:
            print(f'Given yield is not valid', file=sys.stderr)
            exit(1)
        try:
            r = get_recipe_with_yield(r, required_yield)
        except StopIteration:
            print(f'Recipe "{r.title}" does not specify a yield in the unit "{required_yield.unit}". The '
                  f'following units can be used: ' + ", ".join(f'"{y.unit}"' for y in r.yields), file=sys.stderr)
            exit(1)
    elif args.multiply is not None:
        multiply = RecipeParser.parse_amount(args.multiply)
        if multiply is None or multiply.factor is None:
            print(f'Given multiplier is not valid', file=sys.stderr)
            exit(1)
        if multiply.unit is not None:
            print(f'A recipe can only be multiplied with a unitless amount', file=sys.stderr)
            exit(1)
        r = multiply_recipe(r, multiply.factor)
    return r


def _get_linked_recipes(recipe: Recipe, *, base_url: URL, parser: RecipeParser, flatten: bool = True):
    """
    Gets all ingredients that have a link and a dict of the ingredient id to to recipe instances
    """
    link_ingredients = [i for i in recipe.leaf_ingredients if i.link is not None]
    ingr_id_to_recipe = dict()
    for ingredient in link_ingredients:
        try:
            ingr_id_to_recipe[id(ingredient)] = _get_linked_recipe(ingredient, base_url=base_url, parser=parser,
                                                                   flatten=flatten)
        except Exception as e:
            print(f'{e}: {e.__cause__}', file=sys.stderr)
    return link_ingredients, ingr_id_to_recipe


def _get_flattened_ingredients_recipe(recipe: Recipe, *, base_url: URL, parser: RecipeParser) -> Recipe:
    new_recipe = copy.deepcopy(recipe)

    link_ingredients, ingr_id_to_recipe = _get_linked_recipes(new_recipe, base_url=base_url, parser=parser)

    # recipes that contain no links need not be processed
    if not ingr_id_to_recipe:
        return recipe

    # ingredients
    new_recipe.ingredients = _create_flattened_substituted_ingredients(new_recipe.ingredients, ingr_id_to_recipe)

    # instructions
    instruction_sections = []
    for ingredient in link_ingredients:
        try:
            link_recipe = ingr_id_to_recipe[id(ingredient)]
        except KeyError:
            pass
        else:
            if link_recipe.instructions:
                instruction_sections.append((_link_ingredient_title(ingredient, link_recipe), link_recipe.instructions, False))

    if new_recipe.instructions:
        instruction_sections.append((new_recipe.title, new_recipe.instructions, True))

    instructions = []
    if len(instruction_sections) == 1 and instruction_sections[0][2]:
        instructions.append(instruction_sections[0][1])
    else:
        for heading, body, is_main_instructions in instruction_sections:
            # find headings (see https://spec.commonmark.org/0.29/#atx-heading) and increase level by one
            # note that only up to level 6 is allowed, so we will do 5 -> 6 but not 6 -> 7
            new_body = re.sub(r'^( {0,3})(#{1,5}.*)$', r'\1#\2', body, flags=re.MULTILINE)
            instructions.append(f'## {heading}\n\n{new_body}')

    new_recipe.instructions = '\n\n'.join(instructions)

    return new_recipe


def _get_linked_recipe(ingredient: Ingredient, *, base_url: URL, parser: RecipeParser, flatten: bool = True) -> Recipe:
    url = base_url.join(URL(ingredient.link))
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
        link_recipe = _get_flattened_ingredients_recipe(link_recipe, base_url=url, parser=parser)

    if ingredient.amount:
        link_recipe = get_recipe_with_yield(link_recipe, ingredient.amount)

    return link_recipe


def _create_flattened_substituted_ingredients(ingredients: List[Union[Ingredient, IngredientGroup]],
                                              ingr_id_to_recipe: Dict[int, Recipe]) \
        -> List[Union[Ingredient, IngredientGroup]]:
    result_ingredients = []
    result_groups = []
    for ingr in ingredients:
        if isinstance(ingr, IngredientGroup):
            new_group = copy.deepcopy(ingr)
            new_group.children = _create_flattened_substituted_ingredients(ingr.children, ingr_id_to_recipe)
            result_groups.append(new_group)
        elif id(ingr) in ingr_id_to_recipe and ingr_id_to_recipe[id(ingr)] is not None:
            link_recipe = ingr_id_to_recipe[id(ingr)]
            new_group = IngredientGroup(title=_link_ingredient_title(ingr, link_recipe))
            new_group.children = link_recipe.ingredients
            result_groups.append(new_group)
        else:
            result_ingredients.append(ingr)

    # groups must come after ingredients, see https://github.com/tstehr/RecipeMD/issues/6
    return result_ingredients + result_groups


def _link_ingredient_title(ingr: Ingredient, link_recipe: Recipe) -> str:
    if ingr.name == link_recipe.title:
        title = f'[{ingr.name}]({ingr.link})'
    else:
        title = f'[{ingr.name}: {link_recipe.title}]({ingr.link})'
    return title


def _ingredient_to_string(ingr: Ingredient, *, rounding: Optional[int]=None) -> str:
    if ingr.amount is not None:
        return f'{RecipeSerializer._serialize_amount(ingr.amount, rounding=rounding)} {ingr.name}'
    return ingr.name


if __name__ == "__main__":
    main()
