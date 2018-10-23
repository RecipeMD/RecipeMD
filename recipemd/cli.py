import argparse
from decimal import Decimal
import sys
from recipemd.data import RecipeParser, RecipeSerializer, multiply_recipe


def main():
    parser = argparse.ArgumentParser(description='Read and process recipemd recipes')

    parser.add_argument('file', type=open, help='A recipemd file')
    parser.add_argument('-i', '--ingredients', action='store_true', help='Display ingredients')

    scale_parser = parser.add_mutually_exclusive_group()
    scale_parser.add_argument('-m', '--multiply', type=Decimal, help='Multiply recipe by N', metavar='N')
    scale_parser.add_argument('-s', '--servings', type=Decimal, help='Scale the recipe for N servings', metavar='N')

    args = parser.parse_args()

    src = args.file.read()

    rp = RecipeParser()
    r = rp.parse(src)

    if args.servings:
        if r.servings is None:
            print(f'Recipe "{r.title}" does not specify a number of servings"', file=sys.stderr)
            exit(1)
        r = multiply_recipe(r, args.servings / r.servings)
    elif args.multiply:
        r = multiply_recipe(r, args.multiply)


    rs = RecipeSerializer()
    if args.ingredients:
        for ingr in r.leaf_ingredients:
            print(' '.join(str(r) for r in (ingr.amount, ingr.unit, ingr.name) if r is not None))
    else:
        print(rs.serialize(r))
