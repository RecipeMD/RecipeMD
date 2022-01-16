import operator
from decimal import Decimal
from pprint import pprint

import pytest
from recipemd.data import Amount, RecipeParser
from recipemd.units import (DisplayUnit, Quantity, Unit, UnitConversionError,
                            UnitSystem)


@pytest.fixture(scope="session")
def quantity_volume():
    return Quantity(
        base_unit=Unit('l', Decimal('1'), alternative_names=frozenset(['liter', 'litre']), perferred_name='liter'),
        alternative_units=[
            Unit('ml', Decimal('1000'), alternative_names=frozenset(['milliliter', 'millilitre'])),
            Unit('cl', Decimal('100'), alternative_names=frozenset(['centiliter', 'centilitre']), perferred_name="centiliter"),
            Unit('tsp', Decimal('1000') / Decimal('5'),
                       display_ignore_max=Decimal('5'), 
                       alternative_names=frozenset(['Teelöffel', 'TL', 'teaspoon', 'teaspoons']),
                       perferred_name="TL"),
            Unit('tbsp', Decimal('1000') / Decimal('15'),
                       alternative_names=frozenset(['Esslöffel', 'EL', 'tablespoon', 'tablespoons']),
                       display_ignore_max=Decimal('5')),
        ],
        display_units=[
            DisplayUnit(unit_name='ml', max=Decimal('500')),
            DisplayUnit(unit_name='cl', max=Decimal('100')),
        ],
    )


# @pytest.fixture(scope="session")
# def quantity_mass():
#     return Quantity(
#         base_unit='kg',
#         units=[
#             Unit(['mg'], Decimal('1000000')),
#             Unit(['g'], Decimal('1000')),
#             Unit(['lb', 'pound'], Decimal('.454')),
#             Unit(['Pfd.', 'Pfund'], Decimal('.5')),
#         ],
#         display_units=[
#             DisplayUnit(unit='mg', max=Decimal('500')),
#             DisplayUnit(unit='g', max=Decimal('1000')),
#         ],
#     )


@pytest.fixture(scope="session")
def unit_system(quantity_volume):
    return UnitSystem(quantities=[quantity_volume])


def test_normalize_unit(quantity_volume):
    amount1 = Amount(Decimal('5'))
    assert quantity_volume.normalize_unit(amount1) == amount1

@pytest.mark.parametrize("input, expected", [
    ("20", "20"),
    ("5 ml", "5 ml"),    
    ("1 ml", "1 ml"),
    # preferred_name set, using it instead of id
    ('2 l', '2 liter'),
    ("5000 ml", "5 liter"),
    ("500 ml", "50 centiliter"),    
    ("750 ml", "75 centiliter"),
    # display_ignore_max with perferred_name set, converting to it    
    ("1 TL", "1 TL"),
    ("1 Teelöffel", "1 TL"),
    # display_ignore_max with no perferred_name set, converting to id
    ("1 EL", "1 tbsp"),
    ("1 Esslöffel", "1 tbsp"),
    # higher than display_ignore_max, normal conversions apply
    ("6 TL", "30 ml"),
    ("6 Esslöffel", "90 ml"),
])
def test_normalize_unit_matrix(quantity_volume, input, expected):
    input = RecipeParser.parse_amount(input)
    expected = RecipeParser.parse_amount(expected)
    normalized = quantity_volume.normalize_unit(input)
    assert normalized == expected
    

def test_convert_to_unit(quantity_volume):
    assert quantity_volume.convert_to_unit(Amount(Decimal('20'), 'ml'), 'l') == Amount(Decimal('0.02'), 'l')
    with pytest.raises(UnitConversionError):
        quantity_volume.convert_to_unit(Amount(Decimal('15')), 'l')
    with pytest.raises(UnitConversionError):
        quantity_volume.convert_to_unit(Amount(None, 'ml'), 'l')

def test_unit_comparison(unit_system):
    with unit_system:
        amount1 = Amount(Decimal('20'), 'ml')
        amount2 = Amount(Decimal('15'), 'g')
        amount3 = Amount(None, 'ml')

        assert not amount1 == 5
        assert not amount1 == amount2
        assert not amount1 == amount3

        with pytest.raises(TypeError):
            amount1 < 5
        with pytest.raises(ValueError):
            amount1 < amount2
        with pytest.raises(ValueError):
            amount1 < amount3

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
def test_unit_comparison_matrix(unit_system, left, right, relation):
    with unit_system:
        left = RecipeParser.parse_amount(left)
        right = RecipeParser.parse_amount(right)
        assert relation(left, right)
