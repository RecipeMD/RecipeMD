import itertools
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import reduce
from pprint import pprint
from typing import List, Iterable, Pattern, Optional, ClassVar, Any

import pyparsing
from pyparsing import infixNotation, QuotedString, CaselessKeyword, opAssoc, CharsNotIn, ParserElement, Or, Combine, \
    ParseResults

from recipemd.data import Recipe


@dataclass(frozen=True)
class ASTElement(ABC):
    @classmethod
    @abstractmethod
    def create_from_tokens(cls, toks):
        pass


@dataclass(frozen=True)
class FilterString(ASTElement, ABC):
    @abstractmethod
    def contained_in(self, to_search: Iterable[str]):
        pass


@dataclass(frozen=True)
class SimpleFilterString(FilterString):
    contains: bool
    string: str

    @classmethod
    def create_from_tokens(cls, toks: ParseResults):
        return cls(string=toks["string"], contains="contains" in toks)

    def contained_in(self, to_search: Iterable[str]):
        to_find_caseless = self._normalize_str(self.string)
        if self.contains:
            return any(to_find_caseless in self._normalize_str(el) for el in to_search)
        else:
            return any(to_find_caseless == self._normalize_str(el) for el in to_search)

    def _normalize_str(self, text: str):
        return unicodedata.normalize("NFKD", text.strip().casefold())

    def __str__(self):
        return f'{"~" if self.contains else ""}{self.string!r}'


@dataclass(frozen=True)
class RegexFilterString(FilterString):
    regex: Pattern

    @classmethod
    def create_from_tokens(cls, toks: ParseResults):
        return cls(regex=re.compile(toks[0]))

    def contained_in(self, to_search: Iterable[str]):
        return any(self.regex.search(el) for el in to_search)

    def __str__(self):
        return f'/{self.regex.pattern}/'


@dataclass(frozen=True)
class FilterElement(ASTElement, ABC):
    @abstractmethod
    def evaluate(self, recipe: Recipe) -> bool:
        pass


@dataclass(frozen=True)
class FilterTerm(FilterElement, ABC):
    filter_string: FilterString

    @classmethod
    def create_from_tokens(cls, toks: ParseResults):
        return cls(filter_string=toks["filter_string"])


@dataclass(frozen=True)
class TagFilterTerm(FilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        return self.filter_string.contained_in(recipe.tags)

    def __str__(self):
        return f'tag:{self.filter_string!r}'


@dataclass(frozen=True)
class IngredientFilterTerm(FilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        ingredient_names = (ingr.name for ingr in recipe.leaf_ingredients if ingr.name is not None)
        return self.filter_string.contained_in(ingredient_names)

    def __str__(self):
        return f'ingr:{self.filter_string!r}'


@dataclass(frozen=True)
class UnitFilterTerm(FilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        ingredient_units = (ingr.amount.unit for ingr in recipe.leaf_ingredients if ingr.amount is not None and ingr.amount.unit is not None)
        yield_units = (yield_.unit for yield_ in recipe.yields if yield_.unit is not None)
        return self.filter_string.contained_in(itertools.chain(ingredient_units, yield_units))

    def __str__(self):
        return f'unit:{self.filter_string!r}'


@dataclass(frozen=True)
class AnyFilterTerm(IngredientFilterTerm, TagFilterTerm, UnitFilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        return IngredientFilterTerm.evaluate(self, recipe) or TagFilterTerm.evaluate(self, recipe) \
               or UnitFilterTerm.evaluate(self, recipe)

    def __str__(self):
        return f'{self.filter_string!r}'


@dataclass(frozen=True)
class BooleanOperation(FilterElement, ABC):
    OPERATOR: ClassVar[str]
    ASSOCIATIVITY: ClassVar[Any]
    ARITY: ClassVar[int]
    operands: List[FilterElement]

    @classmethod
    def get_operator_expression(cls) -> Optional[ParserElement]:
        return CaselessKeyword(cls.OPERATOR)


@dataclass(frozen=True)
class BooleanUnaryOperation(BooleanOperation, ABC):
    ARITY = 1

    @classmethod
    def create_from_tokens(cls, toks: ParseResults):
        return cls(operands=[toks[0][1]])

    def __str__(self):
        return f'({self.OPERATOR} {self.operands[0]})'


@dataclass(frozen=True)
class BooleanBinaryOperation(BooleanOperation, ABC):
    @classmethod
    def create_from_tokens(cls, toks: ParseResults):
        return cls(operands=toks[0][0::2])

    def __str__(self):
        op = f' {self.OPERATOR} '
        return f'({op.join([repr(oper) for oper in self.operands])})'


@dataclass(frozen=True)
class BooleanNotOperation(BooleanUnaryOperation):
    OPERATOR = "not"

    def evaluate(self, recipe: Recipe) -> bool:
        return not self.operands[0].evaluate(recipe)


@dataclass(frozen=True)
class BooleanAndExpression(BooleanBinaryOperation):
    OPERATOR = "and"

    def evaluate(self, recipe: Recipe) -> bool:
        return all(oper.evaluate(recipe) for oper in self.operands)

    @classmethod
    def create_from_implicit_tokens(cls, toks: ParseResults):
        return cls(operands=toks[0])


@dataclass(frozen=True)
class BooleanOrExpression(BooleanBinaryOperation):
    OPERATOR = "or"

    def evaluate(self, recipe: Recipe) -> bool:
        return any(oper.evaluate(recipe) for oper in self.operands)


@dataclass(frozen=True)
class BooleanXorExpression(BooleanBinaryOperation):
    OPERATOR = "xor"

    def evaluate(self, recipe: Recipe) -> bool:
        return reduce(lambda left, right: left ^ right, [oper.evaluate(recipe) for oper in self.operands])


class FilterParser:
    filter_expression_parser: ParserElement

    def __init__(self):
        self.filter_expression_parser = self._create_parser()

    def parse_filter_string(self, filter_string) -> FilterElement:
        return self.filter_expression_parser.parseString(filter_string, parseAll=True)[0]

    def _create_parser(self) -> ParserElement:
        operator_list = [
            (None, 2, opAssoc.LEFT,  BooleanAndExpression.create_from_implicit_tokens),
            (CaselessKeyword('not'), 1, opAssoc.RIGHT, BooleanNotOperation.create_from_tokens),
            (CaselessKeyword('and'), 2, opAssoc.LEFT, BooleanAndExpression.create_from_tokens),
            (CaselessKeyword('xor'), 2, opAssoc.LEFT, BooleanXorExpression.create_from_tokens),
            (CaselessKeyword('or'), 2, opAssoc.LEFT, BooleanOrExpression.create_from_tokens),
        ]

        term_list = [
            (CaselessKeyword('tag:'), TagFilterTerm.create_from_tokens),
            (CaselessKeyword('ingr:'), IngredientFilterTerm.create_from_tokens),
            (CaselessKeyword('unit:'), UnitFilterTerm.create_from_tokens),
            (None, AnyFilterTerm.create_from_tokens),
        ]

        operator_expressions = [om[0] for om in operator_list if om[0] is not None]
        term_expressions = [tm[0] for tm in term_list if tm[0] is not None]

        reserved_expressions = operator_expressions + term_expressions

        single_quoted_string = QuotedString('"', escChar='\\')
        double_quoted_string = QuotedString("'", escChar='\\')
        unquoted_string = ~Or(reserved_expressions) + CharsNotIn(" \t\r\n()")
        base_filter_string = single_quoted_string | double_quoted_string | unquoted_string
        base_filter_string.setParseAction(lambda toks: toks[0])

        simple_filter_string = pyparsing.Optional("~").setResultsName("contains") + base_filter_string.setResultsName("string")
        simple_filter_string.setParseAction(SimpleFilterString.create_from_tokens)

        regex_filter_string = QuotedString('/', escChar='\\')
        regex_filter_string.setParseAction(RegexFilterString.create_from_tokens)

        filter_string = regex_filter_string | simple_filter_string
        filter_string.setParseAction(lambda toks: toks[0])

        filter_terms = []
        for prefix_expression, term_action in term_list:
            if prefix_expression is not None:
                filter_term = Combine(prefix_expression + filter_string.setResultsName("filter_string"))
            else:
                filter_term = filter_string.setResultsName("filter_string")
            filter_term.addParseAction(term_action)
            filter_terms.append(filter_term)
        filter_term = Or(filter_terms)

        filter_expr = infixNotation(filter_term, operator_list)

        return filter_expr

if __name__ == "__main__":
    filter_parser = FilterParser()

    filter_parser.filter_expression_parser.runTests('''
        a b
        a b c ingr:d
    ''')
