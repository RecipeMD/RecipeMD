"""
Defines the RecipeMD data structures, provides parser, serializer and recipe scaling functions.
"""
#from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Callable, Generator, List, Optional, Tuple, TypeVar, Union

from dataclasses_json import config, dataclass_json
from markdown_it import MarkdownIt
from markdown_it.token import Token
from typing_extensions import Literal

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

    md_block: MarkdownIt
    md_emph: MarkdownIt
    md_link: MarkdownIt

    src: Optional[str]
    src_lines: List[str]
    block_tokens: List[Token]


    def __init__(self):
        self.md_block = MarkdownIt()
        self.md_block.disable("reference")
        self.md_block.disable(
            names=[*self.md_block.get_all_rules()["inline"], *self.md_block.get_all_rules()["inline2"]]
        )

        self.md_emph = MarkdownIt()
        self.md_emph.disable(self.md_emph.get_all_rules()["inline"])
        self.md_emph.enable("emphasis")

        self.md_link = MarkdownIt()
        self.md_link.disable(self.md_link.get_all_rules()["inline"])
        self.md_link.enable("link")

        self.src = None
        self.src_lines = []
        self.block_tokens = []

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
        self.src_lines = src.splitlines()

        self.block_tokens = self.md_block.parse(src)

        title = self._parse_title()
        description = self._parse_description()
        tags, yields = self._parse_tags_and_yields()

        if self.block_tokens and self.block_tokens[0].type == "hr":
            self.block_tokens.pop(0)
        else:
            # TODO this hr is required, but we might just continue anyways?
            raise RuntimeError(f"Invalid, expected hr before ingredient list, got {self.block_tokens[0] and self.block_tokens[0].type if self.block_tokens else None} instead")

        ingredients, ingredient_groups = self._parse_ingredients()

        if self.block_tokens and self.block_tokens[0].type == "hr":
            self.block_tokens.pop(0)
        elif self.block_tokens:
            # TODO this hr is required, but we might just continue anyways?
            raise RuntimeError(f"Invalid, expected hr before instructions, got {self.block_tokens[0] and self.block_tokens[0].type} instead")

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
        if not self.block_tokens:
            raise RuntimeError(
                f"Invalid, title (heading_open with level h1) required, got None instead"
            )

        heading_open_token = self.block_tokens.pop(0)

        # TODO title is required according to spec, maybe the parser might be more forgiving?
        if heading_open_token.type != "heading_open":
            raise RuntimeError(
                f"Invalid, title (heading_open with level h1) required, got {heading_open_token.type} instead"
            )
        if heading_open_token.tag != "h1":
            raise RuntimeError(
                f"Invalid, title (heading_open with level h1) required, got level {heading_open_token.tag} instead"
            )

        heading_content_token = self.block_tokens.pop(0)
        assert self.block_tokens.pop(0).type == "heading_close"

        return heading_content_token.content

    def _parse_description(self):
        return self._parse_blocks_while(lambda: (self.block_tokens[0].type != "hr") and self._peek_emph_paragraph() is None)

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
            del self.block_tokens[:3]            
            peeked_emph_paragraph = self._peek_emph_paragraph()
        return tags, yields


    def _parse_ingredients(self):
        ingredients: List[Ingredient] = []
        ingredient_groups: List[IngredientGroup] = []
        while self.block_tokens and (
            self.block_tokens[0].type == "heading_open" 
            or self.block_tokens[0].type == "bullet_list_open"
            or self.block_tokens[0].type == "ordered_list_open"
        ):
            if self.block_tokens[0].type == 'heading_open':
                self._parse_ingredient_groups(ingredient_groups, parent_level=-1)
                pass
            else:
                self._parse_ingredient_list(ingredients)
        return ingredients, ingredient_groups

    def _parse_ingredient_groups(self, ingredient_groups: List['IngredientGroup'], parent_level):
        while self.block_tokens and (
            self.block_tokens[0].type == "heading_open" 
        ):
            level = int(self.block_tokens[0].tag.lstrip('h'))
            if level <= parent_level:
                return

            self.block_tokens.pop(0)
            heading_content_token = self.block_tokens.pop(0)
            assert self.block_tokens.pop(0).type == "heading_close"

            group = IngredientGroup(title=heading_content_token.content)
            if self.block_tokens and (self.block_tokens[0].type == "bullet_list_open" or self.block_tokens[0].type == "ordered_list_open"):
                self._parse_ingredient_list(group.ingredients)

            ingredient_groups.append(group)

            self._parse_ingredient_groups(group.ingredient_groups, parent_level=level)

    def _parse_ingredient_list(self, ingredients: List['Ingredient']):
        while self.block_tokens and (
            self.block_tokens[0].type == "bullet_list_open"
            or self.block_tokens[0].type == "ordered_list_open"
        ):
            list_open = self.block_tokens.pop(0)

            list_close_index = RecipeParser._get_close_index(list_open, self.block_tokens)
            list_close = self.block_tokens[list_close_index]
            while self.block_tokens[0].type == "list_item_open":
                ingredients.append(self._parse_ingredient())
            assert self.block_tokens.pop(0) == list_close

    def _parse_ingredient(self) -> 'Ingredient':
        list_item_open = self.block_tokens.pop(0)
        assert list_item_open.type == "list_item_open"


        continuation_start_line = None
        first_paragraph_content = None
        if self.block_tokens and self.block_tokens[0].type == "paragraph_open":
            first_paragraph_open = self.block_tokens.pop(0)
            first_paragraph_content = self.block_tokens.pop(0)
            first_paragraph_close_index = RecipeParser._get_close_index(
                first_paragraph_open, self.block_tokens
            )
            del self.block_tokens[: first_paragraph_close_index + 1]
            if first_paragraph_open.map:
                continuation_start_line =  first_paragraph_open.map[1]

        end_index = RecipeParser._get_close_index(list_item_open, self.block_tokens)
        list_item_close = self.block_tokens[end_index]

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

        name_continuation = self._parse_blocks_while(lambda: self.block_tokens[0] != list_item_close, start_line=continuation_start_line)
        if name_continuation:
            name += "\n" + name_continuation

        assert self.block_tokens.pop(0) == list_item_close

        if not name:
            raise RuntimeError("No ingredient name!")
        name = name.strip()

        return Ingredient(name=name, amount=RecipeParser.parse_amount(amount) if amount is not None else None, link=link)

    def _parse_instructions(self):
        if not self.block_tokens:
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
    def parse_amount(amount_str: str) -> Union[Amount, None]:
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

    def _peek_emph_paragraph(self) -> Optional[Tuple[Union[Literal['em_open'], Literal['strong_open']], str]]:
        if (
            len(self.block_tokens) < 3
            or self.block_tokens[0].type != "paragraph_open"
            or self.block_tokens[1].type != "inline"
            or self.block_tokens[2].type != "paragraph_close"
        ):
            return None
        inline_content = self.block_tokens[1].content

        inline_tokens = self.md_emph.parseInline(inline_content)[0].children or []

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
        while self.block_tokens and condition():
            open_token = self._consume_block()        
            assert open_token.map
            start_line = start_line or open_token.map[0]
            end_line = open_token.map[1]
        if start_line is None or end_line is None:
            return None
        return "\n".join(self.src_lines[start_line:end_line])

    def _consume_block(self):
        open = self.block_tokens.pop(0)
        if open.type.endswith("_open"):
            close_index = RecipeParser._get_close_index(open, self.block_tokens)
            del self.block_tokens[0 : close_index + 1]
        return open

    def _parse_first_emph(self, first_paragraph: str):
        inline_tokens = self.md_emph.parseInline(first_paragraph)[0].children or []

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
        p = self.md_link.parseInline(first_paragraph)
        inline_tokens = self.md_link.parseInline(first_paragraph)[0].children or []

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
