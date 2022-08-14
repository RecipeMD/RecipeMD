# Changelog

The `recipemd` package uses [semantic versioning](https://semver.org).

## Version 4.1.0 (2022-08-14)

- *Fix:* Don't parse links that partially wrap an ingredient's name as
  amount links. This was never spec conformant, but the test cases
  were incorrect up to spec version 2.3.5
- *Fix:* Preserve reference links and reference-style images in
  description and instructions
- Switch the underlying commonmark markdown parser from
  [`commonmark.py`] to [`markdown-it-py`]
    - [`commonmark.py`] is deprecated and the project recommends
      switching to [`markdown-it-py`]
    - The new parser allows for more accurate parsing of certain
      markdown constructs, enabling the fixes detailed above

[`markdown-it-py`]: https://markdown-it-py.readthedocs.io/


## Version 4.0.8 (2021-12-26)

- *Fix:* Work around bug in [`commonmark.py`] which led to incorrect
  parsing of fenced code blocks

[`commonmark.py`]: https://github.com/readthedocs/commonmark.py


## Version 4.0.7 (2021-05-01)

- *Fix:* Make `--flatten` compatible with Python 3.9
- *Fix:* Use UTF-8 encoding when loading linked files
- *Fix:* Fix path being parsed as port under windows
- Add integrations tests for the `recipemd` CLI


## Version 4.0.6 (2021-03-28)

- *Fix:* Show error on duplicated yields/tag instead of silently ignoring the earlier occurrence.
- *Fix:* Prevent error when scaling a recipe with a factor-less yield. 
- Relax version requirement for yarl and argcomplete
- Include test cases in source distributions 


## Version 4.0.5 (2020-12-31)

- *Fix:* Fix missing package due to bundling error
- *Fix:* Incorrect heading in changelog


## Version 4.0.4 (2020-12-30)

- *Fix:* Scaling of amounts with `None` factors
- *Fix:* Possible infinite recursion when flattening recipes
- *Fix:* Make `recipemd` compatible with Python 3.9 


## Version 4.0.3 (2020-01-21)

- *Fix:* Duplicating ingredients in groups as top level ingredients when multiplying recipe
- *Fix:* Inconsistent changelog formatting


## Version 4.0.2 (2020-01-08)

- *Fix:* Flattening failing with exception


## Version 4.0.1 (2019-12-18)

- *Fix:* Incorrect trove classifiers


## Version 4.0.0 (2019-12-18)

- *Breaking*: Create separate lists of ingredients and ingredients groups in `Recipe` and `IngredientGroup`. This 
  ensures that ingredients groups always follow after ingredients (see https://github.com/tstehr/RecipeMD/issues/6)
- Improve error message when trying to flatten a linked recipe and no matching yield can be found.
- License under LGPL


## Version 3.0.1 (2019-11-27)

- Add `-v/--version` argument to `recipemd` and `recipemd-find` to display current version


## Version 3.0.0 (2019-11-17)

- *Breaking:* Classes in `recipemd.data` are now frozen
- *Breaking:* Rename `recipemd-tags` to `recipemd-find` and option  `-f/--filter` to `-e/--expression`
- *Breaking:* `recipemd-find` now searches tags, ingredient names and units
- *Breaking:* `recipemd-find` displays result in columns instead of rows by default. Use `-x` for old behavior
- Prevent duplicated headlines when flattening
- Amount values can be negative to allow simple stock keeping
- Remove linked recipe amount from title in instructions as it is confusing with multiple levels of flattened recipes
- Add option `--export-linked` to export linked recipes in the correct scale to a folder 
- Advanced expression syntax in recipemd-find
    - Terms are now case insensitive by default
    - Terms can be quoted to for exact match
    - Allow `tag:`, `ingr:` or `unit:` as prefix for terms to restrict term to tag, ingredient or unit
    - Search via regular expressions is possible by surrounding a term with `/`
- Add option `-j/--json` for JSON output of recipe
- *Fix:* Exception in flattening if link ingredient has no amount


## Version 2.2.2 (2019-06-29)

- Implement `recipemd-tags` tool for finding recipes by tag


## Version 2.2.1 (2019-04-22)

- Add option `-r/--round` to allow control of rounding in cli output
- Add shell completions to cli


## Version 2.2.0 (2019-04-22)

- Allow recipes to reference other recipes
- Implement flattening of referenced recipes in cli


## Version 2.1.0 (2019-03-25)

- Allow unicode vulgar fractions in ingredient amounts


## Version 2.0.0 (2018-09-13)

- *Breaking:* Implement parsing of yields separate from tags (according to RecipeMD 2.0.0 specification)


## Version 1.0.0 (2018-08-27)

- Initial version
