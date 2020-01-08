# Changelog

The `recipemd` package uses [semantic versioning](https://semver.org).

## Version 4.0.2 (2020-01-08)

- Fix flattening

## Version 4.0.1 (2019-12-18)

- Fix incorrect trove classifiers

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
