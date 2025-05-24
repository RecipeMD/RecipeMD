import glob
import operator
import os
from dataclasses import replace
from decimal import Decimal
from pprint import pprint

import pytest
import json
import jsonschema
from recipemd.units import DisplayUnit, Quantity, Unit, UnitSystem

from recipemd.data import (Amount, Ingredient, IngredientGroup, IngredientList, Recipe,
                           RecipeParser, RecipeSerializer,
                           get_recipe_with_yield, multiply_recipe)

WRITE_MISSING_TESTCASES = bool(os.environ.get('WRITE_MISSING_TESTCASES'))

@pytest.fixture(scope="session")
def parser():
    return RecipeParser()


@pytest.fixture(scope="session")
def serializer():
    return RecipeSerializer()

@pytest.fixture(scope="session")
def quantity_volume():
    return Quantity(
        base_unit=Unit('l', Decimal('1'), alternative_names=frozenset(['liter', 'litre'])),
        alternative_units=[
            Unit('ml', Decimal('1000'), alternative_names=frozenset(['milliliter', 'millilitre'])),
            Unit('cl', Decimal('100'), alternative_names=frozenset(['centiliter', 'centilitre'])),
            Unit(
                'tsp', 
                Decimal('1000') / Decimal('5'),
                alternative_names=frozenset(['Teelöffel', 'TL', 'teaspoon', 'teaspoons']),
                preferred_name="TL"
            ),
            Unit(
                'tbsp', 
                Decimal('1000') / Decimal('15'),
                alternative_names=frozenset(['Esslöffel', 'EL', 'tablespoon', 'tablespoons']),
            ),
        ],
        display_units=[            
            DisplayUnit(unit_name='tsp', max=Decimal('5'), only_if_matching_source_unit=True),
            DisplayUnit(unit_name='tbsp', max=Decimal('5'), only_if_matching_source_unit=True),
            DisplayUnit(unit_name='ml', max=Decimal('500')),
            DisplayUnit(unit_name='cl', max=Decimal('100')),
        ],
    )


@pytest.fixture(scope="session")
def unit_system(quantity_volume):
    return UnitSystem(quantities=[quantity_volume])


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
        glob.glob(os.path.join(os.path.dirname(__file__), '..', 'testcases', 'cases', '*.md')),
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
                # Validate expected result against json schema
                with open(expected_result_file, 'r', encoding='UTF-8') as f:
                    expected_result_json = json.loads(f.read())
                with open(os.path.join(os.path.dirname(__file__), '..', 'testcases', 'testcase.schema.json'), 'r', encoding='UTF-8') as f:
                    schema_json = json.loads(f.read())
                jsonschema.validate(instance=expected_result_json, schema=schema_json)

                # Check that recipes are equal
                expected_result = Recipe.from_dict(expected_result_json)
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

        with pytest.raises(RuntimeError):
            parser.parse_amount('')

        with pytest.raises(RuntimeError):
            parser.parse_amount('foo')


class TestRecipeSerializer:
    def test_serialize(self, serializer):
        testcase_folder = os.path.join(os.path.dirname(__file__), '..', 'testcases', 'cases')
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
        yields=[Amount(factor=Decimal('5'), unit="servings")],
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


class TestAmount:
    def test_normalize(self, unit_system):
        assert Amount(Decimal('2000'), 'ml').normalized().is_identical(Amount(Decimal('2000'), 'ml'))

        with unit_system: 
            assert Amount(Decimal('2000'), 'ml').normalized().is_identical(Amount(Decimal('2'), 'l'))

    def test_in_unit(self, unit_system):
        with pytest.raises(ValueError):
            Amount(Decimal('2000'), 'ml').in_unit('l')

        with unit_system: 
            assert Amount(Decimal('2000'), 'ml').in_unit('l').is_identical(Amount(Decimal('2'), 'l'))

    def test_operators_comparison(self, unit_system):
        assert Amount(Decimal('20'), 'ml') == Amount(Decimal('20'), 'ml')
        assert Amount(Decimal('15'), 'ml') < Amount(Decimal('20'), 'ml')

        assert not Amount(Decimal('20'), 'ml', unit_system=unit_system) == Amount(Decimal('20'), 'ml')
        with pytest.raises(ValueError):
            Amount(Decimal('20'), 'ml', unit_system=unit_system) < Amount(Decimal('1'), 'l') # type: ignore

        with unit_system:            
            assert Amount(Decimal('20'), 'ml') == Amount(Decimal('20'), 'ml')
            assert Amount(Decimal('20'), 'ml') == Amount(Decimal('2'), 'cl')

            assert not Amount(Decimal('20'), 'ml') == 5
            assert not Amount(Decimal('20'), 'ml') == Amount(Decimal('15'), 'g')

            with pytest.raises(TypeError):
                Amount(Decimal('20'), 'ml') < 5 # type: ignore
            with pytest.raises(ValueError):
                Amount(Decimal('20'), 'ml') < Amount(Decimal('15'), 'g') # type: ignore

    @pytest.mark.parametrize("left, relation, right", [
        ("1 TL", operator.eq, "1 TL"),
        ("1 Teelöffel", operator.eq, "1 TL"),
        ("6 TL", operator.eq, "30 ml"),
        ("1 EL", operator.eq, "1 EL"),
        ("1 Esslöffel", operator.eq, "1 Esslöffel"),
        ("6 Esslöffel", operator.eq, "90 ml"),
        ("5 ml", operator.eq, "5 ml"),
        ("5000 ml", operator.gt, "4 liter")
    ])
    def test_operators_comparison_matrix(self, unit_system, left, right, relation):
        with unit_system:
            left = RecipeParser.parse_amount(left)
            right = RecipeParser.parse_amount(right)
            assert relation(left, right)

           
    def test_operator_add(self, unit_system):
        assert Amount(Decimal('20')) + Amount(Decimal('20')) == Amount(Decimal('40'))
        assert Amount(Decimal('20')) + 20 == Amount(Decimal('40'))
        assert Amount(Decimal('20')) + 20.0 == Amount(Decimal('40'))

        assert Amount(Decimal('200'), 'ml') + Amount(Decimal('150'), 'ml') == Amount(Decimal('350'), 'ml')

        with pytest.raises(ValueError):
            Amount(Decimal('20'), 'cl') + Amount(Decimal('150'), 'ml') # type: ignore

        with pytest.raises(ValueError):
            Amount(Decimal('20'), 'cl', unit_system=unit_system) + Amount(Decimal('150'), 'ml') # type: ignore

        with pytest.raises(ValueError):
            Amount(Decimal('20')) + Amount(Decimal('150'), 'ml') # type: ignore

        with pytest.raises(TypeError):
            assert Amount(Decimal('20')) + "2" # type: ignore

        with pytest.raises(TypeError):
            assert Amount(Decimal('20'), 'cl') + 20 # type: ignore

        with unit_system:
            result1 = Amount(Decimal('20'), 'cl') + Amount(Decimal('150'), 'ml')
            assert result1.is_identical(Amount(Decimal('35'), 'cl'))

            result2 = Amount(Decimal('150'), 'ml') + Amount(Decimal('20'), 'cl')
            assert result2.is_identical(Amount(Decimal('350'), 'ml'))

            with pytest.raises(ValueError):
                Amount(Decimal('20'), 'cl') + Amount(Decimal('150'), 'g') # type: ignore

    def test_operator_sub(self, unit_system):
        assert Amount(Decimal('20')) - Amount(Decimal('20')) == Amount(Decimal('0'))
        assert Amount(Decimal('20')) - Decimal('20') == Amount(Decimal('0'))
        assert Amount(Decimal('20')) - 20 == Amount(Decimal('0'))
        assert Amount(Decimal('20')) - 20.0 == Amount(Decimal('0'))

        assert Amount(Decimal('200'), 'ml') - Amount(Decimal('150'), 'ml') == Amount(Decimal('50'), 'ml')

        with pytest.raises(ValueError):
            Amount(Decimal('20'), 'cl') - Amount(Decimal('150'), 'ml') # type: ignore

        with pytest.raises(TypeError):
            assert Amount(Decimal('20')) - "2" # type: ignore

        with pytest.raises(TypeError):
            assert Amount(Decimal('20'), 'cl') - 20 # type: ignore

        with unit_system:   
            result1 = Amount(Decimal('20'), 'cl') - Amount(Decimal('150'), 'ml')
            assert result1.is_identical(Amount(Decimal('5'), 'cl'))

            result2 = Amount(Decimal('200'), 'ml') - Amount(Decimal('15'), 'cl')
            assert result2.is_identical(Amount(Decimal('50'), 'ml'))

            with pytest.raises(ValueError):
                Amount(Decimal('20'), 'cl') - Amount(Decimal('150'), 'g') # type: ignore

    def test_operator_mul(self, unit_system):
        assert Amount(Decimal('6')) * Amount(Decimal('6')) == Amount(Decimal('36'))

        assert Amount(Decimal('20'), 'cl') * 6 == Amount(Decimal('120'), 'cl')
        assert 6 * Amount(Decimal('20'), 'cl') == Amount(Decimal('120'), 'cl')

        assert Amount(Decimal('20'), 'cl') * 6.0 == Amount(Decimal('120'), 'cl')
        assert 6.0 * Amount(Decimal('20'), 'cl') == Amount(Decimal('120'), 'cl')

        assert Amount(Decimal('20'), 'cl') * Decimal('6') == Amount(Decimal('120'), 'cl')
        assert Decimal('6') * Amount(Decimal('20'), 'cl') == Amount(Decimal('120'), 'cl')

        assert Amount(Decimal('20'), 'cl') * Amount(Decimal('6')) == Amount(Decimal('120'), 'cl')
        assert Amount(Decimal('6')) * Amount(Decimal('20'), 'cl') == Amount(Decimal('120'), 'cl')

        with pytest.raises(ValueError):
            Amount(Decimal('20'), 'cl') * Amount(Decimal('20'), 'cl') # type: ignore

        with pytest.raises(TypeError):
            assert Amount(Decimal('20')) * "2" # type: ignore

        with unit_system:
            result1 = Amount(Decimal('20'), 'cl') * 6
            assert result1.is_identical(Amount(Decimal('120'), 'cl'))
            assert result1.unit == 'cl'
            
            result2 = 6 * Amount(Decimal('20'), 'cl')
            assert result2.is_identical(Amount(Decimal('120'), 'cl'))

            assert Amount(Decimal('20'), 'cl') * 6.0 == Amount(Decimal('120'), 'cl')
            assert 6.0 * Amount(Decimal('20'), 'cl') == Amount(Decimal('120'), 'cl')

            assert Amount(Decimal('20'), 'cl') * Decimal('6') == Amount(Decimal('120'), 'cl')
            assert Decimal('6') * Amount(Decimal('20'), 'cl') == Amount(Decimal('120'), 'cl')

            assert Amount(Decimal('20'), 'cl') * Amount(Decimal('6')) == Amount(Decimal('120'), 'cl')
            assert Amount(Decimal('6')) * Amount(Decimal('20'), 'cl') == Amount(Decimal('120'), 'cl')

            with pytest.raises(ValueError):
                Amount(Decimal('20'), 'cl') * Amount(Decimal('20'), 'cl') # type: ignore

    def test_operator_truediv(self, unit_system):
        assert Amount(Decimal('20'), 'cl') / Amount(Decimal('10'), 'cl') == Amount(Decimal('2'))

        assert Amount(Decimal('20'), 'cl') / Amount(Decimal('10')) == Amount(Decimal('2'), unit='cl')
        assert Amount(Decimal('20'), 'cl') / 10 == Amount(Decimal('2'), unit='cl')
        assert Amount(Decimal('20'), 'cl') / 10.0 == Amount(Decimal('2'), unit='cl')

        with pytest.raises(ValueError):
            Amount(Decimal('20'), 'cl') / Amount(Decimal('20'), 'ml') # type: ignore

        with pytest.raises(TypeError):
            assert Amount(Decimal('20')) / "2" # type: ignore

        with unit_system:
            assert Amount(Decimal('20'), 'cl') / Amount(Decimal('20'), 'ml') == Amount(Decimal('10'))
            assert Amount(Decimal('20'), 'ml') / Amount(Decimal('20'), 'cl') == Amount(Decimal('0.1'))
            assert Amount(Decimal('20'), 'cl') / 10 == Amount(Decimal('20'), unit='ml')

            with pytest.raises(ValueError):
                Amount(Decimal('20'), 'cl') / Amount(Decimal('20'), 'g') # type: ignore

    def test_operator_mod(self):
        assert Amount(Decimal('20'), 'cl') % 3 == Amount(Decimal('2'), 'cl')

class TestIngredient:
    def test_normalize(self, unit_system):
        assert Ingredient('salt').normalized() == Ingredient('salt')
        with unit_system: 
            assert Ingredient('water', Amount(Decimal('2000'), 'ml')).normalized() == Ingredient('water', Amount(Decimal('2'), 'l'))


    def test_in_unit(self, unit_system):
        with pytest.raises(ValueError):
            Ingredient('salt').in_unit('l')

        with unit_system: 
            assert Ingredient('salt', Amount(Decimal('2000'), 'ml')).in_unit('l') == Ingredient('salt', Amount(Decimal('2'), 'l'))

    def test_operator_mul(self):
        assert Ingredient('water', Amount(Decimal('2000'), 'ml')) * 3 == Ingredient('water', Amount(Decimal('6000'), 'ml'))
        assert 3 * Ingredient('water', Amount(Decimal('2000'), 'ml')) == Ingredient('water', Amount(Decimal('6000'), 'ml'))
    
    def test_operator_div(self):
        assert Ingredient('water', Amount(Decimal('2000'), 'ml')) / 2 == Ingredient('water', Amount(Decimal('1000'), 'ml'))

class TestRecipe:
    def test_normalize(self, unit_system):
        with unit_system: 
            recipe = Recipe(
                yields=[Amount(Decimal('2000'), 'ml')],
                ingredients=[Ingredient('water', Amount(Decimal('2000'), 'ml'))],
                ingredient_groups=[
                    IngredientGroup(
                        title='Test',
                        ingredients=[Ingredient('water', Amount(Decimal('2000'), 'ml'))],
                    )
                ]
            )
            normalized = recipe.normalized()
            # Note that comparing the whole recipe to an expected normalized version would work even without normalization,
            # because comparisons also use the unit system. To make sure that normalization actually happened we check that the
            # units change in the output.
            assert normalized.yields[0].unit == 'l'
            assert normalized.ingredients[0].amount.unit == 'l' # type: ignore
            assert normalized.ingredient_groups[0].ingredients[0].amount.unit == 'l' # type: ignore