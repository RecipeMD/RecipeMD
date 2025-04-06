from dataclasses import replace
import operator
from decimal import Decimal
from pprint import pprint

import pytest
from recipemd.data import Amount, RecipeParser
from recipemd.units import (DisplayUnit, Quantity, Unit, UnitConversionError, UnitSystem)


@pytest.fixture(scope="session")
def quantity_volume():
    return Quantity(
        base_unit=Unit('l', Decimal('1'), alternative_names=frozenset(['liter', 'litre']), preferred_name='liter'),
        alternative_units=[
            Unit('ml', Decimal('1000'), alternative_names=frozenset(['milliliter', 'millilitre'])),
            Unit('cl', Decimal('100'), alternative_names=frozenset(['centiliter', 'centilitre']), preferred_name="centiliter"),
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

class TestQuantity:
    def test_quantity_base_unit(self, ):
        with pytest.raises(TypeError):
            Quantity(
                base_unit=Unit('l', Decimal('2')),
                alternative_units=[],
                display_units=[]
            )

    def test_convert_to_unit(self, quantity_volume):
        assert quantity_volume.convert_to_unit(Amount(Decimal('20'), 'ml'), 'l') == Amount(Decimal('0.02'), 'l')
        with pytest.raises(UnitConversionError):
            quantity_volume.convert_to_unit(Amount(Decimal('15')), 'l')

class TestUnitSystem:
    def test_convert_to_unit(self, unit_system):
        assert unit_system.convert_to(Amount(Decimal('20'), 'ml'), 'l') == Amount(Decimal('0.02'), 'l', unit_system=unit_system)
        with pytest.raises(UnitConversionError):
            unit_system.convert_to(Amount(Decimal('15')), 'l')

    def test_normalize_unit(self, unit_system):
        amount1 = Amount(Decimal('5'))
        assert  replace(unit_system.normalize_unit(amount1), unit_system=None) == amount1

    @pytest.mark.parametrize("input, expected", [
        ("20", "20"),
        ("5 ml", "5 ml"),    
        ("1 ml", "1 ml"),
        # preferred_name set, using it instead of id
        ('2 l', '2 liter'),
        ("5000 ml", "5 liter"),
        ("500 ml", "50 centiliter"),    
        ("750 ml", "75 centiliter"),
        # only_if_matching_source_unit display unit with preferred_name set, converting to it    
        ("1 TL", "1 TL"),
        ("1 Teelöffel", "1 TL"),
        # display_ignore_max with no preferred_name set, converting to id
        ("1 EL", "1 tbsp"),
        ("1 Esslöffel", "1 tbsp"),
        # higher than display_ignore_max, normal conversions apply
        ("6 TL", "30 ml"),
        ("6 Esslöffel", "90 ml"),
    ])
    def test_normalize_unit_matrix(self, unit_system, input, expected):
        input = RecipeParser.parse_amount(input)
        expected = RecipeParser.parse_amount(expected)
        normalized = unit_system.normalize_unit(input)
        normalized_without_unit_system = replace(normalized, unit_system=None)
        assert normalized_without_unit_system == expected
    