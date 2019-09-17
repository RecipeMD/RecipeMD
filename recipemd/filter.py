import itertools
import re
import unicodedata
from abc import ABC, abstractmethod
from functools import reduce
from typing import List, Iterable, Pattern

from pyparsing import infixNotation, QuotedString, CaselessKeyword, opAssoc, CharsNotIn, Word, Optional

from recipemd.data import Recipe


class FilterString(ABC):
    @abstractmethod
    def contained_in(self, to_search: Iterable[str]):
        pass


class SimpleFilterString(FilterString):
    contains: bool
    string: str

    def __init__(self, toks):
        self.string = toks["string"]
        self.contains = "contains" in toks

    def contained_in(self, to_search: Iterable[str]):
        to_find_caseless = self._normalize_str(self.string)
        if self.contains:
            return any(to_find_caseless in self._normalize_str(el) for el in to_search)
        else:
            return any(to_find_caseless == self._normalize_str(el) for el in to_search)

    def _normalize_str(self, text: str):
        return unicodedata.normalize("NFKD", text.strip().casefold())

    def __repr__(self):
        return f'{"~" if self.contains else ""}{self.string!r}'


class RegexFilterString(FilterString):
    regex: Pattern

    def __init__(self, toks):
        self.regex = re.compile(toks[0])

    def contained_in(self, to_search: Iterable[str]):
        return any(self.regex.search(el) for el in to_search)

    def __repr__(self):
        return f'/{self.regex.pattern}/'


class FilterElement(ABC):
    @abstractmethod
    def evaluate(self, recipe: Recipe) -> bool:
        pass


class FilterTerm(FilterElement, ABC):
    filter_string: FilterString

    def __init__(self, toks):
        self.filter_string = toks["filter_string"]


class TagFilterTerm(FilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        return self.filter_string.contained_in(recipe.tags)

    def __repr__(self):
        return f'tag:{self.filter_string!r}'


class IngredientFilterTerm(FilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        ingredient_names = (ingr.name for ingr in recipe.leaf_ingredients if ingr.name is not None)
        return self.filter_string.contained_in(ingredient_names)

    def __repr__(self):
        return f'ingr:{self.filter_string!r}'


class UnitFilterTerm(FilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        ingredient_units = (ingr.amount.unit for ingr in recipe.leaf_ingredients if ingr.amount is not None and ingr.amount.unit is not None)
        yield_units = (yield_.unit for yield_ in recipe.yields if yield_.unit is not None)
        return self.filter_string.contained_in(itertools.chain(ingredient_units, yield_units))

    def __repr__(self):
        return f'unit:{self.filter_string!r}'


class AnyFilterTerm(IngredientFilterTerm, TagFilterTerm, UnitFilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        return IngredientFilterTerm.evaluate(self, recipe) or TagFilterTerm.evaluate(self, recipe) \
               or UnitFilterTerm.evaluate(self, recipe)

    def __repr__(self):
        return f'{self.filter_string!r}'


class BooleanOperation(FilterElement, ABC):
    OPERATOR: str
    ASSOCIATIVITY: opAssoc
    ARITY: int
    operands: List[FilterElement]


class BooleanUnaryOperation(BooleanOperation, ABC):
    ARITY = 1

    def __init__(self, toks):
        self.operands = [toks[0][1]]

    def __repr__(self):
        return f'({self.OPERATOR} {self.operands[0]})'


class BooleanBinaryOperation(BooleanOperation, ABC):
    ARITY = 2

    def __init__(self, toks):
        self.operands = toks[0][0::2]

    def __repr__(self):
        op = f' {self.OPERATOR} '
        return f'({op.join([repr(oper) for oper in self.operands])})'


class BooleanNotOperation(BooleanUnaryOperation):
    OPERATOR = "not"
    ASSOCIATIVITY = opAssoc.RIGHT

    def evaluate(self, recipe: Recipe) -> bool:
        return not self.operands[0].evaluate(recipe)


class BooleanAndExpression(BooleanBinaryOperation):
    OPERATOR = "and"
    ASSOCIATIVITY = opAssoc.LEFT

    def evaluate(self, recipe: Recipe) -> bool:
        return all(oper.evaluate(recipe) for oper in self.operands)


class BooleanOrExpression(BooleanBinaryOperation):
    OPERATOR = "or"
    ASSOCIATIVITY = opAssoc.LEFT

    def evaluate(self, recipe: Recipe) -> bool:
        return any(oper.evaluate(recipe) for oper in self.operands)


class BooleanXorExpression(BooleanBinaryOperation):
    OPERATOR = "xor"
    ASSOCIATIVITY = opAssoc.LEFT

    def evaluate(self, recipe: Recipe) -> bool:
        return reduce(lambda left, right: left ^ right, [oper.evaluate(recipe) for oper in self.operands])


single_quoted_string = QuotedString('"', escChar='\\')
double_quoted_string = QuotedString("'", escChar='\\')
unquoted_string = CharsNotIn(" \t\r\n()~")
base_filter_string = single_quoted_string | double_quoted_string | unquoted_string

simple_filter_string = Optional(Word("~")).setResultsName("contains") + base_filter_string.setResultsName("string")
simple_filter_string.setParseAction(SimpleFilterString)

regex_filter_string = QuotedString('/', escChar='\\')
regex_filter_string.setParseAction(RegexFilterString)

filter_string = regex_filter_string | simple_filter_string
filter_string.setParseAction(lambda toks: toks[0])

tag_filter_term = "tag:" + filter_string.setResultsName("filter_string")
tag_filter_term.setParseAction(TagFilterTerm)

ingredient_filter_term = "ingr:" + filter_string.setResultsName("filter_string")
ingredient_filter_term.setParseAction(IngredientFilterTerm)

unit_filter_term = ("unit:" + filter_string.setResultsName("filter_string"))
unit_filter_term.setParseAction(UnitFilterTerm)

any_filter_term = filter_string.setResultsName("filter_string")
# using addParserAction because filter_string already has a parser action
any_filter_term.addParseAction(AnyFilterTerm)

filter_term = ingredient_filter_term | tag_filter_term | unit_filter_term | any_filter_term

filter_expr = infixNotation(filter_term, [
    (CaselessKeyword(op.OPERATOR), op.ARITY, op.ASSOCIATIVITY, op)
    for op in [BooleanNotOperation, BooleanAndExpression, BooleanXorExpression, BooleanOrExpression]
])

if __name__ == "__main__":
    filter_expr.runTests('''
        ingr:/.*/ or /.+/
    ''')
