# RecipeMD Specification

This is version 2.3.6 of the RecipeMD specification.

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



## RecipeMD Data Types

### Recipe

A *valid* recipe consists of:

- a title
- *optional*: a short description
- 0..n tags
- 0..n yields
- ingredients:
  - ungrouped ingredients as 0..n ingredients
  - grouped ingredients as 0..n ingredient groups
- *optional*: instructions

A recipe is represented in markdown as follows:

1. Title as a first level heading
2. Short description as zero or more paragraphs
3. Yield and Tags (arbitrary order, both optional):
    - Tags as a single paragraph which is completely in italics. Tags 
      are a comma separated list of strings.
    - Yields as a single paragraph which is completely in bold. Yields 
      are a comma separated list of amounts. Note the rules about 
      commas in amounts.
5. a horizontal line
6. the ingredients
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

- a title
- 0..n ingredients
- 0..n ingredients groups

An ingredient group us represented as follows:

1. A [heading], whose contents are the group's title
2. A list of ingredients (can be skipped)
3. A group may have child groups: Groups directly following a group
   are considered children of that group if their initial heading has
   a lower level than the original group. Heading levels are
   determined by their corresponding HTML heading, with `<h1>` being
   the highest heading level and `<h6>` the lowest.

[heading]: https://spec.commonmark.org/0.28/#atx-heading

## RecipeMD Parsing Strategy

This section presents a parsing strategy for RecipeMD documents. This
is based on the parsing algorithm used by the reference
implementation. 

The main algorithm is presented first. 

### Definitions

The following conventions are common to all algorithms.

- Variables are represented as `code`
- Advance a block `b`: Set `b` to the block after `b`. If `b` is the
  last block, it will be unset afterwards. 
- Enter a block `b`: Set `b` to the first child of `b`. This is only
  defined for [container blocks], and will error otherwise.
- Leave a block `b`: Set `b` to the parent of `b`. If `b` has no
  parent, it will be unset afterwards.

[container blocks]: https://spec.commonmark.org/0.31.2/#container-blocks

### Parsing a Recipe

The RecipeMD syntax is described in terms of the [commonmark]
specification. To parse a recipe, follow this algorithm. The algorithm
accepts a commonmark document.

1. Let `c` be the first block of the document.
2. Parse title:
    - **If** `c` it is a *heading* and has a level of 1:
      - Assign `c`'s contents to the recipe's title.
      - Advance `c`.
    - **Else** abort parsing with an error.
3. Let `descriptionStart` be the index of the starting line of `c`,
   let `descriptionEnd` be unset
4. Parse the description:
    - **If** `c` is a *paragraph* whose contents are a single
      *emphasis* or *strong emphasis*, go to 5.
    - **Else if** `c` is a thematic break, go to 5.
    - **Else** set `descriptionEnd` to the ending line of `c`, advance
      `c`.
5. Set the description:
    - **If** `descriptionEnd` is unset, keep the description unset.
    - **Else** set the recipe's description to the the inclusive range
      of lines between `descriptionStart` and `descriptionEnd` 
6. Parse tags and yields:
    - **If** `c` is a *paragraph* whose contents are a single
      *emphasis*:
      - **If** the recipe's tags are set, abort parsing with an error
      - **Else** set the recipe's tags to the contents of the
        paragraph, split at the comma character (with commas between
        ASCII digits ignored) and each element stripped from
        whitespace. 
      - Advance `c`, go to 6.
    - **Else if** `c` ia a *paragraph* whose contents are a single
      *strong emphasis*:
      - **If** the recipe's yields are set, abort parsing with an
        error
      - **Else** set the recipe's yields to the contents of the
        paragraph, split a the comma character (with commas between
        ASCII digits ignored), each element stripped from whitespace
        and parsed as an amount.
      - Advance `c`, go to 6.
    - **Else** go to next step.
7. Find ingredient divider:
    - **If** `c` is a *thematic break*, advance `c`
    - **Else** abort parsing with an error.
8. Parse ingredients and ingredient groups:
  - **If** `c` is a *heading*: 
    - Run "Parsing Ingredient Groups" with `c`, `groups` set to the
      recipe's ingredient groups and `parentLevel` set to -1.
    - Set `c` to the returned block
    - Go to 8.
  - **Else if** `c` is a list item (ordered or unordered)
    - Run "Parsing an Ingredient List" with `c` and `ingredients` set
      to the recipe's ingredients.
    - Go to 8.
9. Find instruction divider
    - **If** `c` is a *thematic break*, advance `c`
10. Set the recipe's instructions to the remainder of the documents
    contents from `c` to the end of the file.
    

### Parsing Ingredient Groups

This algorithm accepts a block `c`, a list of ingredients groups
`groups` and an integer parent level `parentLevel`. It modifies
`groups` to append the ingredient groups found and returns the current
block `c`.

1. Examine `c`:
  - **If** `c` is not a *heading*, return.
  - **Else**
    - Let `l` be the heading level of `c`
    - Check nesting:
      - **If** `l` is less than or equal to `parentLevel`, return.
    - Let `g` be an ingredient group with a title equal to the
      contents of the heading `c`, empty ingredients and empty
      ingredient groups.
    - Advance `c`
    - Run "Parsing an Ingredient List" with `c` and `i` set to the
      ingredients of `g`.
    - Run "Parsing Ingredient Groups" with `c`, `groups` set to the
      ingredient groups of `g` and `parentLevel` set to `l`.
    - Go to 1.


### Parsing an Ingredient List

This algorithm accepts a block `c` and a list of ingredients
`ingredients`. It modifies `ingredients` to append the ingredients
found and returns the current block `c`.

1. Examine `c`:
  - **If** `c` is not the start of a bulleted list of an ordered list,
    return.
  - **Else**:
    - Enter `c`
2. Collect ingredients:
  - **If** `c` is a list item:
    - Run "Parsing an Ingredient" on `c` and append the result to
      `ingredients`.
    - Go to next item:
      - **If** `c` has a following block
        - Advance `c` and go to 2.
      - **Else** leave `c`

### Parsing an Ingredient

This algorithm accepts a block `c`. It returns an ingredient `i`:

1. Examine `c`:
  - **If** `c` is a [list item], enter `c`-
  - **Else** abort parsing with an error.
2. Let `a` be the amount, set to unset.
3. Let `n` be the name, set to an empty string.
4. Let `l` be a link, set to unset.
5. Examine `c`:
  - **If** `c` is not a paragraph, set `n` to the verbatim contents of
    `c`.
  - **Else**:
    - Parse the amount:
      - **If** `c`'s contents start with an [emphasis] inline:
        - Run "Parsing an Amount" with `s` set to the emphasis'
          contents, and set `a` to the result.
        - Let `r` be the remaining contents of `c` after the emphasis.
      - **Else**: Let `r` be the verbatim contents of `c`
    - Parse the link:
      - **If** `c` is the only child of its containing list item and
        `c`'s contents consist only of a single [inline link]:
          - Set `l` to the link's destination.
          - Set `n` to the link's text.
      - **Else** set `n` to `r`.
6. Parse the following blocks of the list item:
  - **If** `c` has a block following after it:
    - Advance `c`.
    - Append `c`'s verbatim contents to `n`.
    - Go to 6.
7. Leave `c`
8. Let `i` be an ingredient with the amount `a`, name `n` and link
   `l`.

[list item]: https://spec.commonmark.org/0.31.2/#list-items
[emphasis]: https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis
[inline link]: https://spec.commonmark.org/0.28/#inline-link

### Parsing an Amount

This algorithm accepts a string `s` and returns an amount or nothing.
In this algorithm the following conventions are used.

- `w+` represents one or more whitespace characters
- `w*` represents zero or more whitespace characters
- `[xy]` represents the set of literal characters enclosed by the
  brackets, in this case the character "x" or "y"

1. Trim all whitespace at the beginning of `s`
2. Check for negative
  - **If** `s` starts with a `"-"` character, let `negative` be true.
    Remove the `"-"` and trim all whitespace at the beginning of `s`
  - **Else** let `negative` be false
3. Let `v` be a number, set it to unset
  - **If** `s` starts with an improper fraction (`a` `w+` `b` `w*`
`[/]` `w*` `c`, with `a`, `b`, `c` integers), set `v` to `a` +
(`b`/`c`).
  - **Else if** `s` stars with an improper faction using Unicode
    vulgar fractions (`a` `w+` `b`, with `a` integers and `b` a
    Unicode vulgar fractions). Set `f` to the numeric value assigned
    to `b` and `v` to `a` + `f`.
  - **Else if** `s` starts with a proper fraction (`a` `w*` `[/]` `w*`
    `b`, with `a`, `b` integers), set `v` to (`a`/`b`).
  - **Else if** `s` starts with a Unicode vulgar fraction `a`. Set `v`
    to the numeric value assigned to `a`.
  - **Else if** `s` starts with a decimal number (`a` `[.,]` `b`, with
    `a`, `b` integers), set `v` to a decimal number with `a` being its
    whole and `b` being its fractional part.
  - **Else if** `s` starts with an integer `a`, set `v` to `a`.
4. Let `u` be the remainder of `s`, stripped of whitespace. Set `u` to
   unset if it is the empty string.
5. Return result:
  - **If** `v` is set, return an amount the the value `v` and the unit
    `u`.
  - **Else if** `u` is set, abort parsing with an error.
  - **Else** return nothing.
  

## Test Cases

Implementations of this specification must conform with all [test
cases]. There are two kinds of test cases: valid files (`*.md` with a
corresponding `*.json`) and invalid files (`*.invalid.md`). 

The format of the JSON files is specified via a JSON schema file
distributed with the testcases. When comparing the actual to the
expected results property order in objects should be ignored.

[test cases]: https://github.com/RecipeMD/RecipeMD/tree/master/testcases



## Authors Licensing

This specification was written and is maintained by Jonas Grosse-Holz 
and Tilman Stehr. The project's website is [recipemd.org].

The specification is licensed under the terms of the GNU Lesser 
General Public License as published by the Free Software Foundation, 
either version 3 of the License, or any later version.

[recipemd.org]: https://recipemd.org


## Version History

### Version 2.3.6 (Unreleased)

- Update link to test cases to point to the new "RecipeMD" GitHub
  organization.
- Fix test cases that included amounts with no factor.
  - These were always invalid according to the spec, but the reference
    implementation incorrectly accepted them.
- Update data type definitions to align with the test cases and the
  reference implementation. Many thanks to
  [d-k-bo](https://github.com/d-k-bo) for the [detailed
  report](https://github.com/RecipeMD/RecipeMD/issues/52) on the
  discrepancies.
- Add a detailed description of a RecipeMD parsing strategy.
- Reference new JSON Schema for test case JSON files.
- Specify the *title*  of an *ingredient group* as a non-optional
  field.
    - The parsing algorithm never allowed the creation of groups
      without a *title*, but the field was marked as optional in the
      data type description.
    - This will not change the parsing behavior of any recipes. It may
      however be a breaking change for implementations, since it
      changes the interface of the *ingredient group*  data type in a
      way that may not be backwards compatible. 


### Version 2.3.5 (2022-08-14)

- Fix test case "ingredients_multiline.md" to use valid link targets
- Expand test cases to cover
  - [reference links] and [reference-style images]
  - ingredients with sublists 
  - ingredients using numbered lists
  - ingredients partially wrapped with links
  - link ingredients with spaces in link targets
  - link ingredients with link titles
  - partial tag paragraphs that should not be interpreted as tags
  - titles using [setext headings]

[reference links]: https://spec.commonmark.org/0.30/#reference-link
[reference-style images]: https://spec.commonmark.org/0.30/#example-581
[setext headings]: https://spec.commonmark.org/0.30/#setext-headings

### Version 2.3.4 (2021-12-26)

- Fixes to test cases:
  - Add missing ingredient groups in JSON files
  - Clean up formatting
  - Fix missing indentation spaces for multiline ingredients

### Version 2.3.3 (2021-01-02)

- Clarify that yields and tags may appear at most once.
- Add test cases:
  - Multiple yields or tags
  - Tag/yield order

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

