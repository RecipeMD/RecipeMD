from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

import CommonMark
from CommonMark.node import Node
from CommonMarkExtensions.plaintext import CommonMarkToCommonMarkRenderer


@dataclass
class IngredientGroup:
    prefix: Optional[str] = None
    ingredients: List[Ingredient] = field(default_factory=list)

    def __repr__(self):
        ingredients_repr = "\n".join(repr(i) for i in self.ingredients)
        if self.prefix is not None:
            return f'{self.prefix}\n\n{ingredients_repr}'
        return ingredients_repr

@dataclass
class Ingredient:
    name: str
    amount: Optional[Decimal] = None
    unit: Optional[str] = None

    def __repr__(self):
        if self.amount is not None and self.unit is not None:
            return f'- *{self.amount} {self.unit}* {self.name}'
        elif self.amount is not None:
            return f'- *{self.amount}* {self.name}'
        elif self.unit is not None:
            return f'- *{self.unit}* {self.name}'
        else:
            return f'- {self.name}'


@dataclass
class Recipe:
    title: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    servings: Optional[int] = None
    ingredient_groups: List[IngredientGroup] = field(default_factory=list)
    instructions: Optional[str] = None

    def __repr__(self):
        rep = ""
        rep += f'# {self.title}\n\n'
        if self.description is not None:
            rep += f'{self.description}\n\n'
        if len(self.tags) > 0:
            rep += f'*{", ".join(self.tags)}*\n\n'
        rep += f'---\n\n'
        rep += "\n\n".join(repr(g) for g in self.ingredient_groups)
        if self.instructions is not None:
            rep += f'\n\n---\n\n'
            rep += self.instructions
        return rep


class RecipeParser:
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

        parser = CommonMark.Parser()
        ast = parser.parse(src)

        self.current = ast.first_child

        self._parse_title()
        self._parse_description()
        self._parse_tags()

        if self.current is not None and self.current.t == 'thematic_break':
            self._next_node()
        else:
            # TODO this divider is required, but we might just continue anyways?
            raise RuntimeError("Invalid, expected divider before ingredients")

        self._parse_ingredients()

        if self.current is not None and self.current.t == 'thematic_break':
            self._next_node()

        self.recipe.instructions = self._get_source_until()

        return self.recipe

    def _parse_title(self):
        if self.current is not None and self.current.t == 'heading' and self.current.level == 1:
            self.recipe.title = self._get_node_source(self.current.first_child)
            self._next_node()
        else:
            # TODO title is required according to spec, maybe the parser might be more foregiving?
            raise RuntimeError("Invalid, title required")

    def _parse_description(self):
        result = self._get_source_until(lambda n: n.t != 'thematic_break' and not self._is_tags(n))
        self.recipe.description = result

    def _parse_tags(self):
        if self.current is not None and self._is_tags(self.current):
            tags_text = self._get_node_source(self.current.first_child.first_child)
            self.recipe.tags = [t.strip() for t in tags_text.split(',')]
            self._next_node()

    def _parse_ingredients(self):
        while self.current is not None and self.current.t != 'thematic_break':
            group_prefix = self._get_source_until(lambda n: n.t != 'list' and n.t != 'thematic_break')
            group_children = None
            if self.current is not None and self.current.t == 'list':
                group_children = self._parse_ingredient_list_node()

            if group_prefix is not None or group_children is not None:
                self.recipe.ingredient_groups.append(IngredientGroup(prefix=group_prefix, ingredients=group_children))

    def _parse_ingredient_list_node(self):
        ingredients = []
        self._enter_node()
        while self.current is not None:
            ingredients.append(self._parse_ingredient())
            self._next_node()
        self._exit_node()
        self._next_node()
        return ingredients

    def _parse_ingredient(self):
        self._enter_node()

        amount = None
        unit = None
        first_paragraph = None

        if self.current.t == 'paragraph' and self.current.first_child.t == 'emph':
            self._enter_node()
            self._enter_node()
            amount, unit = self._parse_amount(self._get_node_source(self.current))
            self._exit_node()
            self._next_node()
            while self.current is not None:
                if first_paragraph is None:
                    first_paragraph = ""
                first_paragraph += self._get_node_source(self.current)
                self._next_node()
            self._exit_node()
            self._next_node()

        following_paragraphs = self._get_source_until()

        if first_paragraph is not None and following_paragraphs is not None:
            name = first_paragraph + "\n\n" + following_paragraphs
        elif first_paragraph is not None:
            name = first_paragraph
        elif following_paragraphs is not None:
            name = following_paragraphs
        else:
            raise RuntimeError("No ingredient name!")
        name = name.strip()

        self._exit_node()

        return Ingredient(name=name, amount=amount, unit=unit)

    def _parse_amount(self, amount_str):
        match = re.match(r'^\s*(\d+)\s+(\d+)\s*/\s*(\d+)(.*)$', amount_str)
        if match:
            amount = Decimal(match.group(1)) + (Decimal(match.group(2)) / Decimal(match.group(3)))
            unit = match.group(4).strip()
            return amount, unit

        match = re.match(r'^\s*(\d+)\s*/\s*(\d+)(.*)$', amount_str)
        if match:
            amount = (Decimal(match.group(1)) / Decimal(match.group(2)))
            unit = match.group(3).strip()
            return amount, unit

        match = re.match(r'^\s*(\d*)[.,](\d+)(.*)$', amount_str)
        if match:
            amount = Decimal(match.group(1) + '.' + match.group(2))
            unit = match.group(3).strip()
            return amount, unit

        match = re.match(r'^\s*(\d+)(.*)$', amount_str)
        if match:
            amount = Decimal(match.group(1))
            unit = match.group(2).strip()
            return amount, unit

        return None, amount_str.strip()


    def _is_tags(self, ast_node: Node):
        return ast_node.t == 'paragraph' and ast_node.first_child.t == 'emph' and ast_node.first_child == ast_node.last_child

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

    def _get_sourcepos_source(self, sourcepos):
        start_line = sourcepos[0][0] - 1
        end_line = sourcepos[1][0]

        first_line_start_offset = sourcepos[0][1] - 1
        last_line_end_offset = sourcepos[1][1]

        lines = self.src.splitlines()[start_line:end_line]
        lines[0] = lines[0][first_line_start_offset:]
        lines[-1] = lines[-1][:last_line_end_offset]

        return "\n".join(lines)


if __name__ == "__main__":
    #src = open('examples/schwarzbierbrot.md', 'r').read()
    src = open('examples/griechischer_kartoffeltopf.md', 'r').read()

    rp = RecipeParser()
    r = rp.parse(src)
    print(r)
