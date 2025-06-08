from decimal import Decimal
from recipemd.data import Amount
from recipemd.units import DisplayUnit, Quantity, Unit, UnitSystem

unit_system = UnitSystem(quantities=[
    Quantity(
        base_unit=Unit('l', Decimal('1'), alternative_names=frozenset(['liter'])),
        alternative_units=[
            Unit('ml', Decimal('1000'), alternative_names=frozenset(['milliliter'])),
        ],
        display_units=[
            DisplayUnit(unit_name='ml', max=Decimal('500')),
        ],
    ),
])



amount2 = Amount(Decimal('0.15'), 'l', unit_system=unit_system)
amount3 = Amount(Decimal('200'), 'ml', unit_system=unit_system)
print(amount2 < amount3)