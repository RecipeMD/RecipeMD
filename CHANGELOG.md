# Version Next

- Amount values can be negative to allow simple stock keeping
- Remove linked recipe amount from title in instructions as it is confusing with multiple levels of flattened recipes
- Prevent duplicated headlines when flattening
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