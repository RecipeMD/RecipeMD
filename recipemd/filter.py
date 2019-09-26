import itertools
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from functools import reduce, wraps
from pprint import pprint
from typing import List, Iterable, Pattern, Type, Callable, Optional, TypeVar

from pyparsing import infixNotation, QuotedString, CaselessKeyword, opAssoc, ParserElement, Combine, \
    ParseResults, MatchFirst, Regex, Literal

from recipemd.data import Recipe


def _value_error_to_not_implemented(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError:
            return NotImplemented

    return wrapper


@dataclass(frozen=True)
class ASTElement(ABC):
    @classmethod
    @abstractmethod
    def create_from_tokens(cls, toks):
        raise NotImplementedError

    def _to_filter_element(self, other) -> 'FilterElement':
        if isinstance(other, FilterElement):
            return other
        if isinstance(other, FilterString):
            return AnyFilterTerm(other)
        if isinstance(other, str):
            return AnyFilterTerm(FuzzyFilterString(other))
        if isinstance(other, Pattern):
            return AnyFilterTerm(RegexFilterString(other))
        raise ValueError()

    @_value_error_to_not_implemented
    def __or__(self, other):
        return BooleanOrOperation(operands=[self._to_filter_element(self), self._to_filter_element(other)])

    @_value_error_to_not_implemented
    def __and__(self, other):
        return BooleanAndOperation(operands=[self._to_filter_element(self), self._to_filter_element(other)])

    @_value_error_to_not_implemented
    def __xor__(self, other):
        return BooleanXorOperation(operands=[self._to_filter_element(self), self._to_filter_element(other)])

    @_value_error_to_not_implemented
    def __ror__(self, other):
        return BooleanOrOperation(operands=[self._to_filter_element(other), self._to_filter_element(self)])

    @_value_error_to_not_implemented
    def __rand__(self, other):
        return BooleanAndOperation(operands=[self._to_filter_element(other), self._to_filter_element(self)])

    @_value_error_to_not_implemented
    def __rxor__(self, other):
        return BooleanXorOperation(operands=[self._to_filter_element(other), self._to_filter_element(self)])

    @_value_error_to_not_implemented
    def __invert__(self):
        return BooleanNotOperation(operands=[self._to_filter_element(self)])


@dataclass(frozen=True)
class FilterString(ASTElement, ABC):
    @abstractmethod
    def contained_in(self, to_search: Iterable[str]):
        raise NotImplementedError


@dataclass(frozen=True)
class FuzzyFilterString(FilterString):
    string: str

    @classmethod
    def create_from_tokens(cls, toks: ParseResults):
        return cls(string=toks["string"])

    def contained_in(self, to_search: Iterable[str]):
        to_find_caseless = _normalize_str(self.string)
        return any(to_find_caseless in _normalize_str(el) for el in to_search)


@dataclass(frozen=True)
class ExactFilterString(FilterString):
    string: str

    @classmethod
    def create_from_tokens(cls, toks: ParseResults):
        return cls(string=toks["string"])

    def contained_in(self, to_search: Iterable[str]):
        to_find_caseless = _normalize_str(self.string)
        return any(to_find_caseless == _normalize_str(el) for el in to_search)


@dataclass(frozen=True)
class RegexFilterString(FilterString):
    regex: Pattern

    @classmethod
    def create_from_tokens(cls, toks: ParseResults):
        return cls(regex=re.compile(toks[0]))

    def contained_in(self, to_search: Iterable[str]):
        return any(self.regex.search(el) for el in to_search)


@dataclass(frozen=True)
class FilterElement(ASTElement, ABC):
    @abstractmethod
    def evaluate(self, recipe: Recipe) -> bool:
        raise NotImplementedError


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


@dataclass(frozen=True)
class IngredientFilterTerm(FilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        ingredient_names = (ingr.name for ingr in recipe.leaf_ingredients if ingr.name is not None)
        return self.filter_string.contained_in(ingredient_names)


@dataclass(frozen=True)
class UnitFilterTerm(FilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        ingredient_units = (ingr.amount.unit for ingr in recipe.leaf_ingredients if ingr.amount is not None and ingr.amount.unit is not None)
        yield_units = (yield_.unit for yield_ in recipe.yields if yield_.unit is not None)
        return self.filter_string.contained_in(itertools.chain(ingredient_units, yield_units))


@dataclass(frozen=True)
class AnyFilterTerm(IngredientFilterTerm, TagFilterTerm, UnitFilterTerm):
    def evaluate(self, recipe: Recipe) -> bool:
        return IngredientFilterTerm.evaluate(self, recipe) or TagFilterTerm.evaluate(self, recipe) \
               or UnitFilterTerm.evaluate(self, recipe)


@dataclass(frozen=True)
class BooleanOperation(FilterElement, ABC):
    operands: List[FilterElement]


@dataclass(frozen=True)
class BooleanUnaryOperation(BooleanOperation, ABC):
    @classmethod
    def create_from_tokens(cls, toks: ParseResults):
        return cls(operands=[toks[0][1]])


@dataclass(frozen=True)
class BooleanBinaryOperation(BooleanOperation, ABC):
    @classmethod
    def create_from_tokens(cls, toks: ParseResults):
        return cls(operands=toks[0][0::2])


@dataclass(frozen=True)
class BooleanNotOperation(BooleanUnaryOperation):
    def evaluate(self, recipe: Recipe) -> bool:
        return not self.operands[0].evaluate(recipe)

    def __invert__(self):
        return self.operands[0]


@dataclass(frozen=True)
class BooleanAndOperation(BooleanBinaryOperation):
    def evaluate(self, recipe: Recipe) -> bool:
        return all(oper.evaluate(recipe) for oper in self.operands)

    @classmethod
    def create_from_implicit_tokens(cls, toks: ParseResults):
        return cls(operands=list(toks[0]))

    @_value_error_to_not_implemented
    def __and__(self, other):
        return BooleanAndOperation(operands=[*self.operands, self._to_filter_element(other)])

    @_value_error_to_not_implemented
    def __rand__(self, other):
        return BooleanAndOperation(operands=[self._to_filter_element(other), *self.operands])


@dataclass(frozen=True)
class BooleanOrOperation(BooleanBinaryOperation):
    def evaluate(self, recipe: Recipe) -> bool:
        return any(oper.evaluate(recipe) for oper in self.operands)

    @_value_error_to_not_implemented
    def __or__(self, other):
        return BooleanOrOperation(operands=[*self.operands, self._to_filter_element(other)])

    @_value_error_to_not_implemented
    def __ror__(self, other):
        return BooleanOrOperation(operands=[self._to_filter_element(other), *self.operands])


@dataclass(frozen=True)
class BooleanXorOperation(BooleanBinaryOperation):
    OPERATOR = "xor"

    def evaluate(self, recipe: Recipe) -> bool:
        return reduce(lambda left, right: left ^ right, [oper.evaluate(recipe) for oper in self.operands])

    @_value_error_to_not_implemented
    def __xor__(self, other):
        return BooleanXorOperation(operands=[*self.operands, self._to_filter_element(other)])

    @_value_error_to_not_implemented
    def __rxor__(self, other):
        return BooleanXorOperation(operands=[self._to_filter_element(other), *self.operands])


def _normalize_str(text: str):
    return unicodedata.normalize("NFKD", text.strip().casefold())


class FilterParser:
    filter_expression_parser: ParserElement

    def __init__(self):
        self.filter_expression_parser = self._create_parser()

    def parse_filter_string(self, filter_string) -> FilterElement:
        """
        Parses a filter string into an evaluateable ast.

        :param filter_string: A string representing a recipe filter
        :return: filter_element: A filter ast, subclass of FilterElement
        :raises ParseBaseException: If string is not a valid filter
        :raises re.error: If a regular expression used in a filter term is not syntactically correct
        """
        return self.filter_expression_parser.parseString(filter_string, parseAll=True)[0]

    @staticmethod
    def _create_parser() -> ParserElement:
        # operators in the format later used by infixNotation
        operator_list = [
            (None, 2, opAssoc.LEFT, BooleanAndOperation.create_from_implicit_tokens),
            (CaselessKeyword('not') | "~" | "!", 1, opAssoc.RIGHT, BooleanNotOperation.create_from_tokens),
            (CaselessKeyword('and') | "&", 2, opAssoc.LEFT, BooleanAndOperation.create_from_tokens),
            (CaselessKeyword('xor') | "^", 2, opAssoc.LEFT, BooleanXorOperation.create_from_tokens),
            (CaselessKeyword('or') | "|", 2, opAssoc.LEFT, BooleanOrOperation.create_from_tokens),
        ]

        # terms (atoms) that will be combined with the boolean operators
        term_list = [
            (CaselessKeyword('tag'), TagFilterTerm.create_from_tokens),
            (CaselessKeyword('ingr'), IngredientFilterTerm.create_from_tokens),
            (CaselessKeyword('unit'), UnitFilterTerm.create_from_tokens),
            (None, AnyFilterTerm.create_from_tokens),
        ]

        # extract keywords that can
        operator_expressions = [om[0] for om in operator_list if om[0] is not None]
        term_expressions = [tm[0] for tm in term_list if tm[0] is not None]
        reserved_expressions = operator_expressions + term_expressions

        # quoted string indicates exact macthc
        quoted_filter_string = (QuotedString('"', escChar='\\') | QuotedString("'", escChar='\\')).setResultsName('string')
        # quoted_filter_string.setDebug(True)
        quoted_filter_string.setName("quoted_filter_string")
        quoted_filter_string.setParseAction(ExactFilterString.create_from_tokens)

        # not quoted string is inexact match, can't contain whitespace or be an operator
        unquoted_filter_string = ~MatchFirst(reserved_expressions) + Regex(r'[^\s\(\)]+', flags=re.U).setResultsName('string')
        # unquoted_filter_string.setDebug(True)
        unquoted_filter_string.setName("unquoted_filter_string")
        unquoted_filter_string.setParseAction(FuzzyFilterString.create_from_tokens)

        # regular expressions aren't parsed in the grammar but delegated to python re.compile in the parser action
        regex_filter_string = QuotedString('/', escChar='\\')
        regex_filter_string.setName("regex_filter_string")
        regex_filter_string.setParseAction(RegexFilterString.create_from_tokens)

        # unquoted_filter_string must be last, so that initial quotes are handled correctly
        filter_string = regex_filter_string | quoted_filter_string | unquoted_filter_string
        filter_string.setParseAction(lambda toks: toks[0])

        filter_terms = []
        for prefix_expression, term_action in term_list:
            if prefix_expression is not None:
                filter_term = Combine(prefix_expression + ':' + filter_string.setResultsName("filter_string"))
                filter_term.setName("filter_term_"+str(prefix_expression.match))
            else:
                filter_term = filter_string.setResultsName("filter_string")
                filter_term.setName("filter_term_None")
            # filter_term.setDebug(True)
            filter_term.addParseAction(term_action)
            filter_terms.append(filter_term)
        filter_term = MatchFirst(filter_terms)
        filter_expr = infixNotation(filter_term, operator_list)

        return filter_expr


# DSL
@dataclass(frozen=True)
class _FilterTermBuilder:
    term: Optional[Type[FilterTerm]] = None

    @property
    def fuz(self) -> '_FilterStringBuilder':
        return _FilterStringBuilder(term=self.term, filter_string=FuzzyFilterString)

    @property
    def re(self) -> '_FilterStringBuilder':
        return _FilterStringBuilder(term=self.term, filter_string=lambda s: RegexFilterString(re.compile(s)))

    @property
    def ex(self) -> '_FilterStringBuilder':
        return _FilterStringBuilder(term=self.term, filter_string=ExactFilterString)

    def __call__(self, string):
        term = self.term or AnyFilterTerm
        return term(FuzzyFilterString(string))



@dataclass(frozen=True)
class _FilterStringBuilder:
    term: Optional[Type[FilterTerm]]
    filter_string: Optional[Callable[[str], FilterString]] = None

    def __call__(self, string):
        term = self.term or AnyFilterTerm
        filter_string = self.filter_string or FuzzyFilterString
        return term(filter_string(string))


@dataclass(frozen=True)
class _FilterBuilder(_FilterTermBuilder):
    @property
    def any(self) -> _FilterTermBuilder:
        return _FilterTermBuilder(term=AnyFilterTerm)

    @property
    def tag(self) -> _FilterTermBuilder:
        return _FilterTermBuilder(term=TagFilterTerm)

    @property
    def ingr(self) -> _FilterTermBuilder:
        return _FilterTermBuilder(term=IngredientFilterTerm)

    @property
    def unit(self) -> _FilterTermBuilder:
        return _FilterTermBuilder(term=UnitFilterTerm)

    def __call__(self, string) -> AnyFilterTerm:
        return AnyFilterTerm(FuzzyFilterString(string))


f = _FilterBuilder()