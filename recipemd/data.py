"""
Defines the RecipeMD data structures, provides parser, serializer and recipe scaling functions.
"""
#from __future__ import annotations

from numbers import Number
import re
import unicodedata
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Callable, Generator, List, Optional, Tuple, TypeVar, Union
from functools import total_ordering

from dataclasses_json import config, dataclass_json
from markdown_it import MarkdownIt
from markdown_it.token import Token
from typing_extensions import Literal, Self

import recipemd.units

__all__ = ['RecipeParser', 'RecipeSerializer', 'multiply_recipe', 'get_recipe_with_yield',
           'Recipe', 'Ingredient', 'IngredientGroup', 'Amount', 'IngredientList']


T = TypeVar('T')


@dataclass_json
@dataclass(frozen=True)
class IngredientList:
    """
    Represents a list of ingredients.

    This is used as a base class for :class:`Recipe` and :class:`IngredientGroup`, allowing common algorithm implementations for
    both.
    """
    ingredients: List['Ingredient'] = field(default_factory=list)
    ingredient_groups: List['IngredientGroup'] = field(default_factory=list)

    @property
    def leaf_ingredients(self) -> Generator['Ingredient', None, None]:
        yield from self.ingredients
        for ingredient_group in self.ingredient_groups:
            yield from ingredient_group.leaf_ingredients

    @property
    def all_ingredients(self) -> Generator[Union['Ingredient', 'IngredientGroup'], None, None]:
        yield from self.ingredients
        yield from self.ingredient_groups

    def normalized(self) -> Self:        
        """
        Normalize all amounts in this ingredient list to the appropriate display unit.
        """
        ingredients: List[Ingredient] = [i.normalized() for i in self.ingredients]
        ingredient_groups: List[IngredientGroup] = [ig.normalized() for ig in self.ingredient_groups]
        return replace(self, ingredients=ingredients, ingredient_groups=ingredient_groups)


@dataclass_json
@dataclass(frozen=True)
class IngredientGroup(IngredientList):
    """
    An ingredient group is a list of ingredients and ingredient groups with a title.
    """
    # This needs to have a default value. It inherits from IngredientList, which has default values for its fields. In the
    # generated dataclass constructor this field comes after the parent fields and fields without a default value need to precede
    # fields without one. We just use empty string here, the value is always overwritten during parse. 
    title: str = ""


def _get_current_unit_system() -> Optional['recipemd.units.UnitSystem']:
    # fqn to avoid circular import
    return recipemd.units.get_current_unit_system()


@total_ordering
@dataclass_json
@dataclass(frozen=True)
class Amount:
    """
    Represents an amount, which is a factor with an associated unit.

    Amount implements math operators, allowing calculations and comparisons on amounts with the same unit:

    >>> Amount(Decimal('0.15'), 'l') + Amount(Decimal('1'), 'l')
    Amount(factor=Decimal('1.15'), unit='l')

    Calculations for units with different amounts are not possible when the amount is not associated with a
    :class:`recipemd.units.UnitSystem`:

    >>> Amount(Decimal('150'), 'ml') + Amount(Decimal('1'), 'l')
    Traceback (most recent call last):
    ...
    ValueError: Can't perform this operation on amounts without a unit system

    Associating with a unit system that allows conversion between amount's units makes calculations on the amounts possible.

    >>> from recipemd.units import UnitSystem, Quantity, Unit, DisplayUnit
    >>> unit_system = UnitSystem(quantities=[
    ...     Quantity(
    ...         base_unit=Unit('l', Decimal('1')),
    ...         alternative_units=[Unit('ml', Decimal('1000'))],
    ...         display_units=[],
    ...     ),
    ... ])
    ...
    >>> with unit_system:
    ...     Amount(Decimal('150'), 'ml') + Amount(Decimal('1'), 'l')
    Amount(factor=Decimal('1150'), unit='ml')

    """
    factor: Decimal
    unit: Optional[str] = None
    unit_system: Optional['recipemd.units.UnitSystem'] = field(
        default_factory=_get_current_unit_system, repr=False,
        metadata=config(
            exclude=lambda *_: True
        )
    )

    def normalized(self) -> 'Amount':
        """
        Normalize this amount to the appropriate display unit.

        If if this amount is associated with a unit system, this returns a normalized version of this amount, according to the
        display units set in the unit system. If not it returns the amount unchanged, as without a unit system the amount is
        already normalized.
        """
        if self.unit_system is None:
           return self
        return self.unit_system.normalize_unit(self)

    def is_identical(self, other: 'Amount') -> bool:
        """
        Checks if the given amount is identical to the current amount.

        In contrast to ``==`` this checks for exact equality, without any unit conversion.
        """
        return self.factor == other.factor and self.unit == other.unit and self.unit_system == other.unit_system
    
    def in_unit(self, unit: str):
        """
        Convert this amount to the given unit.

        If this amount is associated with a unit system, returns a new amount which is this amount converted to the given unit. 

        :parameter unit: Target unit of the conversion
        :raises ValueError: If the amount is not associated with a unit system
        :raises UnitConversionError: If there is not conversion to the target unit in the unit system
        """
        if self.unit_system is None:
            raise ValueError("Can't convert amount to unit without a unit system")
        return self.unit_system.convert_to(self, unit)

    def __hash__(self):
        # The api contract for __hash__ states that hashable objects which compare equal must have the same hash value. Since
        # amounts that convert to the same base amount compare equals, we can fulfil that by always hashing the base amount.
        self_base = self._get_base_amount_if_possible()
        return hash((self_base.factor, self_base.unit))

    def __eq__(self, other) -> bool:
        if not isinstance(other, Amount):
            return NotImplemented
        if self.unit_system != other.unit_system:
            return False
        self_base = self._get_base_amount_if_possible()
        other_base = other._get_base_amount_if_possible()
        return (self_base.factor, self_base.unit) == (other_base.factor, other_base.unit)

    def __lt__(self, other):
        if not isinstance(other, Amount):
            return NotImplemented
        (self_base, other_base) = self._convert_to_base(other)
        return self_base.factor < other_base.factor
    
    def __add__(self, other):
        if not isinstance(other, Amount):
            if self.unit is not None:
                return NotImplemented
            other_decimal = self._convert_to_decimal(other)
            if other_decimal is None:
                return NotImplemented
            return replace(self, factor=self.factor + other_decimal)
        other_in_self_unit = self._convert_to_self_unit(other)
        return replace(self, factor=self.factor + other_in_self_unit.factor)

    def __sub__(self, other):
        if not isinstance(other, Amount):
            if self.unit is not None:
                return NotImplemented
            other_decimal = self._convert_to_decimal(other)
            if other_decimal is None:
                return NotImplemented
            return replace(self, factor=self.factor - other_decimal)
        other_in_self_unit = self._convert_to_self_unit(other)
        result = replace(self, factor=self.factor - other_in_self_unit.factor)
        return result

    def __mul__(self, other):
        if isinstance(other, Amount):
            if self.unit is not None and other.unit is not None:
                raise ValueError("Can't multiply two Amounts with units.")
            elif self.unit is not None:
                result = replace(self, factor=self.factor * other.factor)
            elif other.unit is not None:
                result = replace(other, factor=self.factor * other.factor)
            else:                
                result = replace(self, factor=self.factor * other.factor)
        else:
            other_decimal = self._convert_to_decimal(other)
            if other_decimal is None:
                return NotImplemented
            result = replace(self, factor=self.factor * other_decimal)
        return result

    def __truediv__(self, other):
        if isinstance(other, Amount):
            if other.unit is None:
                result = replace(self, factor=self.factor / other.factor)
            else:
                (self_base, other_base) = self._convert_to_base(other)
                result = Amount(factor=self_base.factor / other_base.factor)
        else:
            other_decimal = self._convert_to_decimal(other)
            if other_decimal is None:
                return NotImplemented
            result = replace(self, factor=self.factor / other_decimal)
        return result

    def __mod__(self, other):
        result = replace(self, factor=self.factor % other)
        return result

    def __rmul__(self, other):
        return self * other
    
    def _convert_to_self_unit(self, other: 'Amount'):
        if self.unit == other.unit:
            return other
        if self.unit_system != other.unit_system:
            raise ValueError("Can't perform this operation on amounts that use different unit systems")
        if self.unit is None:
            raise ValueError("Can't perform this operation on amounts without a unit")
        if other.unit_system is None:
            raise ValueError("Can't perform this operation on amounts without a unit system")
        try:
            other_in_self_unit = other.in_unit(self.unit)
        except recipemd.units.UnitConversionError:
            raise ValueError(f'Can\'t convert unit "{other.unit}" to unit "{self.unit}"')
        return other_in_self_unit

    def _convert_to_decimal(self, other):
        if isinstance(other, Decimal):
            return other
        if isinstance(other, float) or isinstance(other, int):
            return Decimal(other)
        return None

    def _convert_to_base(self, other: 'Amount'):
        if self.unit == other.unit:
            return (self, other)
        if self.unit_system != other.unit_system:
            raise ValueError("Can't perform this operation on amounts that use different unit systems")
        self_base = self._get_base_amount_if_possible()
        other_base = other._get_base_amount_if_possible()
        if self_base.unit != other_base.unit:
            raise ValueError(f'Can\'t convert unit "{other.unit}" to unit "{self.unit}"')
        return (self_base, other_base)

    def _get_base_amount_if_possible(self) -> 'Amount':
        if not self.unit_system:
            return self
        try:
            return self.unit_system.convert_to_base(self)
        except recipemd.units.UnitConversionError:
            return self


@dataclass_json
@dataclass(frozen=True)
class Ingredient:    
    """
    Represents an ingredient with name and optional amount and link.

    Ingredients implements multiplication and division for scaling an ingredient.

    >>> 3 * Ingredient(name='salt', amount=Amount(factor=Decimal('1'), unit='tsp'), link=None)
    Ingredient(name='salt', amount=Amount(factor=Decimal('3'), unit='tsp'), link=None)

    """
    name: str
    amount: Optional[Amount] = None
    link: Optional[str] = None

    def normalized(self) -> Self:
        """
        Normalize this ingredient's amount to the appropriate display unit.
        """
        if self.amount is None:
            return self
        return replace(self, amount=self.amount.normalized())
    
    def in_unit(self, unit: str):
        """
        Convert this ingredient to the given unit.

        If this ingredient's amount is associated with a unit system, returns a new ingredient with the amount converted to the
        given unit. 

        :parameter unit: Target unit of the conversion
        :raises ValueError: If there is no amount or the amount is not associated with a unit system
        :raises UnitConversionError: If there is not conversion to the target unit in the unit system
        """
        if self.amount is None:
            raise ValueError("Can't convert ingredient to unit if no amount present")
        return replace(self, amount=self.amount.in_unit(unit))
    
    def __mul__(self, other):
        return replace(self, amount=self.amount * other)
    
    def __truediv__(self, other):
        return replace(self, amount=self.amount / other)

    def __rmul__(self, other):
        return self * other

@dataclass_json
@dataclass(frozen=True)
class Recipe(IngredientList):
    """
    Represents a recipe. 
    """
    title: Optional[str] = None
    description: Optional[str] = None
    yields: List[Amount] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    instructions: Optional[str] = None

    def normalized(self) -> Self:
        """
        Normalize all amounts in this recipe to the appropriate display unit.
        """
        r = super().normalized()
        return replace(r, yields=[y.normalized() for y in self.yields])


class RecipeSerializer:
    def serialize(self, recipe: Recipe, *, rounding: Optional[int] = None) -> str:
        rep = ""
        rep += f'# {recipe.title}\n\n'
        if recipe.description is not None:
            rep += f'{recipe.description}\n\n'
        if len(recipe.tags) > 0:
            rep += f'*{", ".join(recipe.tags)}*\n\n'
        if len(recipe.yields) > 0:
            rep += f'**{", ".join(self._serialize_amount(a, rounding=rounding) for a in recipe.yields)}**\n\n'
        rep += f'---\n\n'
        rep += ("\n".join(self._serialize_ingredient(g, 2, rounding=rounding) for g in recipe.all_ingredients)).strip()
        if recipe.instructions is not None:
            rep += f'\n\n---\n\n'
            rep += recipe.instructions
        return rep

    def _serialize_ingredient(self, ingredient, level, *, rounding: Optional[int] = None):
        if isinstance(ingredient, IngredientGroup):
            return f'\n{"#" * level} {ingredient.title}\n\n'\
                   + "\n".join(self._serialize_ingredient(i, level+1, rounding=rounding) for i in ingredient.all_ingredients)
        else:
            if ingredient.amount is not None:
                return f'- *{self._serialize_amount(ingredient.amount, rounding=rounding)}* {self._serialize_ingredient_text(ingredient)}'
            return f'- {self._serialize_ingredient_text(ingredient)}'

    @staticmethod
    def _serialize_ingredient_text(ingredient: Ingredient):
        if ingredient.link:
            return f'[{ingredient.name}]({ingredient.link})'
        return ingredient.name

    @staticmethod
    def _serialize_amount(amount: Amount, *, rounding: Optional[int] = None):
        if amount.unit is not None:
            return f'{RecipeSerializer._normalize_factor(amount.factor, rounding=rounding)} {amount.unit}'
        return f'{RecipeSerializer._normalize_factor(amount.factor, rounding=rounding)}'

    @staticmethod
    def _normalize_factor(factor: Decimal, *, rounding: Optional[int]=None):
        if rounding is not None:
            factor = round(factor, rounding)
        # remove trailing zeros (https://docs.python.org/3/library/decimal.html#decimal-faq)
        factor = factor.quantize(Decimal(1)) if factor == factor.to_integral() else factor.normalize()
        return factor


class RecipeParser:
    """
    Parses strings to a :class:`Recipe` or :class:`Amount`.

    The markdown format is described in the :ref:`RecipeMD Specification`. 
    """

    _list_split = re.compile(r"(?<!\d),|,(?!\d)")

    _md_block: MarkdownIt
    _md_emph: MarkdownIt
    _md_link: MarkdownIt

    _src: Optional[str]
    _src_lines: List[str]
    _block_tokens: List[Token]


    def __init__(self):
        self._md_block = MarkdownIt()
        self._md_block.disable("reference")
        self._md_block.disable(
            names=[*self._md_block.get_all_rules()["inline"], *self._md_block.get_all_rules()["inline2"]]
        )

        self._md_emph = MarkdownIt()
        self._md_emph.disable(self._md_emph.get_all_rules()["inline"])
        self._md_emph.enable("emphasis")

        self._md_link = MarkdownIt()
        self._md_link.disable(self._md_link.get_all_rules()["inline"])
        self._md_link.enable("link")

        self._src = None
        self._src_lines = []
        self._block_tokens = []

    def parse(self, src: str) -> Recipe:
        """
        Parses a markdown string into a :class:`Recipe`.

        >>> recipe_parser = RecipeParser()
        <BLANKLINE>
        >>> recipe = recipe_parser.parse('''
        ...   # Guacamole
        ...   ---
        ...   - *1* avocado
        ...   - *.5 teaspoon* salt
        ...   - *1 1/2 pinches* red pepper flakes
        ...   - lemon juice
        ...   ---
        ...   Remove flesh from avocado and roughly mash with fork. Season to taste with salt pepper and lemon juice.
        ... ''')
        <BLANKLINE>
        >>> recipe.title
        'Guacamole'
        <BLANKLINE>
        >>> recipe.ingredients[0].name
        'avocado'
    

        :raises RuntimeException: If src is not a valid RecipeMD recipe.
        """
        self._src = src
        self._src_lines = src.splitlines()

        self._block_tokens = self._md_block.parse(src)

        title = self._parse_title()
        description = self._parse_description()
        tags, yields = self._parse_tags_and_yields()

        if self._block_tokens and self._block_tokens[0].type == "hr":
            self._block_tokens.pop(0)
        else:
            # TODO this hr is required, but we might just continue anyways?
            raise RuntimeError(f"Invalid, expected hr before ingredient list, got {self._block_tokens[0] and self._block_tokens[0].type if self._block_tokens else None} instead")

        ingredients, ingredient_groups = self._parse_ingredients()

        if self._block_tokens and self._block_tokens[0].type == "hr":
            self._block_tokens.pop(0)
        elif self._block_tokens:
            # TODO this hr is required, but we might just continue anyways?
            raise RuntimeError(f"Invalid, expected hr before instructions, got {self._block_tokens[0] and self._block_tokens[0].type} instead")

        instructions = self._parse_instructions()

        return Recipe(
            title=title,
            description=description,
            tags=tags,
            yields=yields,
            ingredients=ingredients,
            ingredient_groups=ingredient_groups,
            instructions=instructions,
        )

    def _parse_title(self):
        if not self._block_tokens:
            raise RuntimeError(
                f"Invalid, title (heading_open with level h1) required, got None instead"
            )

        heading_open_token = self._block_tokens.pop(0)

        # TODO title is required according to spec, maybe the parser might be more forgiving?
        if heading_open_token.type != "heading_open":
            raise RuntimeError(
                f"Invalid, title (heading_open with level h1) required, got {heading_open_token.type} instead"
            )
        if heading_open_token.tag != "h1":
            raise RuntimeError(
                f"Invalid, title (heading_open with level h1) required, got level {heading_open_token.tag} instead"
            )

        heading_content_token = self._block_tokens.pop(0)
        assert self._block_tokens.pop(0).type == "heading_close"

        return heading_content_token.content

    def _parse_description(self):
        return self._parse_blocks_while(lambda: (self._block_tokens[0].type != "hr") and self._peek_emph_paragraph() is None)

    def _parse_tags_and_yields(self):
        tags: List[str] = []
        yields: List[Amount] = []
        peeked_emph_paragraph = self._peek_emph_paragraph()
        while peeked_emph_paragraph is not None:
            token_type, content = peeked_emph_paragraph
            if token_type == "em_open":
                if tags:
                    raise RuntimeError(f"Invalid, tags may not be specified multiple times")
                tags = [t.strip() for t in self._list_split.split(content)]
            else:
                if yields:
                    raise RuntimeError(f"Invalid, tags may not be specified multiple times")
                yields = [self.parse_amount(t.strip()) for t in self._list_split.split(content)]
            
            # consume paragraph
            del self._block_tokens[:3]            
            peeked_emph_paragraph = self._peek_emph_paragraph()
        return tags, yields


    def _parse_ingredients(self):
        ingredients: List[Ingredient] = []
        ingredient_groups: List[IngredientGroup] = []
        while self._block_tokens and (
            self._block_tokens[0].type == "heading_open" 
            or self._block_tokens[0].type == "bullet_list_open"
            or self._block_tokens[0].type == "ordered_list_open"
        ):
            if self._block_tokens[0].type == 'heading_open':
                self._parse_ingredient_groups(ingredient_groups, parent_level=-1)
                pass
            else:
                self._parse_ingredient_list(ingredients)
        return ingredients, ingredient_groups

    def _parse_ingredient_groups(self, ingredient_groups: List['IngredientGroup'], parent_level):
        while self._block_tokens and (
            self._block_tokens[0].type == "heading_open" 
        ):
            level = int(self._block_tokens[0].tag.lstrip('h'))
            if level <= parent_level:
                return

            self._block_tokens.pop(0)
            heading_content_token = self._block_tokens.pop(0)
            assert self._block_tokens.pop(0).type == "heading_close"

            group = IngredientGroup(title=heading_content_token.content)
            if self._block_tokens and (self._block_tokens[0].type == "bullet_list_open" or self._block_tokens[0].type == "ordered_list_open"):
                self._parse_ingredient_list(group.ingredients)

            self._parse_ingredient_groups(group.ingredient_groups, parent_level=level)

            ingredient_groups.append(group)

    def _parse_ingredient_list(self, ingredients: List['Ingredient']):
        while self._block_tokens and (
            self._block_tokens[0].type == "bullet_list_open"
            or self._block_tokens[0].type == "ordered_list_open"
        ):
            list_open = self._block_tokens.pop(0)

            list_close_index = RecipeParser._get_close_index(list_open, self._block_tokens)
            list_close = self._block_tokens[list_close_index]
            while self._block_tokens[0].type == "list_item_open":
                ingredients.append(self._parse_ingredient())
            assert self._block_tokens.pop(0) == list_close

    def _parse_ingredient(self) -> 'Ingredient':
        list_item_open = self._block_tokens.pop(0)
        assert list_item_open.type == "list_item_open"


        continuation_start_line = None
        first_paragraph_content = None
        if self._block_tokens and self._block_tokens[0].type == "paragraph_open":
            first_paragraph_open = self._block_tokens.pop(0)
            first_paragraph_content = self._block_tokens.pop(0)
            first_paragraph_close_index = RecipeParser._get_close_index(
                first_paragraph_open, self._block_tokens
            )
            del self._block_tokens[: first_paragraph_close_index + 1]
            if first_paragraph_open.map:
                continuation_start_line = first_paragraph_open.map[1]

        end_index = RecipeParser._get_close_index(list_item_open, self._block_tokens)
        list_item_close = self._block_tokens[end_index]

        if first_paragraph_content is not None:
            amount, rest = self._parse_first_emph(first_paragraph_content.content)
            if end_index == 0:
                link, name = self._parse_wrapping_link(rest)
                pass
            else:
                name = rest
                link = None
        else:
            amount = None
            name = ""
            link = None

        name_continuation = self._parse_blocks_while(lambda: self._block_tokens[0] != list_item_close, start_line=continuation_start_line)
        if name_continuation:
            name += "\n" + name_continuation

        assert self._block_tokens.pop(0) == list_item_close

        if not name:
            raise RuntimeError("No ingredient name!")
        name = name.strip()

        return Ingredient(name=name, amount=RecipeParser.parse_amount(amount) if amount is not None else None, link=link)

    def _parse_instructions(self):
        if not self._block_tokens:
            return None
        return self._parse_blocks_while(lambda: True)

    _value_formats = [
        # improper fraction (1 1/2)
        (r'(\d+)\s+(\d+)\s*/\s*(\d+)', lambda match: Decimal(match.group(2)) + (Decimal(match.group(3)) / Decimal(match.group(4))), 3),
        # improper fraction with unicode vulgar fraction (1 ½)
        (r'(\d+)\s+([\u00BC-\u00BE\u2150-\u215E])', lambda match: Decimal(match.group(2)) + Decimal(unicodedata.numeric(match.group(3))), 2),
        # proper fraction (5/6)
        (r'(\d+)\s*/\s*(\d+)', lambda match: Decimal(match.group(2)) / Decimal(match.group(3)), 2),
        # proper fraction with unicode vulgar fraction (⅚)
        (r'([\u00BC-\u00BE\u2150-\u215E])', lambda match: Decimal(unicodedata.numeric(match.group(2))), 1),
        # decimal (5,4 or 5.6)
        (r'(\d*)[.,](\d+)', lambda match: Decimal(match.group(2) + '.' + match.group(3)), 2),
        # integer (4)
        (r'(\d+)', lambda match: Decimal(match.group(2)), 1)
    ]

    @staticmethod
    def parse_amount(amount_str: str) -> Amount:
        """
        Parses an amount string to an :class:`Amount`.

        >>> RecipeParser.parse_amount('3.5 l')
        Amount(factor=Decimal('3.5'), unit='l')

        Will recognize different :ref:`number formats<Amount>`:  

        >>> RecipeParser.parse_amount('3 1/2 l')
        Amount(factor=Decimal('3.5'), unit='l')
        <BLANKLINE>
        >>> RecipeParser.parse_amount('3 ½ l')
        Amount(factor=Decimal('3.5'), unit='l')
        <BLANKLINE>
        >>> RecipeParser.parse_amount('3,5 l')
        Amount(factor=Decimal('3.5'), unit='l')

        :raises RuntimeError: If the given string can not be parsed as an amount.
        """
        # iterate over different value format
        for regexp, factor_function, group_count in RecipeParser._value_formats:
            match = re.match(r'^\s*(-?)\s*' + regexp + r'(.*)$', amount_str)
            if match:
                factor = factor_function(match)
                if match.group(1) == '-':
                    factor = -1 * factor
                unit = match.group(group_count + 2).strip()
                return Amount(factor, unit or None)
            
        raise RuntimeError("Amount must start with a number")

    def _peek_emph_paragraph(self) -> Optional[Tuple[Union[Literal['em_open'], Literal['strong_open']], str]]:
        if (
            len(self._block_tokens) < 3
            or self._block_tokens[0].type != "paragraph_open"
            or self._block_tokens[1].type != "inline"
            or self._block_tokens[2].type != "paragraph_close"
        ):
            return None
        inline_content = self._block_tokens[1].content

        inline_tokens = self._md_emph.parseInline(inline_content)[0].children or []

        RecipeParser._consume_empty_text_tokens(inline_tokens)

        emph_open_token = inline_tokens.pop(0)
        if emph_open_token.type != "em_open" and emph_open_token.type != "strong_open":
            return None

        emph_close_index = RecipeParser._get_close_index(emph_open_token, inline_tokens)
        emph_content_tokens = inline_tokens[0:emph_close_index]
        del inline_tokens[: emph_close_index + 1]

        RecipeParser._consume_empty_text_tokens(inline_tokens)

        if inline_tokens:
            return None

        return (emph_open_token.type, RecipeParser._serialize_emph_inline_tokens(emph_content_tokens))
        
    def _parse_blocks_while(self, condition: Callable[[], bool], start_line: Optional[int] = None):
        end_line = None
        while self._block_tokens and condition():
            open_token = self._consume_block()        
            assert open_token.map
            start_line = start_line or open_token.map[0]
            end_line = open_token.map[1]
        if start_line is None or end_line is None:
            return None
        return "\n".join(self._src_lines[start_line:end_line])

    def _consume_block(self):
        open = self._block_tokens.pop(0)
        if open.type.endswith("_open"):
            close_index = RecipeParser._get_close_index(open, self._block_tokens)
            del self._block_tokens[0 : close_index + 1]
        return open

    def _parse_first_emph(self, first_paragraph: str):
        inline_tokens = self._md_emph.parseInline(first_paragraph)[0].children or []

        if len(inline_tokens) and inline_tokens[0].type == "em_open":
            emph_open_token = inline_tokens.pop(0)
            emph_close_index = RecipeParser._get_close_index(emph_open_token, inline_tokens)
            emph_content_tokens = inline_tokens[:emph_close_index]
            emph_content = RecipeParser._serialize_emph_inline_tokens(emph_content_tokens)
            del inline_tokens[: emph_close_index + 1]
        else:
            emph_content = None

        rest = RecipeParser._serialize_emph_inline_tokens(inline_tokens)

        return emph_content, rest

    def _parse_wrapping_link(self, first_paragraph: str) -> Tuple[Optional[str], str]:
        p = self._md_link.parseInline(first_paragraph)
        inline_tokens = self._md_link.parseInline(first_paragraph)[0].children or []

        RecipeParser._consume_whitespace_text_tokens(inline_tokens)

        if not inline_tokens or inline_tokens[0].type != "link_open":
            return None, first_paragraph

        link_open_token = inline_tokens.pop(0)
        link_close_index = RecipeParser._get_close_index(link_open_token, inline_tokens)
        link_content_tokens = inline_tokens[:link_close_index]
        del inline_tokens[: link_close_index + 1]

        RecipeParser._consume_whitespace_text_tokens(inline_tokens)

        if inline_tokens:
            return None, first_paragraph

        link_content = "".join(token.content for token in link_content_tokens)
        return str(link_open_token.attrGet("href")), link_content

    @staticmethod
    def _consume_empty_text_tokens(inline_tokens):
        while (
            inline_tokens
            and inline_tokens[0].type == "text"
            and inline_tokens[0].content == ""
        ):
            inline_tokens.pop(0)

    
    @staticmethod
    def _consume_whitespace_text_tokens(inline_tokens):
        while (
            inline_tokens
            and inline_tokens[0].type == "text"
            and inline_tokens[0].content.isspace()
        ):
            inline_tokens.pop(0)

    @staticmethod
    def _serialize_emph_inline_tokens(emph_content_tokens):
        return "".join(token.content or token.markup for token in emph_content_tokens)

    @staticmethod
    def _get_close_index(open: Token, tokens: List[Token]):
        assert open.type.endswith("_open")
        close_type = open.type[:-5]+ "_close"
        close_index = next(
            (
                i
                for i, token in enumerate(tokens)
                if token.type == close_type and token.level == open.level
            ),
            len(tokens),
        )

        return close_index


def multiply_recipe(recipe: Recipe, multiplier: Union[Decimal, Amount]) -> Recipe:
    """
    Multiplies a recipe by the given multiplier.

    Creates a new recipe where the factor of yield and ingredient is changed according to the multiplier.

    >>> recipe = Recipe(
    ...   ingredients=[
    ...     Ingredient(name='Eggs', amount=Amount(factor=Decimal('5'), unit=None), link=None),
    ...     Ingredient(name='Butter', amount=Amount(factor=Decimal('200'), unit='g'), link=None),
    ...    ]    
    ... )
    >>> multiplied_recipe = multiply_recipe(recipe, 3)
    <BLANKLINE>
    >>> multiplied_recipe.ingredients[0]
    Ingredient(name='Eggs', amount=Amount(factor=Decimal('15'), unit=None), link=None)
    <BLANKLINE>
    >>> multiplied_recipe.ingredients[1]
    Ingredient(name='Butter', amount=Amount(factor=Decimal('600'), unit='g'), link=None)
    """
    recipe = replace(recipe, yields=[y * multiplier for y in recipe.yields if y.factor is not None])
    recipe = _multiply_ingredient_list(recipe, multiplier)
    return recipe


def get_recipe_with_yield(recipe: Recipe, required_yield: Amount) -> Recipe:
    """
    Scale the given recipe to a required yield.

    Creates a new recipe, which has the yield given by `required_yield`. A recipe can only be scaled if a yield with a matching 
    unit is present.

    :raises StopIteration: If no yield with a matching unit can be found.
    :raises RuntimeError: If required_yield or the matching yield in the recipe do not have a factor.
    """
    matching_recipe_yield = next((y for y in recipe.yields if y.unit == required_yield.unit), None)
    if matching_recipe_yield is None:
        # no unit in required amount is interpreted as "one recipe"
        if required_yield.unit is None:
            matching_recipe_yield = Amount(Decimal(1))
        else:
            raise StopIteration
    recipe = multiply_recipe(recipe, required_yield / matching_recipe_yield)
    return recipe


IL = TypeVar('IL', bound=IngredientList)

def _multiply_ingredient_list(ingredient_list: IL, multiplier: Union[Decimal, Amount]) -> IL:
    ingredients: List[Ingredient] = [_multiply_ingredient(i, multiplier) for i in ingredient_list.ingredients]
    ingredient_groups: List[IngredientGroup] = [_multiply_ingredient_list(ig, multiplier)
                                                for ig in ingredient_list.ingredient_groups]
    return replace(ingredient_list, ingredients=ingredients, ingredient_groups=ingredient_groups)


def _multiply_ingredient(ingr: Ingredient, multiplier: Union[Decimal, Amount]) -> Ingredient:
    if ingr.amount is None:
        return ingr
    return ingr * multiplier
