from decimal import Decimal
from recipemd.units import DisplayUnit, Quantity, Unit, UnitSystem

en_us_si = UnitSystem(quantities=[
    Quantity(
        base_unit=Unit('l', Decimal('1'), alternative_names=frozenset(['liter', 'litre'])),
        alternative_units=[
            Unit('drops', Decimal('20000'), alternative_names=frozenset(['drop'])),
            Unit('ml', Decimal('1000')),
            Unit('cl', Decimal('100'), alternative_names=frozenset(['Cl'])),
            Unit('dl', Decimal('10'), alternative_names=frozenset(['Dl'])),
            Unit('tsp', Decimal('1000') / Decimal('4.93'), alternative_names=frozenset(['Tsp', 'tsp.', 'Teaspoon'])),
            Unit('tbsp', Decimal('1000') / Decimal('14.79'), alternative_names=frozenset(['Tbsp', 'tbsp.', 'Tablespoon'])),
            Unit('fl oz', Decimal('1000') / Decimal('29.57'), alternative_names=frozenset(['fl. oz.'])),  # US fluid ounce
            Unit('cup', Decimal('1') / Decimal('0.23659'), alternative_names=frozenset(['cups'])),
            Unit('pt', Decimal('1') / Decimal('0.473'), alternative_names=frozenset(['pint', 'pints'])),  # US pint
            Unit('qt', Decimal('1') / Decimal('946.35'), alternative_names=frozenset(['quart', 'quarts'])),  # US quart
            Unit('gal', Decimal('1') / Decimal('3785.41'), alternative_names=frozenset(['gallon', 'gallons'])),  # US gallon
        ],
        display_units=[
            DisplayUnit(unit_name='drop', max=Decimal('1')),
            DisplayUnit(unit_name='drops', max=Decimal('5')),
            DisplayUnit(unit_name='tsp', max=Decimal('5'), only_if_matching_source_unit=True),
            DisplayUnit(unit_name='tbsp', max=Decimal('5'), only_if_matching_source_unit=True),
            DisplayUnit(unit_name='ml', max=Decimal('1000')),
        ],
    ),
    Quantity(
        base_unit=Unit('kg', Decimal('1'), alternative_names=frozenset(['kilo', 'KG'])),
        alternative_units=[
            Unit('mg', Decimal('1000000')),
            Unit('g', Decimal('1000')),
            Unit('lb', Decimal('.454'), alternative_names=frozenset(['lbs', 'pound', 'pounds'])),
            Unit('pound', Decimal('.5')),
            Unit('ounce', Decimal('.02834952'), alternative_names=frozenset(['oz', 'oz.', 'ounces'])),
        ],
        display_units=[
            DisplayUnit(unit_name='mg', max=Decimal('500')),
            DisplayUnit(unit_name='g', max=Decimal('1000')),
        ],
    )
])