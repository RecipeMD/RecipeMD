from decimal import Decimal
from pprint import pprint

from recipemd.data import Amount
from recipemd.units import DisplayUnit, Quantity, Unit, UnitSystem

us = UnitSystem(quantities=[
    Quantity(
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
])

with us:    
    amount1 = Amount(Decimal('20'), 'cl')
    amount2 = Amount(Decimal('150'), 'ml')
    result = amount1 + amount2
    pprint(result)