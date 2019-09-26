# RecipeMD

A standard format for recipes as [Markdown](https://commonmark.org) files and a python reference implementation.


## Specification

See [specification.md](./specification.md) for the current specification and [examples](https://github.com/tstehr/RecipeMD/tree/master/examples) for some example recipes.


## CLI tool

1. Check out repo
2. Install via pip: `pip install <path to repo>`
3. *Optional:* The command line tool provides completions via [argcomplete]. See [below](#install-completions) for installation 
   instructions.

[argcomplete]: https://github.com/kislyuk/argcomplete


### How to use

Display and validate a recipe:

```
recipemd <path/to/recipe.md>
```

Get recipe title:

```
recipemd <path/to/recipe.md> -t
```

Get recipe ingredients, e.g. to pipe to [shoppinglist-cli]:

[shoppinglist-cli]: https://github.com/AberDerBart/shoppinglist-cli

```
recipemd <path/to/recipe.md> -i
```

Multiply recipe by a factor:

```
recipemd <path/to/recipe.md> -m 5.5
```

Scale recipe for a given yield (e.g. number of servings, volume, mass, amount):

```
recipemd <path/to/recipe.md> -y "10 servings"
```

Get all tags of all recipes in the current folder:

```
recipemd-find tags
```

Get recipes by tag:

```
recipemd-find -e "tag:cheese or tag:summer" recipes
```


### Install completions

Completion installation depends on your shell. Read the [argcomplete documentation][argcomplete] for more detail. 

#### Bash

```
activate-global-python-argcomplete
```

#### Zsh

```
autoload -U bashcompinit
bashcompinit
eval "$(register-python-argcomplete recipemd)"
```

#### Tcsh

```
eval `register-python-argcomplete --shell tcsh recipemd`
```

#### Fish

```
register-python-argcomplete --shell fish recipemd > ~/.config/fish/completions/recipemd.fish
```

## Resources

You can use [recipemd-extract](https://github.com/AberDerBart/recipemd-extract) to fetch and extract recipes from the web.

Some RecipeMD repositories:

- [AberDerBart](https://github.com/AberDerBart/recipes)
- [dasnessie](https://github.com/dasnessie/recipes)
- [sonea-pm8](https://github.com/sonea-pm8/recipes)
- [timschubert](https://github.com/timschubert/recipes)
- [tstehr](https://github.com/tstehr/recipes)
