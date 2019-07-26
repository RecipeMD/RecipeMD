from __future__ import annotations

import copy
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from pprint import pprint
from typing import List, Optional, Union

import commonmark
from commonmark.node import Node
from commonmark_extensions.plaintext import CommonMarkToCommonMarkRenderer

__all__ = ['Amount', 'IngredientGroup', 'Ingredient', 'Recipe', 'RecipeParser', 'RecipeSerializer', 'multiply_recipe',
           'get_recipe_with_yield']


@dataclass
class IngredientGroup:
    title: Optional[str] = None
    children: List[Union[Ingredient, IngredientGroup]] = field(default_factory=list)


@dataclass
class Amount:
    factor: Optional[Decimal] = None
    unit: Optional[str] = None

    def __post_init__(self):
        if self.factor is None and self.unit is None:
            raise TypeError(f"Factor and unit may not both be None")


@dataclass
class Ingredient:
    name: str
    amount: Optional[Amount] = None
    link: Optional[str] = None


@dataclass
class Recipe:
    title: str
    description: Optional[str] = None
    yields: List[Amount] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    ingredients: List[Union[Ingredient, IngredientGroup]] = field(default_factory=list)
    instructions: Optional[str] = None

    @property
    def leaf_ingredients(self) -> List[Ingredient]:
        yield from self._get_leaf_ingredients(self.ingredients)

    def _get_leaf_ingredients(self, ingredients: List[Union[Ingredient, IngredientGroup]]):
        for ingr in ingredients:
            if isinstance(ingr, IngredientGroup):
                yield from self._get_leaf_ingredients(ingr.children)
            else:
                yield ingr


class RecipeSerializer:
    def serialize(self, recipe: Recipe, *, rounding: Optional[int]=None):
        rep = ""
        rep += f'# {recipe.title}\n\n'
        if recipe.description is not None:
            rep += f'{recipe.description}\n\n'
        if len(recipe.tags) > 0:
            rep += f'*{", ".join(recipe.tags)}*\n\n'
        if len(recipe.yields) > 0:
            rep += f'**{", ".join(self._serialize_amount(a, rounding=rounding) for a in recipe.yields)}**\n\n'
        rep += f'---\n\n'
        rep += ("\n".join(self._serialize_ingredient(g, 2, rounding=rounding) for g in recipe.ingredients)).strip()
        if recipe.instructions is not None:
            rep += f'\n\n---\n\n'
            rep += recipe.instructions
        return rep

    def _serialize_ingredient(self, ingredient, level, *, rounding: Optional[int]=None):
        if isinstance(ingredient, IngredientGroup):
            return f'\n{"#" * level} {ingredient.title}\n\n'\
                   + "\n".join(self._serialize_ingredient(i, level+1, rounding=rounding) for i in ingredient.children)
        else:
            if ingredient.amount is not None:
                return f'- *{self._serialize_amount(ingredient.amount, rounding=rounding)}* {self._serialize_ingredient_text(ingredient)}'
            return f'- {self._serialize_ingredient_text(ingredient)}'

    @staticmethod
    def _serialize_ingredient_text(ingredient):
        if ingredient.link:
            return f'[{ingredient.name}]({ingredient.link})'
        return ingredient.name

    @staticmethod
    def _serialize_amount(amount, *, rounding: Optional[int]=None):
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
    _list_split = re.compile("(?<!\d),|,(?!\d)")

    src: Optional[str]
    recipe: Optional[Recipe]
    parents: List[Node]
    current: Node

    def __init__(self):
        self.src = None
        self.recipe = None
        self.parents = []
        self.current = None

    def parse(self, src):
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

        self.recipe.instructions = self._get_source_until()

        return self.recipe

    def _parse_title(self):
        if self.current is not None and self.current.t == 'heading' and self.current.level == 1:
            self.recipe.title = self._get_current_node_children_source()
            self._next_node()
        else:
            # TODO title is required according to spec, maybe the parser might be more foregiving?
            raise RuntimeError(f"Invalid, title (heading with level 1) required, got "
                               f"{self.current and self.current.t if not self.current or self.current.t != 'heading' else f'level {self.current.level }'} "
                               f"instead")

    def _parse_description(self):
        result = self._get_source_until(lambda n: n.t != 'thematic_break' and not self._is_tags(n)
                                        and not self._is_yields(n))
        self.recipe.description = result

    def _parse_tags_and_yields(self):
        while self.current is not None and (self._is_tags(self.current) or self._is_yields(self.current)):
            if self._is_tags(self.current):
                self._enter_node()
                tags_text = self._get_current_node_children_source()
                self._exit_node()
                self.recipe.tags = [t.strip() for t in self._list_split.split(tags_text)]
            else:
                self._enter_node()
                yields_text = self._get_current_node_children_source()
                self._exit_node()
                self.recipe.yields = [self.parse_amount(t.strip()) for t in self._list_split.split(yields_text)]
            self._next_node()

    def _parse_ingredients(self):
        while self.current is not None and (self.current.t == 'heading' or self.current.t == 'list'):
            if self.current.t == 'heading':
                self._parse_ingredient_groups(self.recipe.ingredients, parent_level=-1)
            elif self.current is not None and self.current.t == 'list':
                self._parse_ingredient_list_node(self.recipe.ingredients)

    def _parse_ingredient_groups(self, ingredients, parent_level):
        while self.current is not None and self.current.t == 'heading':
            level = self.current.level
            if level <= parent_level:
                return

            group = IngredientGroup()
            group.title = self._get_current_node_children_source()
            self._next_node()

            if self.current is not None and self.current.t == 'list':
                self._parse_ingredient_list_node(group.children)

            ingredients.append(group)

            self._parse_ingredient_groups(group.children, parent_level=level)

    def _parse_ingredient_list_node(self, ingredients):
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

        if self.current.t == 'paragraph':
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

    @staticmethod
    def parse_amount(amount_str: str) -> Amount:
        # improper fraction (1 1/2)
        match = re.match(r'^\s*(\d+)\s+(\d+)\s*/\s*(\d+)(.*)$', amount_str)
        if match:
            factor = Decimal(match.group(1)) + (Decimal(match.group(2)) / Decimal(match.group(3)))
            unit = match.group(4).strip()
            return Amount(factor, unit or None)

        # improper fraction with unicode vulgar fraction (1 ½)
        match = re.match(r'^\s*(\d+)\s+([\u00BC-\u00BE\u2150-\u215E])(.*)$', amount_str)
        if match:
            try:
                factor = Decimal(match.group(1)) + Decimal(unicodedata.numeric(match.group(2)))
                unit = match.group(3).strip()
                return Amount(factor, unit or None)
            except ValueError:
                pass

        # proper fraction (5/6)
        match = re.match(r'^\s*(\d+)\s*/\s*(\d+)(.*)$', amount_str)
        if match:
            factor = (Decimal(match.group(1)) / Decimal(match.group(2)))
            unit = match.group(3).strip()
            return Amount(factor, unit or None)

        # proper fraction with unicode vulgar fraction (⅚)
        match = re.match(r'^\s*([\u00BC-\u00BE\u2150-\u215E])(.*)$', amount_str)
        if match:
            try:
                factor = Decimal(unicodedata.numeric(match.group(1)))
                unit = match.group(2).strip()
                return Amount(factor, unit or None)
            except ValueError:
                pass

        # decimal (5,4 or 5.6)
        match = re.match(r'^\s*(\d*)[.,](\d+)(.*)$', amount_str)
        if match:
            factor = Decimal(match.group(1) + '.' + match.group(2))
            unit = match.group(3).strip()
            return Amount(factor, unit or None)

        # integer
        match = re.match(r'^\s*(\d+)(.*)$', amount_str)
        if match:
            factor = Decimal(match.group(1))
            unit = match.group(2).strip()
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
            return self._get_sourcepos_source((start, end))

        return None

    def _get_node_source(self, ast_node):
        if ast_node.sourcepos is not None:
            return self._get_sourcepos_source(ast_node.sourcepos)
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

    def _get_sourcepos_source(self, sourcepos):
        start_line = sourcepos[0][0] - 1
        end_line = sourcepos[1][0]

        first_line_start_offset = sourcepos[0][1] - 1
        last_line_end_offset = sourcepos[1][1]

        lines = self.src.splitlines()[start_line:end_line]
        lines[0] = lines[0][first_line_start_offset:]
        lines[-1] = lines[-1][:last_line_end_offset]

        return "\n".join(lines)


def multiply_recipe(base_recipe: Recipe, multiplier: Decimal):
    recipe = copy.deepcopy(base_recipe)
    for yield_ in recipe.yields:
        if yield_.factor:
            yield_.factor *= multiplier
    _multiply_ingredients(recipe.ingredients, multiplier)
    return recipe


def get_recipe_with_yield(recipe, required_yield):
    matching_recipe_yield = next((y for y in recipe.yields if y.unit == required_yield.unit), None)
    if matching_recipe_yield is None:
        # no unit in required amount is interpreted as "one recipe"
        if required_yield.unit is None:
            matching_recipe_yield = Amount(Decimal(1))
        else:
            raise StopIteration
    recipe = multiply_recipe(recipe, required_yield.factor / matching_recipe_yield.factor)
    return recipe


def _multiply_ingredients(ingredients: List[Union[Ingredient, IngredientGroup]], multiplier: Decimal):
    for ingr in ingredients:
        if hasattr(ingr, 'amount') and ingr.amount is not None and ingr.amount.factor is not None:
            ingr.amount.factor *= multiplier
        if hasattr(ingr, 'children'):
            _multiply_ingredients(ingr.children, multiplier)


if __name__ == "__main__":
    # src = open('examples/schwarzbierbrot.md', 'r').read()
    # src = open('examples/griechischer_kartoffeltopf.md', 'r').read()
    src = open('examples/example_menu.md', 'r').read()

    rp = RecipeParser()
    r = rp.parse(src)
    pprint(r.ingredients)
    #rs = RecipeSerializer()
    #print(rs.serialize(r))
