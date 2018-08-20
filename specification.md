# Markdown Recipe Specification



- a *valid* recipe consists of:
	- a title
	- *optional*: a short description
	- *optional*: 1..n tags
	- *optional*: A number of servings
	- 1..n ingredients
	- *optional*: instructions

- the Markdown representation shall be as follows:
	1. the title
	2. *optional*: the short description
	3. *optional*: the tags, including the number of servings
	5. a horizontal line
	6. the ingredients, consisting of
	    1. headings to group ingredients
	    2. lists, where each list item is an ingredient
	7. a horizontal line -- this may be omitted if there are no instructions
	8. *optional*: the instructions

- the markdown shall follow the commonmark specification
- the title is noted as a first level header:
```# Guacamole```
- the short description is noted as a single paragraph:
```Some people call it guac.```
- the tags are noted as paragraph containing only a comma seperated list in italic case:
```*sauce, vegan*```
- the number of servings is noted as the first number in the first tag (this implies that no other numbers shall be used in the first tag):
```
*servings: 4, vegan, sauce*
```
- the ingredients are noted as list items. The headings form the titles of ingredient groups. The amount of each ingredient (if given) is noted in italic case. Amounts may be expressed as decimals (dividers "." and ",") and fractions:
```
- *1* avocado
- *.5 teaspoon* salt
- *1 1/2 pinches* red pepper flakes
- lemon juice
```
- anything following the second horizontal line is considered instructions
