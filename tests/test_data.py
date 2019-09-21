import glob
import os
import textwrap
from decimal import Decimal

import pytest

from recipemd.data import Recipe, Amount, Ingredient, IngredientGroup, multiply_recipe, RecipeParser


@pytest.fixture(scope="session")
def parser():
    return RecipeParser()


def test_amount():
    with pytest.raises(TypeError) as excinfo:
        Amount()

    assert excinfo.value.args[0] == "Factor and unit may not both be None"


class TestRecipeParser:
    @pytest.mark.parametrize(
        "testcase_file",
        glob.glob(os.path.join(os.path.dirname(__file__), '..', 'testcases','*.md')),
    )
    def test_parse(self, parser, testcase_file):
        if testcase_file.endswith('.invalid.md'):
            with pytest.raises(BaseException):
                with open(testcase_file, 'r', encoding='UTF-8') as f:
                    parser.parse(f.read())
        else:
            expected_result_file = os.path.splitext(testcase_file)[0] + '.json'
            with open(expected_result_file, 'r', encoding='UTF-8') as f:
                expected_result = Recipe.from_json(f.read())
            with open(testcase_file, 'r', encoding='UTF-8') as f:
                actual_result = parser.parse(f.read())
            assert actual_result == expected_result

    def test_parse_amount(self, parser):
        assert parser.parse_amount("2") == Amount(factor=Decimal('2'))
        assert parser.parse_amount("5 g") == Amount(factor=Decimal('5'), unit='g')
        assert parser.parse_amount("5 1/4 ml") == Amount(factor=Decimal('5.25'), unit='ml')
        assert parser.parse_amount("1/4 l") == Amount(factor=Decimal('0.25'), unit='l')
        assert parser.parse_amount("-5") == Amount(factor=Decimal('-5'))
        assert parser.parse_amount("3.2") == Amount(factor=Decimal('3.2'))
        assert parser.parse_amount("3,2") == Amount(factor=Decimal('3.2'))
        assert parser.parse_amount("1 ½ cloves") == Amount(factor=Decimal('1.5'), unit='cloves')
        assert parser.parse_amount("½ pieces") == Amount(factor=Decimal('.5'), unit='pieces')
        assert parser.parse_amount('') is None


def test_multiply_recipe():
    recipe = Recipe(
        title="Test",
        yields=[Amount(factor=Decimal('5'), unit="servings")],
        ingredients=[
            Ingredient(amount=Amount(factor=Decimal('5')), name='Eggs'),
            Ingredient(amount=Amount(factor=Decimal('200'), unit='g'), name='Butter'),
            IngredientGroup(title='Group', children=[
                Ingredient(amount=Amount(factor=Decimal('2'), unit='cloves'), name='Garlic')
            ]),
            Ingredient(name='Salt')
        ],
    )

    result = multiply_recipe(recipe, Decimal(2))

    assert result.yields[0].factor == Decimal('10')
