# RecipeMD Specification

This is version 2.3.2 of the RecipeMD specification.

RecipeMD is a Markdown-based format for writing down recipes. It 
defines a certain structure which a document must follow to be a 
RecipeMD recipe.

All RecipeMD files shall follow the [commonmark] specification.

[commonmark]: https://commonmark.org



## Example

This example presents the basic format of a RecipeMD recipe

```markdown
# Guacamole

Some people call it guac.

*sauce, vegan*

**4 Servings, 200g**

---

- *1* avocado
- *.5 teaspoon* salt
- *1 1/2 pinches* red pepper flakes
- lemon juice

---

Remove flesh from avocado and roughly mash with fork. Season to taste 
with salt, pepper and lemon juice.
```

- the title is noted as a first level header: `# Guacamole`
- the short description is noted as one or more paragraphs: `Some 
  people call it guac.`
- the tags are noted as paragraph containing only a comma seperated 
  list in italics: `*sauce, vegan*`
- the yield is noted as paragraph containing only a comma seperated 
  list in bold face: `**4 Servings, 200g**`
- the ingredients are noted as list items. The headings form the
  titles of ingredient groups. The amount of each ingredient (if 
  given) is noted in italics. Amounts may be expressed as decimals
  (dividers "." and ",") and fractions:
  
    ```markdown
    - *1* avocado
    - *.5 teaspoon* salt
    - *1 1/2 pinches* red pepper flakes
    - lemon juice
    ```
- anything following the second horizontal line is considered 
  instructions



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
3. Yield and Tags (arbitrary order):
    - Tags as a paragraph which is completely in italics. Tags are a
      comma separated list of strings.
    - Yields as a paragraph which is completely in bold. Yields are a
      comma separated list of amounts. Note the rules about commas in
      amounts.
5. a horizontal line
6. the ingredients, consisting of
    1. *optional*: headings to group ingredients
    2. lists, where each list item is an ingredient
7. a horizontal line -- this may be omitted if there are no 
   instructions
8. *optional*: the instructions, everything following the second line

### Amount

An amount consists of

- a value as a number
- *optional* a unit

An amount is represented as follows:

1. A number, which may have one of the following formats
    - improper fraction (e.g. `1 1/5`)
    - proper fraction (e.g `3/7`)
    - [unicode vulgar fractions] (like ½) may also be used
    - decimal with dividers "." and "," (e.g. "41.9")
2. A unit which is just everything following the number

[unicode vulgar fractions]: http://unicode.org/cldr/utility/list-unicodeset.jsp?a=[:Decomposition_Type=Fraction:]

Note that when an amount is inside of a comma separated list, a comma
is treated as a decimal divider if the characters directly before and
after are numerical and as a list divider otherwise.

### Ingredient

An ingredient consists of

- *optional* an amount
- a name
- *optional* a link to a recipe for the ingredient

An ingredient is represented as follows:

1. The amount in italics
2. Everything following until the end of the list item is part of the
   name or the link as specified below:
   1. If a name contains only an [inline-link], the [link-text]
      represents the name of the ingredient and the [link-destination]
      specifies a resource that contains a recipe for the ingredient
   2. Otherwise, the text is the name and the link is not set

[inline-link]: https://spec.commonmark.org/0.28/#inline-link
[link-text]: https://spec.commonmark.org/0.28/#link-text
[link-destination]: https://spec.commonmark.org/0.28/#link-destination

### Ingredient Group

An ingredient group is a group of related ingredients, e.g. the
ingredients making up one component of a dish. It consists of:

- *optional* a title
- 1..n ingredients

An ingredient group us represented as follows:

1. A [heading], whose contents are the group's title
2. A list of ingredients

[heading]: https://spec.commonmark.org/0.28/#atx-headings



## Test Cases

Implementations of this specification must conform with all 
[test cases]. There are two kinds of testcases: valid files (`*.md` 
with a corresponding `*.json`) and invalid files (`*.invalid.md`)

[test cases]: https://github.com/tstehr/RecipeMD/tree/master/testcases



## Authors Licensing

This specification was written and is maintained by Jonas Grosse-Holz 
and Tilman Stehr. The project's website is [recipemd.org].

The specification is licensed under the terms of the GNU Lesser 
General Public License as published by the Free Software Foundation, 
either version 3 of the License, or any later version.

[recipemd.org]: https://recipemd.org


## Version History

### Version 2.3.2 (2019-12-18)

- Add author and license information

### Version 2.3.1 (2019-11-18)

- Fix missing link
- Fix wrong indentation and word wrapping

### Version 2.3.0 (2019-11-18)

- Add a full version of the example
- Add version history reconstructed from git
- Add reference to test suite

### Version 2.2.0 (2019-04-22)

- Allow recipes to reference other recipes

### 2.1.0 (2019-03-25)

- Allow unicode vulgar fractions in ingredient amounts

### 2.0.1 (2018-09-17)

- Reword specification
- Clarify edge cases

### 2.0.0 (2018-09-13)

- *Breaking:* Seperate yields and tags into own paragraphs

### 1.0.0 (2018-08-26)

- Initial version

