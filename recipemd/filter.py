"""
Defines boolean predicates that can be evaluated against a recipe.

Filters allow easy searching within the structure of a :class:`recipemd.data.Recipe`. They can be created from strings
with the :class:`FilterParser` or in code with the :class:`FilterBuilder` which can be imported as :data:`f` from this
module.

"""
import itertools
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import reduce, wraps
from typing import List, Iterable, Pattern, Type, Callable, Optional

from pyparsing import infixNotation, QuotedString, CaselessKeyword, opAssoc, ParserElement, Combine, \
    ParseResults, MatchFirst, Regex

from recipemd.data import Recipe

__all__ = [
    "FilterParser", "f", "FilterBuilder",
    "BooleanAndOperation", "BooleanOrOperation", "BooleanNotOperation", "BooleanXorOperation",
    "AnyFilterTerm", "TagFilterTerm", "IngredientFilterTerm", "UnitFilterTerm",
    "FuzzyFilterString", "ExactFilterString", "RegexFilterString",
]


def _value_error_to_not_implemented(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError:
            return NotImplemented

    return wrapper


@dataclass(frozen=True)
class _ASTElement(ABC):
    @classmethod
    @abstractmethod
    def _create_from_tokens(cls, toks):
        raise NotImplementedError

    def _to_filter_element(self, other) -> '_FilterElement':
        if isinstance(other, _FilterElement):
            return other
        if isinstance(other, _FilterString):
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
class _FilterString(_ASTElement, ABC):
    @abstractmethod
    def contained_in(self, to_search: Iterable[str]) -> bool:
        """Checks if any of the elements in `to_search` match the filter string."""
        raise NotImplementedError


@dataclass(frozen=True)
class FuzzyFilterString(_FilterString):
    string: str

    @classmethod
    def _create_from_tokens(cls, toks: ParseResults):
        return cls(string=toks["string"])

    def contained_in(self, to_search: Iterable[str]) -> bool:
        to_find_caseless = _normalize_str(self.string)
        return any(to_find_caseless in _normalize_str(el) for el in to_search)


@dataclass(frozen=True)
class ExactFilterString(_FilterString):
    string: str

    @classmethod
    def _create_from_tokens(cls, toks: ParseResults):
        return cls(string=toks["string"])

    def contained_in(self, to_search: Iterable[str]) -> bool:
        to_find_caseless = _normalize_str(self.string)
        return any(to_find_caseless == _normalize_str(el) for el in to_search)


@dataclass(frozen=True)
class RegexFilterString(_FilterString):
    regex: Pattern

    @classmethod
    def _create_from_tokens(cls, toks: ParseResults):
        return cls(regex=re.compile(toks[0]))

    def contained_in(self, to_search: Iterable[str]) -> bool:
        return any(self.regex.search(el) for el in to_search)


@dataclass(frozen=True)
class _FilterElement(_ASTElement, ABC):
    @abstractmethod
    def evaluate(self, recipe: Recipe) -> bool:
        """Evaluate filter against given recipe"""
        raise NotImplementedError


@dataclass(frozen=True)
class FilterTerm(_FilterElement, ABC):
    filter_string: _FilterString

    @classmethod
    def _create_from_tokens(cls, toks: ParseResults):
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
class _BooleanOperation(_FilterElement, ABC):
    operands: List[_FilterElement]


@dataclass(frozen=True)
class _BooleanUnaryOperation(_BooleanOperation, ABC):
    @classmethod
    def _create_from_tokens(cls, toks: ParseResults):
        return cls(operands=[toks[0][1]])


@dataclass(frozen=True)
class _BooleanBinaryOperation(_BooleanOperation, ABC):
    @classmethod
    def _create_from_tokens(cls, toks: ParseResults):
        return cls(operands=toks[0][0::2])


@dataclass(frozen=True)
class BooleanNotOperation(_BooleanUnaryOperation):
    def evaluate(self, recipe: Recipe) -> bool:
        return not self.operands[0].evaluate(recipe)

    def __invert__(self):
        return self.operands[0]


@dataclass(frozen=True)
class BooleanAndOperation(_BooleanBinaryOperation):
    def evaluate(self, recipe: Recipe) -> bool:
        return all(oper.evaluate(recipe) for oper in self.operands)

    @classmethod
    def _create_from_implicit_tokens(cls, toks: ParseResults):
        return cls(operands=list(toks[0]))

    @_value_error_to_not_implemented
    def __and__(self, other):
        return BooleanAndOperation(operands=[*self.operands, self._to_filter_element(other)])

    @_value_error_to_not_implemented
    def __rand__(self, other):
        return BooleanAndOperation(operands=[self._to_filter_element(other), *self.operands])


@dataclass(frozen=True)
class BooleanOrOperation(_BooleanBinaryOperation):
    def evaluate(self, recipe: Recipe) -> bool:
        return any(oper.evaluate(recipe) for oper in self.operands)

    @_value_error_to_not_implemented
    def __or__(self, other):
        return BooleanOrOperation(operands=[*self.operands, self._to_filter_element(other)])

    @_value_error_to_not_implemented
    def __ror__(self, other):
        return BooleanOrOperation(operands=[self._to_filter_element(other), *self.operands])


@dataclass(frozen=True)
class BooleanXorOperation(_BooleanBinaryOperation):
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
    """Normalizes a string for evaluation of filter strings"""
    return unicodedata.normalize("NFKD", text.strip().casefold())


class FilterParser:
    """Allows parsing filter strings into ASTs"""
    filter_expression_parser: ParserElement

    def __init__(self):
        self.filter_expression_parser = self._create_parser()

    def parse_filter_string(self, filter_string: str) -> _FilterElement:
        """
        Parses a filter string into an evaluateable AST.

        >>> fp = FilterParser()
        >>> fp.parse_filter_string('vegan and summer')
        BooleanAndOperation(operands=[AnyFilterTerm(filter_string=FuzzyFilterString(string='vegan')), AnyFilterTerm(filter_string=FuzzyFilterString(string='summer'))])

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
            (None, 2, opAssoc.LEFT, BooleanAndOperation._create_from_implicit_tokens),
            (CaselessKeyword('not') | "~" | "!", 1, opAssoc.RIGHT, BooleanNotOperation._create_from_tokens),
            (CaselessKeyword('and') | "&", 2, opAssoc.LEFT, BooleanAndOperation._create_from_tokens),
            (CaselessKeyword('xor') | "^", 2, opAssoc.LEFT, BooleanXorOperation._create_from_tokens),
            (CaselessKeyword('or') | "|", 2, opAssoc.LEFT, BooleanOrOperation._create_from_tokens),
        ]

        # terms (atoms) that will be combined with the boolean operators
        term_list = [
            (CaselessKeyword('tag'), TagFilterTerm._create_from_tokens),
            (CaselessKeyword('ingr'), IngredientFilterTerm._create_from_tokens),
            (CaselessKeyword('unit'), UnitFilterTerm._create_from_tokens),
            (None, AnyFilterTerm._create_from_tokens),
        ]

        # extract keywords that can
        operator_expressions = [om[0] for om in operator_list if om[0] is not None]
        term_expressions = [tm[0] for tm in term_list if tm[0] is not None]
        reserved_expressions = operator_expressions + term_expressions

        # quoted string indicates exact macthc
        quoted_filter_string = (QuotedString('"', escChar='\\') | QuotedString("'", escChar='\\')).setResultsName('string')
        # quoted_filter_string.setDebug(True)
        quoted_filter_string.setName("quoted_filter_string")
        quoted_filter_string.setParseAction(ExactFilterString._create_from_tokens)

        # not quoted string is inexact match, can't contain whitespace or be an operator
        unquoted_filter_string = ~MatchFirst(reserved_expressions) + Regex(r'[^\s\(\)]+', flags=re.U).setResultsName('string')
        # unquoted_filter_string.setDebug(True)
        unquoted_filter_string.setName("unquoted_filter_string")
        unquoted_filter_string.setParseAction(FuzzyFilterString._create_from_tokens)

        # regular expressions aren't parsed in the grammar but delegated to python re.compile in the parser action
        regex_filter_string = QuotedString('/', escChar='\\')
        regex_filter_string.setName("regex_filter_string")
        regex_filter_string.setParseAction(RegexFilterString._create_from_tokens)

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
        """Create a filter where the given string is matched fuzzily"""
        return _FilterStringBuilder(term=self.term, filter_string=FuzzyFilterString)

    @property
    def re(self) -> '_FilterStringBuilder':
        """Create a filter where the given string is interpreted as a regular expression"""
        return _FilterStringBuilder(term=self.term, filter_string=lambda s: RegexFilterString(re.compile(s)))

    @property
    def ex(self) -> '_FilterStringBuilder':
        """Create a filter where the given string must match exactly"""
        return _FilterStringBuilder(term=self.term, filter_string=ExactFilterString)

    def __call__(self, string):
        """Create a filter where the given string is matched fuzzily"""
        term = self.term or AnyFilterTerm
        return term(FuzzyFilterString(string))


@dataclass(frozen=True)
class _FilterStringBuilder:
    term: Optional[Type[FilterTerm]]
    filter_string: Optional[Callable[[str], _FilterString]] = None

    def __call__(self, string):
        """Create a filter that matches any supported fields and the given string is matched fuzzily"""
        term = self.term or AnyFilterTerm
        filter_string = self.filter_string or FuzzyFilterString
        return term(filter_string(string))


@dataclass(frozen=True)
class FilterBuilder(_FilterTermBuilder):
    """
    Creates filter expressions in code

    Allows using a language similar to the expressions parsed by `recipemd.filter.FilterParser` directly in python code.
    This makes filters usable as an embedded domain specific language.

    A preconfigured Filter builder is available as `f` in this module:

    >>> f('Cheese')
    AnyFilterTerm(filter_string=FuzzyFilterString(string='Cheese'))

    >>> f.ingr('Cheese')
    IngredientFilterTerm(filter_string=FuzzyFilterString(string='Cheese'))

    >>> f.re('Cheese|Bacon')
    AnyFilterTerm(filter_string=RegexFilterString(regex=re.compile('Cheese|Bacon')))

    >>> f.tag.ex('vegan')
    TagFilterTerm(filter_string=ExactFilterString(string='vegan'))


    Filters can be combined with logical operators "&" (and), "|" (or), "^" (xor), and "~" (not):

    >>> f('Cheese') | f('Bacon')
    BooleanOrOperation(operands=[AnyFilterTerm(filter_string=FuzzyFilterString(string='Cheese')), AnyFilterTerm(filter_string=FuzzyFilterString(string='Bacon'))])
    """
    @property
    def any(self) -> _FilterTermBuilder:
        """Create a filter that matches any supported fields"""
        return _FilterTermBuilder(term=AnyFilterTerm)

    @property
    def tag(self) -> _FilterTermBuilder:
        """Create a filter that matches tags"""
        return _FilterTermBuilder(term=TagFilterTerm)

    @property
    def ingr(self) -> _FilterTermBuilder:
        """Create a filter that matches ingredient names"""
        return _FilterTermBuilder(term=IngredientFilterTerm)

    @property
    def unit(self) -> _FilterTermBuilder:
        """Create a filter that matches units in ingredients or in yields"""
        return _FilterTermBuilder(term=UnitFilterTerm)

    def __call__(self, string) -> AnyFilterTerm:
        return AnyFilterTerm(FuzzyFilterString(string))


#: A preconfigured :class:`FilterBuilder` for convenient use
f = FilterBuilder()

# hack to make sphinx_autodoc_typehints happy
object.__setattr__(f, '__qualname__', 'f')
