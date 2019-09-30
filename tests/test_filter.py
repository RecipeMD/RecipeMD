import inspect
import re
from decimal import Decimal

import pytest
from pyparsing import ParseException

from recipemd.data import Recipe, Ingredient, Amount, IngredientGroup
from recipemd.filter import FilterParser, f, BooleanOrOperation, AnyFilterTerm, FuzzyFilterString, BooleanAndOperation, \
    RegexFilterString, BooleanXorOperation, BooleanNotOperation


@pytest.fixture(scope="session")
def filter_parser() -> FilterParser:
    return FilterParser()


@pytest.mark.parametrize("filter_string, expected_ast", [
    ("a b",  f("a") & f("b")),
    ("'a' 'b'", f.ex("a") & f.ex("b")),
    ("/a+/ 'b'", f.re("a+") & f.ex("b")),
    ("tag:a", f.tag("a")),
    ("unit:b xor ingr:/c/", f.unit("b") ^ f.ingr.re("c")),
    ("not 5", ~f("5")),
    ("a tag:b", f("a") & f.tag("b")),
    ("a and b", f("a") & f("b")),
    ("a and ~b?", f("a") & ~f("b?")),
    ("a & ~b?", f("a") & ~f("b?")),
    ("ingr:/^a+$/ ^ $b", f.ingr.re("^a+$") ^ f("$b")),
    ("a and b or c", (f("a") & f("b")) | f("c")),
    ("(a and b) or c", (f("a") & f("b")) | f("c")),
    ("a and (b or c)", f("a") & (f("b") | f("c"))),
    ("!/[a-c]+/", ~f.re("[a-c]+")),

    # unquoted filter term may not start with location specifier
    ("tag:", ParseException),
    # containing a location specifier is okay
    ("btag:", f("btag:")),
    # * is not a valid regex
    ("/*/", re.error),
])
def test_parse_filter_string(filter_parser, filter_string, expected_ast):
    if inspect.isclass(expected_ast) and issubclass(expected_ast, BaseException):
        with pytest.raises(expected_ast):
            filter_parser.parse_filter_string(filter_string)
    else:
        assert filter_parser.parse_filter_string(filter_string) == expected_ast


@pytest.mark.parametrize("builder_ast, expected_ast", [
    (
        "a" & f.any("b"),
        BooleanAndOperation(operands=[AnyFilterTerm(FuzzyFilterString("a")), AnyFilterTerm(FuzzyFilterString("b"))])
    ),
    (
        re.compile("a") | f("b"),
        BooleanOrOperation(operands=[AnyFilterTerm(RegexFilterString(re.compile("a"))), AnyFilterTerm(FuzzyFilterString("b"))])
    ),
    (
        ~f("a"),
        BooleanNotOperation(operands=[AnyFilterTerm(FuzzyFilterString("a"))])
    ),
    (
        ~(~f("a")),
        AnyFilterTerm(FuzzyFilterString("a"))
    ),
    (
        "a" & (f("b") & "c") & "d",
        BooleanAndOperation(operands=[
            AnyFilterTerm(FuzzyFilterString("a")), AnyFilterTerm(FuzzyFilterString("b")),
            AnyFilterTerm(FuzzyFilterString("c")), AnyFilterTerm(FuzzyFilterString("d"))
        ])

    ),
    (
        "a" | (f("b") | "c") | "d",
        BooleanOrOperation(operands=[
            AnyFilterTerm(FuzzyFilterString("a")), AnyFilterTerm(FuzzyFilterString("b")),
            AnyFilterTerm(FuzzyFilterString("c")), AnyFilterTerm(FuzzyFilterString("d"))
        ])

    ),
    (
        "a" ^ ("b" ^ f.fuz("c")) ^ FuzzyFilterString("d"),
        BooleanXorOperation(operands=[
            AnyFilterTerm(FuzzyFilterString("a")), AnyFilterTerm(FuzzyFilterString("b")),
            AnyFilterTerm(FuzzyFilterString("c")), AnyFilterTerm(FuzzyFilterString("d"))
        ])
    ),

])
def test_filter_builder(builder_ast, expected_ast):
    assert builder_ast == expected_ast


def test_filter_builder_invalid_operands():
    with pytest.raises(TypeError):
        f("a") | 5


@pytest.fixture(scope="session")
def recipe() -> Recipe:
    return Recipe(
        title="Test",
        tags=["vegetarian", "flavorful", "tag with spaces"],
        yields=[Amount(factor=Decimal("1"), unit="serving"), Amount(factor=Decimal(0.4), unit="kg")],
        ingredients=[
            Ingredient(amount=Amount(factor=Decimal('5')), name='Eggs'),
            Ingredient(amount=Amount(factor=Decimal('200'), unit='g'), name='Butter'),
            IngredientGroup(title='Group', children=[
                Ingredient(amount=Amount(factor=Decimal('2'), unit='cloves'), name='Garlic'),
                IngredientGroup(title='Subgroup', children=[
                    Ingredient(name='Onions'),
                ]),
            ]),
            Ingredient(name='Salt')
        ],
    )


@pytest.mark.parametrize("filter_ast, result", [
    (f.tag("vegetarian"), True),
    (f.tag("veg"), True),
    (f.tag.ex("vegetarian"), True),
    (f.tag.ex("veg"), False),
    (f.tag.re("flavou?rful"), True),
    (f.tag.re("veg"), True),
    (f.tag.re("^veg$"), False),
    (f.unit.ex("g"), True),
    (f.unit.ex("l"), False),
    (f.ingr("Eggs"), True),
    (f.ingr("Ham"), False),
    (f.ingr.ex("Subgroup"), False),
    (f.ex("tag with spaces"), True),

    (~f("Ham"), True),
    (f("Eggs") | f("Ham"), True),
    (f("Cheese") | f("Ham"), False),
    (f("Eggs") & f("Salt"), True),
    (f("Eggs") & f("Ham"), False),
    (f("Eggs") ^ f("Ham"), True),
    (f("Eggs") ^ f("Salt"), False),
    (f("Cheese") ^ f("Ham"), False),
])
def test_evaluate(recipe, filter_ast, result):
    assert filter_ast.evaluate(recipe) == result
