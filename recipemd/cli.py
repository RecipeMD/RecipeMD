import argparse
import sys
from decimal import Decimal
from pprint import pprint
from typing import Union

from recipemd.data import RecipeParser, RecipeSerializer, multiply_recipe, Amount

__all__ = ['main']


def main():
    parser = argparse.ArgumentParser(description='Read and process recipemd recipes')

    parser.add_argument('file', type=open, help='A recipemd file')
    display_parser = parser.add_mutually_exclusive_group()
    display_parser.add_argument('-t', '--title', action='store_true', help='Display recipe title')
    display_parser.add_argument('-i', '--ingredients', action='store_true', help='Display recipe ingredients')

    scale_parser = parser.add_mutually_exclusive_group()
    scale_parser.add_argument('-m', '--multiply', type=str, help='Multiply recipe by N', metavar='N')
    scale_parser.add_argument('-y', '--yield', type=str, help='Scale the recipe for yield Y', metavar='Y',
                              dest='required_yield')

    args = parser.parse_args()

    src = args.file.read()

    rp = RecipeParser()
    r = rp.parse(src)

    if args.required_yield is not None:
        required_yield = RecipeParser.parse_amount(args.required_yield)
        if required_yield is None or required_yield.factor is None:
            print(f'Given yield is not valid', file=sys.stderr)
            exit(1)
        matching_recipe_yield = next((y for y in r.yields if y.unit == required_yield.unit), None)
        if matching_recipe_yield is None:
            if required_yield.unit is None:
                matching_recipe_yield = Amount(Decimal(1))
            else:
                print(f'Recipe "{r.title}" does not specify a yield in the unit "{required_yield.unit}". The '
                      f'following units can be used: ' + ", ".join(f'"{y.unit}"' for y in r.yields), file=sys.stderr)
                exit(1)
        r = multiply_recipe(r, required_yield.factor / matching_recipe_yield.factor)
    elif args.multiply is not None:
        multiply = RecipeParser.parse_amount(args.multiply)
        if multiply is None or multiply.factor is None:
            print(f'Given multiplier is not valid', file=sys.stderr)
            exit(1)
        if multiply.unit is not None:
            print(f'A recipe can only be multiplied with a unitless amount', file=sys.stderr)
            exit(1)
        r = multiply_recipe(r, multiply.factor)

    if args.title:
        print(r.title)
    elif args.ingredients:
        for ingr in r.leaf_ingredients:
            print(' '.join(str(r) for r in (ingr.amount.factor, ingr.amount.unit, ingr.name) if r is not None))
    else:
        rs = RecipeSerializer()
        print(rs.serialize(r))
