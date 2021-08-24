"""
Defines the RecipeMD data structures, provides parser, serializer and recipe scaling functions.
"""
#from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import List, Optional, Union, Dict, Generator, TypeVar

import commonmark
from commonmark.node import Node
from recipemd._vendor.commonmark_extensions.plaintext import CommonMarkToCommonMarkRenderer
from dataclasses_json import dataclass_json, config

__all__ = ['RecipeParser', 'RecipeSerializer', 'multiply_recipe', 'get_recipe_with_yield',
           'Recipe', 'Ingredient', 'IngredientGroup', 'Amount', 'IngredientList']


T = TypeVar('T')


@dataclass_json
@dataclass(frozen=True)
class IngredientList:
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


@dataclass_json
@dataclass(frozen=True)
class IngredientGroup(IngredientList):
    title: Optional[str] = None


@dataclass_json
@dataclass(frozen=True)
class Amount:
    factor: Optional[Decimal] = field(
        default=None,
        # decoder is workaround for https://github.com/lidatong/dataclasses-json/issues/137
        metadata=config(decoder=lambda val: Decimal(val) if val is not None else None)
    )
    unit: Optional[str] = None

    def __post_init__(self):
        if self.factor is None and self.unit is None:
            raise TypeError(f"Factor and unit may not both be None")


@dataclass_json
@dataclass(frozen=True)
class Ingredient:
    name: str
    amount: Optional[Amount] = None
    link: Optional[str] = None


@dataclass_json
@dataclass(frozen=True)
class Recipe(IngredientList):
    title: Optional[str] = None
    description: Optional[str] = None
    yields: List[Amount] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    instructions: Optional[str] = None


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
        if amount.factor is not None and amount.unit is not None:
            return f'{RecipeSerializer._normalize_factor(amount.factor, rounding=rounding)} {amount.unit}'
        if amount.factor is not None:
            return f'{RecipeSerializer._normalize_factor(amount.factor, rounding=rounding)}'
        if amount.unit is not None:
            return f'{amount.unit}'

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

    src: Optional[str]
    recipe: Optional[Recipe]
    parents: List[Node]
    current: Node

    def __init__(self):
        self.src = None
        self.recipe = None
        self.parents = []
        self.current = None

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
        self.src = src
        self.recipe = Recipe(title=None)

        parser = commonmark.Parser()
        ast = parser.parse(src)

        self.current = ast.first_child

        self._parse_title()
        self._parse_description()
        self._parse_tags_and_yields()

        if self.current is not None and self.current.t == 'thematic_break':
            self._next_node()
        else:
            # TODO this divider is required, but we might just continue anyways?
            raise RuntimeError(f"Invalid, expected divider before ingredient list, got {self.current and self.current.t} instead")

        self._parse_ingredients()

        if self.current is not None:
            if self.current.t == 'thematic_break':
                self._next_node()
            else:
                # TODO this divider is required, but we might just continue anyways?
                raise RuntimeError(f"Invalid, expected divider before ingredient list, got {self.current and self.current.t} instead")

        self.recipe = replace(self.recipe, instructions=self._get_source_until())

        return self.recipe

    def _parse_title(self):
        if self.current is not None and self.current.t == 'heading' and self.current.level == 1:
            self.recipe = replace(self.recipe, title=self._get_current_node_children_source())
            self._next_node()
        else:
            # TODO title is required according to spec, maybe the parser might be more foregiving?
            raise RuntimeError(f"Invalid, title (heading with level 1) required, got "
                               f"{self.current and self.current.t if not self.current or self.current.t != 'heading' else f'level {self.current.level }'} "
                               f"instead")

    def _parse_description(self):
        result = self._get_source_until(lambda n: n.t != 'thematic_break' and not self._is_tags(n)
                                        and not self._is_yields(n))
        self.recipe = replace(self.recipe, description=result)

    def _parse_tags_and_yields(self):
        while self.current is not None and (self._is_tags(self.current) or self._is_yields(self.current)):
            if self._is_tags(self.current):
                if self.recipe.tags:
                    raise RuntimeError(f"Invalid, tags may not be specified multiple times")
                self._enter_node()
                tags_text = self._get_current_node_children_source()
                self._exit_node()
                self.recipe = replace(self.recipe, tags=[t.strip() for t in self._list_split.split(tags_text)])
            else:
                if self.recipe.yields:
                    raise RuntimeError(f"Invalid, tags may not be specified multiple times")
                self._enter_node()
                yields_text = self._get_current_node_children_source()
                self._exit_node()
                self.recipe = replace(self.recipe, yields=[self.parse_amount(t.strip()) for t in self._list_split.split(yields_text)])
            self._next_node()

    def _parse_ingredients(self):
        while self.current is not None and (self.current.t == 'heading' or self.current.t == 'list'):
            if self.current.t == 'heading':
                self._parse_ingredient_groups(self.recipe.ingredient_groups, parent_level=-1)
            elif self.current is not None and self.current.t == 'list':
                self._parse_ingredient_list_node(self.recipe.ingredients)

    def _parse_ingredient_groups(self, ingredient_groups: List['IngredientGroup'], parent_level):
        while self.current is not None and self.current.t == 'heading':
            level = self.current.level
            if level <= parent_level:
                return

            group = IngredientGroup(title=self._get_current_node_children_source())
            self._next_node()

            if self.current is not None and self.current.t == 'list':
                self._parse_ingredient_list_node(group.ingredients)

            ingredient_groups.append(group)

            self._parse_ingredient_groups(group.ingredient_groups, parent_level=level)

    def _parse_ingredient_list_node(self, ingredients: List['Ingredient']):
        self._enter_node()
        while self.current is not None:
            ingredients.append(self._parse_ingredient())
            self._next_node()
        self._exit_node()
        self._next_node()

    def _parse_ingredient(self):
        self._enter_node()

        amount = None
        first_paragraph = None

        can_have_link = True
        has_link = False
        link_destination = None
        link_text = None

        if self.current is not None and self.current.t == 'paragraph':
            # enter paragraph
            self._enter_node()

            if self.current.t == 'emph':
                # enter emph
                self._enter_node()
                amount = self.parse_amount(self._get_node_source(self.current))
                # leave emph
                self._exit_node()
                # parse rest of first paragraph
                self._next_node()

            while self.current is not None:
                if first_paragraph is None:
                    first_paragraph = ""
                node_source = self._get_node_source(self.current)

                if can_have_link:
                    # to have a link, the first paragraph may only contain space and one link
                    if not has_link and self.current.t == 'link':
                        link_destination = self.current.destination
                        link_text = self._get_current_node_children_source()
                        has_link = True
                    elif not node_source.isspace():
                        can_have_link = False

                first_paragraph += node_source
                self._next_node()

            # leave first paragraph
            self._exit_node()
            self._next_node()

        following_paragraphs = self._get_source_until()

        if following_paragraphs is not None and not following_paragraphs.isspace():
            can_have_link = False

        if can_have_link and has_link:
            name = link_text
        elif first_paragraph is not None and following_paragraphs is not None:
            name = first_paragraph + "\n\n" + following_paragraphs
        elif first_paragraph is not None:
            name = first_paragraph
        elif following_paragraphs is not None:
            name = following_paragraphs
        else:
            raise RuntimeError("No ingredient name!")
        name = name.strip()

        self._exit_node()

        return Ingredient(name=name, amount=amount, link=link_destination)

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
            
        unit = amount_str.strip()
        return Amount(None, unit) if unit else None

    def _is_tags(self, ast_node: Node):
        return ast_node.t == 'paragraph' and ast_node.first_child.t == 'emph' \
               and ast_node.first_child == ast_node.last_child

    def _is_yields(self, ast_node: Node):
        return ast_node.t == 'paragraph' and ast_node.first_child.t == 'strong' \
               and ast_node.first_child == ast_node.last_child

    def _next_node(self):
        self.current = self.current.nxt

    def _enter_node(self):
        self.parents.append(self.current)
        self.current = self.current.first_child

    def _exit_node(self):
        self.current = self.parents.pop()

    def _get_source_until(self, predicate=None):
        if self.current is None:
            return None

        start = self.current.sourcepos[0]
        end = None

        while self.current is not None and (predicate is None or predicate(self.current)):
            end = self.current.sourcepos[1]
            self._next_node()

        if end is not None:
            return self._get_sourcepos_source_lines((start, end))

        return None

    def _get_node_source(self, ast_node):
        if ast_node.sourcepos is not None:
            return self._get_sourcepos_source_lines(ast_node.sourcepos)
        if ast_node.literal is not None:
            return ast_node.literal
        return CommonMarkToCommonMarkRenderer().render(ast_node)

    def _get_current_node_children_source(self):
        source = ""
        if self.current.first_child is not None:
            self._enter_node()
            while self.current is not None:
                source += self._get_node_source(self.current)
                self._next_node()
            self._exit_node()
        return source

    def _get_sourcepos_source_lines(self, sourcepos):
        start_line = sourcepos[0][0] - 1
        end_line = sourcepos[1][0]

        lines = self.src.splitlines()[start_line:end_line]

        return "\n".join(lines)


def multiply_recipe(recipe: Recipe, multiplier: Decimal) -> Recipe:
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
    recipe = replace(recipe, yields=[replace(y, factor=y.factor * multiplier) for y in recipe.yields if y.factor is not None])
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
    if required_yield.factor is None:
        raise RuntimeError("Required yield must contain a factor")
    matching_recipe_yield = next((y for y in recipe.yields if y.unit == required_yield.unit), None)
    if matching_recipe_yield is None:
        # no unit in required amount is interpreted as "one recipe"
        if required_yield.unit is None:
            matching_recipe_yield = Amount(Decimal(1))
        else:
            raise StopIteration
    if matching_recipe_yield.factor is None:
        raise RuntimeError(f"Recipe yield with matching unit must contain a factor")
    recipe = multiply_recipe(recipe, required_yield.factor / matching_recipe_yield.factor)
    return recipe


def _multiply_ingredient_list(ingredient_list: T, multiplier: Decimal) -> T:
    ingredients: List[Ingredient] = [_multiply_ingredient(i, multiplier) for i in ingredient_list.ingredients]
    ingredient_groups: List[IngredientGroup] = [_multiply_ingredient_list(ig, multiplier)
                                                for ig in ingredient_list.ingredient_groups]
    return replace(ingredient_list, ingredients=ingredients, ingredient_groups=ingredient_groups)


def _multiply_ingredient(ingr: Ingredient, multiplier: Decimal) -> Ingredient:
    if ingr.amount is None:
        return ingr
    return replace(ingr, amount=replace(
        ingr.amount,
        factor=ingr.amount.factor*multiplier if ingr.amount.factor is not None else None
    ))
