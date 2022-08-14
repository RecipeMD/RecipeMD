import glob
import os
import textwrap
from dataclasses import replace
from decimal import Decimal
from pprint import pprint

import pytest
from recipemd.data import (Amount, Ingredient, IngredientGroup, Recipe,
                           RecipeParser, RecipeSerializer,
                           get_recipe_with_yield, multiply_recipe)

WRITE_MISSING_TESTCASES = bool(os.environ.get('WRITE_MISSING_TESTCASES'))

@pytest.fixture(scope="session")
def parser():
    return RecipeParser()


@pytest.fixture(scope="session")
def serializer():
    return RecipeSerializer()


def test_amount():
    with pytest.raises(TypeError) as excinfo:
        Amount()

    assert excinfo.value.args[0] == "Factor and unit may not both be None"


def test_ingredient_list_get_leaf_ingredients():
    recipe = Recipe(
        title="Test",
        ingredients=[
            Ingredient(amount=Amount(factor=Decimal('5')), name='Eggs'),
            Ingredient(amount=Amount(factor=Decimal('200'), unit='g'), name='Butter'),
            Ingredient(name='Salt')
        ],
        ingredient_groups=[
            IngredientGroup(
                title='Group',
                ingredients=[
                    Ingredient(amount=Amount(factor=Decimal('2'), unit='cloves'), name='Garlic'),
                ],
                ingredient_groups=[
                    IngredientGroup(title='Subgroup', ingredients=[
                        Ingredient(name='Onions'),
                    ]),
                ]
            ),
        ]
    )

    pprint(recipe)

    leaf_ingredients = list(recipe.leaf_ingredients)
    assert len(leaf_ingredients) == 5
    assert leaf_ingredients[0].name == 'Eggs'
    assert leaf_ingredients[1].name == 'Butter'
    assert leaf_ingredients[2].name == 'Salt'
    assert leaf_ingredients[3].name == 'Garlic'
    assert leaf_ingredients[4].name == 'Onions'


class TestRecipeParser:
    @pytest.mark.parametrize(
        "testcase_file",
        glob.glob(os.path.join(os.path.dirname(__file__), '..', 'testcases', '*.md')),
    )
    def test_parse(self, parser, testcase_file):
        if testcase_file.endswith('.invalid.md'):
            with pytest.raises(RuntimeError):
                with open(testcase_file, 'r', encoding='UTF-8') as f:
                    parser.parse(f.read())
        else:
            with open(testcase_file, 'r', encoding='UTF-8') as f:
                actual_result = parser.parse(f.read())
            expected_result_file = os.path.splitext(testcase_file)[0] + '.json'
            try:
                with open(expected_result_file, 'r', encoding='UTF-8') as f:
                    expected_result = Recipe.from_json(f.read())
                assert actual_result == expected_result
            except FileNotFoundError:
                if not WRITE_MISSING_TESTCASES:
                    raise
                with open(expected_result_file, 'w', encoding='UTF-8') as f:
                    f.write(actual_result.to_json(indent=2))

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


class TestRecipeSerializer:
    def test_serialize(self, serializer):
        testcase_folder = os.path.join(os.path.dirname(__file__), '..', 'testcases')
        with open(os.path.join(testcase_folder, 'recipe.md'), 'r', encoding='UTF-8') as f:
            expected_result = f.read()
        with open(os.path.join(testcase_folder, 'recipe.json'), 'r', encoding='UTF-8') as f:
            recipe = Recipe.from_json(f.read())
        actual_result = serializer.serialize(recipe)
        assert actual_result == expected_result

    def test_serialize_amount(self, serializer):
        assert serializer._serialize_amount(Amount(factor=Decimal('5.000'))) == '5'
        assert serializer._serialize_amount(Amount(factor=Decimal('1')/Decimal('3')), rounding=2) == '0.33'
        assert serializer._serialize_amount(Amount(factor=Decimal('1')/Decimal('3')), rounding=4) == '0.3333'


def test_multiply_recipe():
    recipe = Recipe(
        title="Test",
        yields=[Amount(factor=Decimal('5'), unit="servings"), Amount(unit="unitless yield")],
        ingredients=[
            Ingredient(amount=Amount(factor=Decimal('5')), name='Eggs'),
            Ingredient(amount=Amount(factor=Decimal('200'), unit='g'), name='Butter'),
            Ingredient(name='Salt')
        ],
        ingredient_groups=[
            IngredientGroup(
                title='Group',
                ingredients=[
                    Ingredient(amount=Amount(factor=Decimal('2'), unit='cloves'), name='Garlic'),
                ]
            ),
        ]
    )

    result = multiply_recipe(recipe, Decimal(2))

    assert result.yields[0].factor == Decimal('10')
    assert result.ingredients[0].amount.factor == Decimal('10')
    assert result.ingredients[1].amount.factor == Decimal('400')
    assert result.ingredients[2].amount is None
    assert result.ingredient_groups[0].ingredients[0].amount.factor == Decimal('4')


def test_get_recipe_with_yield():
    recipe = Recipe(
        title="Test",
        yields=[Amount(factor=Decimal('2'), unit="servings")],
        ingredients=[
            Ingredient(amount=Amount(factor=Decimal('5')), name='Eggs'),
        ],
    )

    result = get_recipe_with_yield(recipe, Amount(factor=Decimal('4'), unit='servings'))
    assert result.yields[0] == Amount(factor=Decimal('4'), unit='servings')
    assert result.ingredients[0].amount == Amount(factor=Decimal('10'))

    # interpreted as "4 recipes", that is multiply by 4
    result_unitless = get_recipe_with_yield(recipe, Amount(factor=Decimal('4')))
    assert result_unitless.yields[0] == Amount(factor=Decimal('8'), unit='servings')
    assert result_unitless.ingredients[0].amount == Amount(factor=Decimal('20'))

    # if recipe has unitless yield, it is preferred to the above interpretation
    recipe_with_unitless_yield = replace(recipe, yields=[Amount(factor=Decimal('4'))])
    result_unitless_from_unitless_yield = get_recipe_with_yield(recipe_with_unitless_yield, Amount(factor=Decimal('4')))
    assert result_unitless_from_unitless_yield.yields[0] == Amount(factor=Decimal('4'))
    assert result_unitless_from_unitless_yield.ingredients[0].amount == Amount(factor=Decimal('5'))

    # try with unit not in recipe yields
    with pytest.raises(StopIteration):
        get_recipe_with_yield(recipe, Amount(factor=Decimal('500'), unit='ml'))

    # try with factorless required yield
    with pytest.raises(RuntimeError):
        get_recipe_with_yield(recipe, Amount(unit='ml'))

    # try with factorless yield in recipe
    recipe_with_factorless_yield = replace(recipe, yields=[Amount(unit='Foos')])
    with pytest.raises(RuntimeError):
        get_recipe_with_yield(recipe_with_factorless_yield, Amount(factor=Decimal('500'), unit='Foos'))
