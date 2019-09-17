# Version Next

- *Breaking:* Classes in `recipemd.data` are now frozen
- *Breaking:* Rename `recipemd-tags` to `recipemd-find` and option  `-f/--filter` to `-e/--expression`
- Prevent duplicated headlines when flattening
- Amount values can be negative to allow simple stock keeping
- Remove linked recipe amount from title in instructions as it is confusing with multiple levels of flattened recipes
- Add option `--export-linked` to export linked recipes in the correct scale to a folder 
- `recipemd-find` now searches tags, ingredient names and units
- Advanced expression syntax in recipemd-find
    - Terms can be quoted to allow searching for terms that include whitespace
    - Simple terms are now case insensitive by default
    - Implement substring matching by prefixing a term with `~`
    - Allow `tag:`, `ingr:` or `unit:` as prefix for terms to restrict term to tag, ingredient or unit
    - Search via regular expressions is possible by surrounding a term with `/`
- Add option `-j/--json` for JSON output of recipe
- *Fix:* Exception in flattening if link ingredient has no amount


# Version 2.2.2 (2019-06-29)

- Implement `recipemd-tags` tool for finding recipes by tag


# Version 2.2.1 (2019-04-22)

- Add option `-r/--round` to allow control of rounding in cli output
- Add shell completions to cli


# Version 2.2.0 (2019-04-22)

- Allow recipes to reference other recipes
- Implement flattening of referenced recipes in cli


# Version 2.1.0 (2019-03-25)

- Allow unicode vulgar fractions in ingredient amounts


# Version 2.0.0 (2018-09-13)

- *Breaking:* Implement parsing of yields separate from tags (according to RecipeMD 2.0.0 specification)


# Version 1.0.0 (2018-08-27)

- Initial version
