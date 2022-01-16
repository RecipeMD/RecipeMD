"""
Defines the :class:`UnitSystem` which allows converting a :class:`recipemd.data.Amount` to a different compatible unit. 

You can associate an Amount with a :class:`UnitSystem` on creation.

"""

from contextlib import AbstractContextManager, ContextDecorator
from dataclasses import dataclass, field, replace
from decimal import Decimal
from functools import cached_property
from typing import FrozenSet, Generator, List, Optional, Set, cast

from dataclasses_json import dataclass_json

import recipemd.data as data

__all__ = ['UnitSystem', 'Quantity', 'Unit']

@dataclass_json
@dataclass(frozen=True)
class Unit:
    id: str
    '''Identifier of this unit, typically its symbol'''

    conversion_factor: Decimal
    '''
    The factor used to convert to the base unit. It is expressed as follows: from_unit/base_unit. 
    
    Example: For the `base_unit` "l", the `conversion_factor` for the unit "ml" is 1000.
    '''

    preferred_name: Optional[str] = None
    '''The preferred name to use when converting to this unit for display purposes.'''

    alternative_names: FrozenSet[str] = field(default_factory=frozenset)
    '''Alternative names used for this unit. This may be a long form (e.g. "c" vs "cups") or a translation. Allows recipes
    authored with these unit names to use the unit for conversion purposes.'''

    @cached_property 
    def display_name(self) -> str:
        '''The name used when converting to this unit for display purposes. Uses the `preferred_name` if set, then falls back to 
        the unit's `id`.'''
        return self.preferred_name or self.id

    @cached_property 
    def names(self) -> FrozenSet[str]:
        '''All names of the unit. This is computed as the combination of `id`, `alternative_names` and `preferred_name` if set.'''
        names = [self.id, *self.alternative_names]
        if self.preferred_name:
            names.append(self.preferred_name)
        return frozenset(names)

@dataclass_json
@dataclass(frozen=True)
class DisplayUnit:
    """
    Defines which unit to use to display the quantity this DisplayUnit is associated with. 
    
    This allows to use the appropriate unit for a quantity. For example writing 5 ml instead of 0.005 l, but writing 1.5 l instead of 1500 ml.
    """
    unit_name: str
    min: Optional[Decimal] = None
    max: Optional[Decimal] = None


@dataclass_json
@dataclass(frozen=True)
class Quantity:
    """
    A `quantity` describes a physical quantity like weight or volume that can be expressed in different units. This
    class allows conversions between the different units of a quantity.
    """

    # Implementation note: Methods on this class ignore any Amount.unit_system to prevent infinite recursion.
    # Comparisons are always handled by converting to the base unit and then comparing factors.

    base_unit: Unit
    '''
    The basic unit of this quantity. It is recommended to use the SI unit here. 
    
    Other units are expressed in respect to the `base_unit` via their `conversion_factor`. 
    '''

    alternative_units: List[Unit] 
    '''Alternative units for the quantity. This may be units with SI prefixes of customary/nonstandard units (e.g. tbsp or
    cups).'''

    display_units: List[DisplayUnit]

    def __post_init__(self):
        if self.base_unit.conversion_factor != Decimal(1):
            raise TypeError('Base unit must have a conversion factor of 1!')

    @cached_property
    def units(self) -> FrozenSet[Unit]:
        return frozenset([self.base_unit, *self.alternative_units]) 

    def normalize_unit(self, amount: 'data.Amount') -> 'data.Amount':
        """
        Normalize the given amount to appropriate display unit.
        """
        return self._convert_to_display_unit(amount)

    def _convert_to_display_unit(self, amount: 'data.Amount') -> 'data.Amount':
        display_unit = next((du for du in self.display_units if self._is_applicable(du, amount)), None)
        if display_unit is None:
            return self.convert_to_unit(amount, self.base_unit.id, normalize_unit_name=True)
        return self.convert_to_unit(amount, display_unit.unit_name, normalize_unit_name=True)

    def convert_to_unit(self, amount: 'data.Amount', target_unit_name: str, normalize_unit_name: bool=False):        
        if amount.unit is None:
            raise UnitConversionError(f'Amount "{amount}" can\'t be converted without a unit.')
        target_unit = self._get_unit(target_unit_name)        
        source_unit = self._get_unit(amount.unit)
        new_unit_name = target_unit.display_name if normalize_unit_name else target_unit_name
        new_factor = amount.factor / source_unit.conversion_factor * target_unit.conversion_factor        
        return data.Amount(factor=new_factor, unit=new_unit_name)

    def convert_to_base_unit(self, amount: 'data.Amount') -> 'data.Amount':
        return self.convert_to_unit(amount, self.base_unit.id)

    def _get_unit(self, unit_name: Optional[str]):
        try:
            unit = next(c for c in self.units if unit_name in c.names)
        except StopIteration:
            raise UnitConversionError(f'There is no conversion from "{unit_name}" to "{self.base_unit}"')
        return unit

    def _is_applicable(self, display_unit: DisplayUnit, amount: 'data.Amount') -> bool:
        min_base_factor = self._get_base_factor(display_unit.min, display_unit.unit_name, Decimal('-Infinity'))
        max_base_factor = self._get_base_factor(display_unit.max, display_unit.unit_name, Decimal('Infinity'))
        try:
            amount_base_factor = cast(Decimal, self.convert_to_base_unit(amount).factor)
        except UnitConversionError:
            return False
        return min_base_factor < amount_base_factor < max_base_factor

    def _get_base_factor(self, factor: Optional[Decimal], unit_name: str, default: Decimal) -> Decimal:
        if factor is None:
            return default
        return cast(Decimal, self.convert_to_base_unit(data.Amount(factor, unit_name)).factor)

@dataclass_json
@dataclass(frozen=True)
class UnitSystem(AbstractContextManager, ContextDecorator):
    '''
    A `unit system` combines several quantities. 

    >>> unit_system = UnitSystem(quantities=[
    ...     Quantity(
    ...         base_unit=Unit('l', Decimal('1'), alternative_names=frozenset(['liter'])),
    ...         alternative_units=[
    ...             Unit('ml', Decimal('1000'), alternative_names=frozenset(['milliliter'])),
    ...         ],
    ...         display_units=[
    ...             DisplayUnit(unit_name='ml', max=Decimal('500')),
    ...         ],
    ...     ),
    ... ])

    It can be used to convert a :class:`recipemd.data.Amount` between the units specified in its quantities. 

    >>> from recipemd.data import Amount
    >>> amount1 = Amount(Decimal('0.15'), 'l')
    >>> unit_system.convert_to(amount1, 'ml')
    Amount(factor=Decimal('150.00'), unit='ml')

    Amounts can be associated with a unit system. Amounts belonging to the same unit system can be compared with each other.

    >>> amount2 = Amount(Decimal('0.15'), 'l', unit_system=unit_system)
    >>> amount3 = Amount(Decimal('200'), 'ml', unit_system=unit_system)
    >>> amount2 < amount3
    True

    Amounts can only be compared if they belong to the same unit system.

    >>> amount1 < amount2
    Traceback (most recent call last):
    ...
    ValueError: Can't compare amounts that use different unit systems

    Instead of specifying the unit system in an amount's constructor every time, you can make a UnitSystem active by using it as a
    `ContextManager <https://www.python.org/dev/peps/pep-0343/>`_. All amounts created in the context will be associated with the
    unit system.

    >>> with unit_system:
    ...   amount4 = Amount(Decimal('500'), 'ml')
    >>> assert amount4.unit_system == unit_system

    In general it is recommended to chose one :class:`UnitSystem` instance for a whole program.

    Amounts created outside of the `with` statement are not associated with a UnitSystem. 

    >>> amount5 = Amount(Decimal('1'))
    >>> assert amount5.unit_system is None
    '''

    quantities: List[Quantity]

    def __enter__(self):
        _unit_system_stack.append(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert _unit_system_stack.pop() == self

    def convert_to(self, amount: 'data.Amount', target_unit_name: str) -> 'data.Amount':
        for quantity in self.quantities:
            try:
                return self._insert_unit_system(quantity.convert_to_unit(amount, target_unit_name))
            except UnitConversionError:
                pass
        raise UnitConversionError(f'There is no conversion from "{amount.unit}" to "{target_unit_name}"')

    def convert_to_base(self, amount: 'data.Amount') -> 'data.Amount':
        for quantity in self.quantities:
            try:
                return self._insert_unit_system(quantity.convert_to_base_unit(amount))
            except UnitConversionError:
                pass
        base_units = ', '.join(q.base_unit.id for q in self.quantities)
        raise UnitConversionError(f'There is no conversion from "{amount.unit}" to any of the base units: "{base_units}"')

    def _insert_unit_system(self, amount: 'data.Amount') -> 'data.Amount':
        return replace(amount, unit_system=self)


_unit_system_stack = []


def get_current_unit_system() -> Optional[UnitSystem]:
    return _unit_system_stack[-1] if _unit_system_stack else None


class UnitConversionError(Exception):
    pass
