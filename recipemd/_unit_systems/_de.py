from decimal import Decimal
from recipemd.units import DisplayUnit, Quantity, Unit, UnitSystem

de = UnitSystem(quantities=[
    Quantity(
        base_unit=Unit('l', Decimal('1'), alternative_names=frozenset(['liter', 'Liter'])),
        alternative_units=[
            Unit('Tropfen', Decimal('20000'), alternative_names=frozenset(['Trpf.'])),
            Unit('ml', Decimal('1000')),
            Unit('cl', Decimal('100'), alternative_names=frozenset(['Cl'])),
            Unit('dl', Decimal('10'), alternative_names=frozenset(['Dl'])),
            Unit('TL', Decimal('1000') / Decimal('5'), alternative_names=frozenset(['TL', 'Teelöffel'])),
            Unit('EL', Decimal('1000') / Decimal('15'),  alternative_names=frozenset(['EL', 'Esslöffel'])),
            Unit('Tasse', Decimal('.25'), alternative_names=frozenset(['Tassen'])),
        ],
        display_units=[
            DisplayUnit(unit_name='Tropfen', max=Decimal('5')),
            DisplayUnit(unit_name='TL', max=Decimal('5'), only_if_matching_source_unit=True),
            DisplayUnit(unit_name='EL', max=Decimal('5'), only_if_matching_source_unit=True),
            DisplayUnit(unit_name='Tasse', max=Decimal('3'), only_if_matching_source_unit=True),
            DisplayUnit(unit_name='ml', max=Decimal('1000')),
        ],
    ),
    Quantity(
        base_unit=Unit('kg', Decimal('1'), alternative_names=frozenset(['kilo', 'KG'])),
        alternative_units=[
            Unit('mg', Decimal('1000000')),
            Unit('g', Decimal('1000')),
            # Unit(['lb', 'pound'], Decimal('.454')),
            Unit('Pf', Decimal('.5'), alternative_names=frozenset(['Pfd.', 'Pfund'])),
            # Unit(['ounce'], Decimal('.02834952')),
        ],
        display_units=[
            DisplayUnit(unit_name='mg', max=Decimal('500')),
            DisplayUnit(unit_name='g', max=Decimal('1000')),
        ],
    )
])