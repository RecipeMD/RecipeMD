from decimal import Decimal
from recipemd.units import UnitSystem, Quantity, Unit, DisplayUnit

foo = UnitSystem([
    Quantity(
        base_unit=Unit(id='x', conversion_factor=Decimal(1)), 
        alternative_units=[
            Unit('y', Decimal('2')),
        ], 
        display_units=[
            DisplayUnit(unit_name='y')
        ]
    )
])