from dataclasses import replace
from decimal import Decimal
from recipemd.units import DisplayUnit, Quantity, Unit, UnitSystem
from recipemd._unit_systems._en_us_si import en_us_si

en_us = UnitSystem(quantities=[
    replace(
        next(q for q in en_us_si.quantities if q.base_unit.id == 'l'),         
        display_units=[
            DisplayUnit(unit_name='drop', max=Decimal('1')),
            DisplayUnit(unit_name='drops', max=Decimal('5')),
            DisplayUnit(unit_name='tsp', max=Decimal('5')),
            DisplayUnit(unit_name='tbsp', max=Decimal('5')),
            DisplayUnit(unit_name='cup', max=Decimal('10')),
            DisplayUnit(unit_name='gal'),
        ]
    ),
    replace(
        next(q for q in en_us_si.quantities if q.base_unit.id == 'kg'),    
        display_units=[
            DisplayUnit(unit_name='oz', max=Decimal('20')),
            DisplayUnit(unit_name='lb'),
        ],
    )
])