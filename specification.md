# RecipeMD: Markdown Recipe Specification

This is version 2.0.1 of the RecipeMD specification.

RecipeMD is a Markdown-based format for writing down recipes. It
defines a certain structure which a document must follow to be a
RecipeMD recipe.

All RecipeMD files shall follow the [commonmark] specification.

[commonmark]: https://commonmark.org

## Example

This example presents the basic format of a recipemd recipe

- the title is noted as a first level header:
  ```# Guacamole```
- the short description is noted as one or more paragraphs.
  ```Some people call it guac.```
- the tags are noted as paragraph containing only a comma seperated
  list in italics:
   ```*sauce, vegan*```
- the yield is noted as paragraph containing only a comma seperated
  list in bold face:
  ```**4 Servings, 200g**```
- the ingredients are noted as list items. The headings form the
  titles of ingredient groups. The amount of each ingredient (if given)
  is noted in italic case. Amounts may be expressed as decimals
  (dividers "." and ",") and fractions:
    ```
    - *1* avocado
    - *.5 teaspoon* salt
    - *1 1/2 pinches* red pepper flakes
    - lemon juice
    ```
- anything following the second horizontal line is considered instructions

## RecipeMD Data types

### Recipe

A *valid* recipe consists of:

- a title
- *optional*: a short description
- *optional*: 1..n tags
- *optional*: 1..n yields
- the ingredients as 1..n ingredient groups
- *optional*: instructions

A recipe is represented in markdown as follows:

1. Title as a first level heading
2. Short description as zero or more paragraphs
3. Yield and Tags (Ordering :
    - Tags as a paragraph which is completely in italics. Tags are a
      comma separated list of strings.
    - Yields as a paragraph which is completely in bold. Yields are a
      comma separated list of amounts. Note the rules about commas in
      amounts.
5. a horizontal line
6. the ingredients, consisting of
    1. *optional*: headings to group ingredients
    2. lists, where each list item is an ingredient
7. a horizontal line -- this may be omitted if there are no instructions
8. *optional*: the instructions, everything following the second line

### Amount

An amount consists of

- a value as a number
- *optional* a unit

An amount is represented as follows:

1. A number, which may have one of the following formats
    - improper fraction (e.g. `1 1/5`)
    - proper fraction (e.g `3/7`)
    - decimal with dividers "." and "," (e.g. "41.9")
2. A unit which is just everything following the number

Note that when an amount is inside of a comma separated list, a comma
is treated as a decimal divider if the characters directly before and
after are numerical and as a list divider otherwise.

### Ingredient

An ingredient consists of

- *optional* an amount
- a name

An ingredient is represented as follows:

1. The amount in italics
2. Everything following until the end of the list item is part of the name.

#### Name

If a name contains a [inline-link](https://spec.commonmark.org/0.28/#inline-link), the [link-text](https://spec.commonmark.org/0.28/#link-text) becomes the name of the ingredient.
If the linked recipe specifies a yield and the ingredient does not specify an amount, the yield of the linked recipe becomes the amount of the ingredient.
The tags of the linked recipe are added to the tags of the recipe.

### Ingredient Group

An ingredient group is a group of related ingredients, e.g. the
ingredients making up one component of a dish. It consists of:

- *optional* a title
- 1..2 ingredients





